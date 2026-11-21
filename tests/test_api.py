"""REST integration, isolation and real B06 regression; synthetic fixtures are tests only."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import threading
import time

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import ROOT, create_app, MAX_BODY
from api.store import SessionStore
from app import retrospective as ia


CSV = b"cod_mun,ano,semana,cod_eve,conteo\n76001,2024,1,210,5\n76001,2024,3,210,0\n"
CONFIG = {"version": "test-v1", "territory": "76001", "event_codes": [210],
          "periods": [[2024, 1], [2024, 2], [2024, 3]],
          "calendar": {"calendar_id": "declared", "version": "1", "source": "test"}}


@pytest.fixture
def client(tmp_path):
    (tmp_path / "data/processed").mkdir(parents=True)
    pd.DataFrame([np.arange(832) % 17 + 1], index=["76001"],
                 columns=pd.date_range("2007-01-01", periods=832, freq="7D")).to_parquet(tmp_path / "data/processed/panel_casos.parquet")
    with TestClient(create_app(tmp_path)) as c:
        yield c


def auth(client):
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    return {"Authorization": "Bearer " + response.json()["token"]}


def upload(client, headers=None, content=CSV):
    return client.post("/api/v1/datasets/upload", headers={**(headers or auth(client)), "Content-Type": "text/csv"}, content=content)


def test_query_contract_and_cors(client):
    for path in ("health", "overview", "territories", "series?series=76001", "methodology", "experiments", "benchmarks", "openapi.json"):
        response = client.get("/api/v1/" + path)
        assert response.status_code == 200, response.text
    schema = client.get("/api/v1/openapi.json").json()
    assert schema["paths"]["/api/v1/forecasts/retrospective"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("Retrospective")
    assert "HTTPBearer" in schema["components"]["securitySchemes"]
    assert client.get("/api/v1/series?series=99999").status_code == 404
    assert client.get("/api/v1/territories?limit=5000").status_code == 422
    preflight = client.options("/api/v1/datasets/upload", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type,x-filename"})
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
    denied = client.get("/api/v1/health", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in denied.headers
    assert denied.headers["cache-control"] == "no-store"


def test_published_openapi_matches_application():
    exported = json.loads((ROOT / "docs/api/openapi.json").read_text(encoding="utf-8"))
    assert exported == create_app().openapi()


def test_missing_panel_is_unavailable_not_fake(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        assert c.get("/api/v1/health").json()["historical_source_available"] is False
        assert c.get("/api/v1/overview").status_code == 503


def test_csv_manual_b05_provenance_and_isolation(client, monkeypatch):
    def never(*args, **kwargs):
        pytest.fail("Ingestion must not run B06")
    monkeypatch.setattr(ia, "execute_bounded", never)
    a, b = auth(client), auth(client)
    response = upload(client, a)
    assert response.status_code == 201, response.text
    dataset = response.json()
    assert dataset["report"]["summary"]["rows_delivered"] == 2
    assert dataset["sha256"] == hashlib.sha256(CSV).hexdigest()
    assert dataset["trained"] is False and dataset["forecast_eligibility"] == "not_evaluated"
    assert dataset["records"][0]["record"] == 2
    path = "/api/v1/datasets/" + dataset["dataset_id"]
    assert client.get(path, headers=a).status_code == 200
    assert client.get(path, headers=b).status_code == 404
    assert client.get(path).status_code == 401
    result = client.post(path + "/series", headers=a, json=CONFIG)
    assert result.status_code == 200, result.text
    series = result.json()["series"]["series"][0]
    assert [p["observed_count"] for p in series["points"]] == [5, None, 0]
    assert series["eligibility"]["status"] == "not_evaluated"
    assert series["points"][0]["source_refs"][0]["record"] == 2
    manual = client.post("/api/v1/datasets/manual", headers=b, json={"rows": [{"cod_mun": "76001", "ano": 2024, "semana": 1, "cod_eve": 210, "conteo": 5}]})
    assert manual.status_code == 201, manual.text
    assert manual.json()["source"] == "manual.csv"
    assert client.delete(path, headers=a).status_code == 204
    assert client.get(path, headers=a).status_code == 404
    assert client.delete("/api/v1/sessions/current", headers=b).status_code == 204
    assert client.get("/api/v1/datasets/" + manual.json()["dataset_id"], headers=b).status_code == 401


@pytest.mark.parametrize("content", [b"bad\n", CSV + b"76001,2024,1,210,8\n", CSV.replace(b",5", b",-5"), CSV.replace(b",210", b",999"), CSV.replace(b",1,", b",54,")])
def test_invalid_csv_rejected_atomically(client, content):
    response = upload(client, content=content)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CSV_REJECTED"
    assert response.json()["error"]["details"]["summary"]["rows_delivered"] == 0


def test_invalid_manual_and_configuration(client):
    headers = auth(client)
    row = {"cod_mun": "76001", "ano": 2024, "semana": 1, "cod_eve": 210, "conteo": -1}
    assert client.post("/api/v1/datasets/manual", headers=headers, json={"rows": [row]}).status_code == 422
    row["conteo"] = True
    assert client.post("/api/v1/datasets/manual", headers=headers, json={"rows": [row]}).status_code == 422
    path = "/api/v1/datasets/" + upload(client, headers).json()["dataset_id"] + "/series"
    bad = {**CONFIG, "periods": [[2024, 3], [2024, 1]]}
    assert client.post(path, headers=headers, json=bad).status_code == 422
    bad = {**CONFIG, "calendar": {**CONFIG["calendar"], "verification": "verified"}}
    assert client.post(path, headers=headers, json=bad).status_code == 422


def test_limits_expiry_and_errors(client, tmp_path):
    headers = auth(client)
    response = upload(client, headers, b"x" * (MAX_BODY + 1))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "BODY_TOO_LARGE"
    for _ in range(4):
        assert upload(client, headers).status_code == 201
    assert upload(client, headers).status_code == 429
    store = SessionStore(ttl=1, capacity=1)
    with TestClient(create_app(tmp_path, store)) as c:
        token = auth(c)
        assert c.post("/api/v1/sessions").status_code == 429
        next(iter(store.entries.values())).expires = time.monotonic() - 1
        assert upload(c, token).status_code == 401
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert set(response.json()["error"]) == {"code", "message", "details"}


def test_no_forecast_on_read_and_invalid_request(client, monkeypatch):
    calls = []
    monkeypatch.setattr(ia, "execute_bounded", lambda r: calls.append(r))
    for path in ("overview", "series?series=76001", "experiments", "benchmarks", "methodology"):
        assert client.get("/api/v1/" + path).status_code == 200
    body = {"series": "76001", "cut": 778, "method": "ultimo_valor"}
    assert client.post("/api/v1/forecasts/retrospective", json=body).status_code == 422
    assert not calls


def test_mase_unavailable_and_missing_target_remain_explicit(client, monkeypatch):
    monkeypatch.setattr(ia, "execute_bounded", ia.fit_prefix)
    frame = pd.DataFrame([[4.] * 832], index=["76001"], columns=pd.date_range("2007-01-01", periods=832, freq="7D"))
    monkeypatch.setattr(ia, "load_panel", lambda root: (frame, "fixture"))
    body = {"series": "76001", "cut": 779, "method": "ultimo_valor"}
    output = client.post("/api/v1/forecasts/retrospective", json=body)
    assert output.status_code == 200, output.text
    assert output.json()["evaluation"]["metrics"]["MASE"] is None
    assert output.json()["evaluation"]["limitations"]
    frame.iloc[0, 781] = np.nan
    result = client.post("/api/v1/forecasts/retrospective", json=body).json()
    assert result["evaluation"]["rows"][1]["observed"] is None
    assert not result["evaluation"]["metrics"] and not result["indicators"]


def test_unexpected_errors_do_not_leak_internal_paths(tmp_path, monkeypatch):
    def broken(*args):
        raise RuntimeError("secret internal path")
    monkeypatch.setattr(ia, "load_panel", broken)
    with TestClient(create_app(tmp_path), raise_server_exceptions=False) as c:
        response = c.get("/api/v1/overview", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret" not in response.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == response.json()["request_id"]


@pytest.mark.parametrize("code,status", [("BUSY", 429), ("TIMEOUT", 504), ("WORKER_ERROR", 503), ("NO_CONVERGENCIA", 422)])
def test_structured_forecast_failures(client, monkeypatch, code, status):
    monkeypatch.setattr(ia, "execute_bounded", lambda r: ia.failure(r, code, "failure"))
    response = client.post("/api/v1/forecasts/retrospective", json={"series": "76001", "cut": 779, "method": "sarima_sin_estacional"})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"]["points"] == []


def test_actual_shared_slot_rejects_competing_http_request(client, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def worker(*args, **kwargs):
        entered.set()
        release.wait(5)
        raise ia.subprocess.TimeoutExpired("worker", 1)
    monkeypatch.setattr(ia.subprocess, "run", worker)
    body = {"series": "76001", "cut": 779, "method": "ultimo_valor"}
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(client.post, "/api/v1/forecasts/retrospective", json=body)
        try:
            assert entered.wait(5)
            assert client.post("/api/v1/forecasts/retrospective", json=body).status_code == 429
        finally:
            release.set()
        assert first.result().status_code == 504


@pytest.mark.parametrize("method", ia.B06_METHODS)
def test_real_cali_rest_scientific_regression(method):
    path = ROOT / "data/processed/panel_casos.parquet"
    if not path.exists():
        pytest.skip("Requires original historical panel; never substitute synthetic data")
    protected = [path, *ROOT.glob("docs/experiments/*.json"), *ROOT.glob("docs/benchmarks/*.json")]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    with TestClient(create_app()) as c:
        response = c.post("/api/v1/forecasts/retrospective", json={"series": "76001", "cut": 779, "method": method})
    assert response.status_code == 200, response.text
    result = response.json()
    saved = json.loads((ROOT / f"docs/experiments/ia_i1_cali_779_{method}.json").read_text())
    np.testing.assert_allclose([p["yhat"] for p in result["forecast"]["points"]], [p["yhat"] for p in saved["forecast"]["points"]], rtol=1e-8)
    assert [r["observed"] for r in result["evaluation"]["rows"]] == [57, 66, 57, 48, 68, 51, 50, 58]
    for metric in ("MAE", "RMSE", "MASE"):
        assert result["evaluation"]["metrics"][metric] == pytest.approx(saved["evaluation"]["metrics"][metric], rel=1e-8)
    if method.startswith("sarima"):
        assert result["forecast"]["diagnostics"]["converged"] is True
        np.testing.assert_allclose([[p["lo"], p["hi"]] for p in result["forecast"]["points"]], [[p["lo"], p["hi"]] for p in saved["forecast"]["points"]], rtol=1e-8)
    assert all(set(i) >= {"source", "period", "universe", "aggregation", "validation_status"} for i in result["indicators"])
    assert result["request"]["source_sha256"] == before[path]
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected} == before
