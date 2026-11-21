"""Public transport/provisioning tests; no changes to scientific algorithms."""
import io
import json
from pathlib import Path
import secrets

import pytest
from fastapi.testclient import TestClient

from api.main import ROOT, MAX_BODY, create_app
from api import render
from deploy import provision as panel


@pytest.fixture
def public_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EPISENTINEL_OPERATOR_KEY", "test-only-operator-key-that-is-long-enough")
    monkeypatch.setenv("EPISENTINEL_CORS_ORIGINS", "https://frontend.example.org")
    monkeypatch.setenv("EPISENTINEL_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.delenv("EPISENTINEL_FORECAST_METHODS", raising=False)
    monkeypatch.delenv("EPISENTINEL_SARIMA_ACCEPTED", raising=False)
    monkeypatch.delenv("EPISENTINEL_ENABLE_INGESTION", raising=False)
    return {"X-Operator-Key": "test-only-operator-key-that-is-long-enough"}


def test_public_defaults_and_health(public_env):
    with TestClient(render.application()) as c:
        assert c.get("/api/v1/health").status_code == 200
        assert c.get("/api/v1/ready").status_code == 503
        caps = c.get("/api/v1/capabilities").json()
        assert caps["forecast_methods"] == ["ultimo_valor"]
        assert caps["ingestion_enabled"] is False
        schema = c.get("/api/v1/openapi.json").json()
        assert schema["paths"]["/api/v1/forecasts/retrospective"]["post"]["security"] == [{"OperatorKey": []}]
        assert schema["paths"]["/api/v1/datasets/{dataset_id}"]["get"]["security"] == [{"HTTPBearer": [], "OperatorKey": []}]
        assert (caps["session_ttl_s"], caps["max_sessions"], caps["datasets_per_session"]) == (1800, 4, 1)
        assert c.post("/api/v1/sessions").status_code == 401
        assert c.post("/api/v1/sessions", headers=public_env).status_code == 403
        assert c.post("/api/v1/forecasts/retrospective", content=b"x" * (MAX_BODY + 1)).status_code == 401
        rejected = c.post("/api/v1/forecasts/retrospective", headers=public_env, json={"method": "sarima_estacional"})
        assert rejected.status_code == 403 and rejected.json()["error"]["code"] == "METHOD_DISABLED"


@pytest.mark.parametrize("setting,value", [("EPISENTINEL_OPERATOR_KEY", "short"), ("EPISENTINEL_CORS_ORIGINS", "*"),
    ("EPISENTINEL_CORS_ORIGINS", "https://frontend.example.org/path"), ("EPISENTINEL_CORS_ORIGINS", "http://public.example.org"),
    ("EPISENTINEL_FORECAST_METHODS", "sarima_estacional"), ("EPISENTINEL_FORECAST_METHODS", "sarima_sin_estacional")])
def test_configuration_fails_closed(public_env, monkeypatch, setting, value):
    monkeypatch.setenv(setting, value)
    with pytest.raises(ValueError):
        render.application()


def test_cors_errors_and_protected_ingestion(public_env, monkeypatch):
    monkeypatch.setenv("EPISENTINEL_ENABLE_INGESTION", "1")
    with TestClient(render.application()) as c:
        result = c.options("/api/v1/datasets/manual", headers={"Origin": "https://frontend.example.org", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "x-operator-key,authorization,content-type"})
        assert result.status_code == 200
        assert result.headers["access-control-allow-origin"] == "https://frontend.example.org"
        rejected = c.post("/api/v1/sessions", headers={"Origin": "https://frontend.example.org"})
        assert rejected.status_code == 401
        assert rejected.headers["access-control-allow-origin"] == "https://frontend.example.org"
        assert "access-control-allow-origin" not in c.get("/api/v1/health", headers={"Origin": "https://evil.example.org"}).headers
        sessions = [c.post("/api/v1/sessions", headers=public_env) for _ in range(4)]
        assert all(r.status_code == 201 for r in sessions)
        assert c.post("/api/v1/sessions", headers=public_env).status_code == 429


def test_public_size_cap_and_missing_memory_accounting(public_env, monkeypatch):
    monkeypatch.setenv("EPISENTINEL_ENABLE_INGESTION", "1")
    monkeypatch.setenv("EPISENTINEL_FORECAST_METHODS", "sarima_sin_estacional")
    monkeypatch.setenv("EPISENTINEL_SARIMA_ACCEPTED", "1")
    monkeypatch.setattr(render, "memory_current", lambda: None)
    with TestClient(render.application()) as c:
        response = c.post("/api/v1/datasets/upload", headers=public_env, content=b"x" * (render.PUBLIC_BODY_LIMIT + 1))
        assert response.status_code == 413
        response = c.post("/api/v1/forecasts/retrospective", headers=public_env, json={"method": "sarima_sin_estacional"})
        assert response.status_code == 503


@pytest.mark.parametrize("method", [None, [], {}, True])
def test_invalid_method_types_return_structured_error(public_env, method):
    with TestClient(render.application()) as c:
        response = c.post("/api/v1/forecasts/retrospective", headers=public_env, json={"method": method})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_deep_json_is_rejected_before_model(public_env):
    with TestClient(render.application()) as c:
        response = c.post("/api/v1/forecasts/retrospective", headers=public_env,
                          content=b'{"method":' + b'[' * 2000 + b'null' + b']' * 2000 + b'}')
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_rate_budget_and_sarima_headroom(public_env, monkeypatch):
    monkeypatch.setenv("EPISENTINEL_FORECAST_METHODS", "sarima_sin_estacional")
    monkeypatch.setenv("EPISENTINEL_SARIMA_ACCEPTED", "1")
    monkeypatch.setattr(render, "memory_current", lambda: 321 * 1024**2)
    with TestClient(render.application()) as c:
        for _ in range(5):
            r = c.post("/api/v1/forecasts/retrospective", headers=public_env, json={"method": "sarima_sin_estacional"})
            assert r.status_code == 503
        r = c.post("/api/v1/forecasts/retrospective", headers=public_env, json={"method": "sarima_sin_estacional"})
        assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"


def test_readiness_checks_runtime_panel_only(public_env, tmp_path):
    # A marker is sufficient only for this transport test; startup validates real bytes.
    target = tmp_path / "data/processed/panel_casos.parquet"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"test marker")
    with TestClient(render.application()) as c:
        assert c.get("/api/v1/ready").status_code == 200


def test_provision_refuses_missing_approval_and_invalid_source(tmp_path):
    with pytest.raises(panel.ProvisionError, match="APPROVAL"):
        panel.provision({"EPISENTINEL_RUNTIME_ROOT": str(tmp_path)})
    manifest = json.loads(panel.MANIFEST.read_text())
    env = {"EPISENTINEL_RUNTIME_ROOT": str(tmp_path), "EPISENTINEL_PANEL_APPROVED_SHA256": manifest["sha256"],
           "EPISENTINEL_PANEL_URL": "https://wrong.example.org/panel?secret=not-logged", "EPISENTINEL_PANEL_HOST": "approved.example.org"}
    with pytest.raises(panel.ProvisionError, match="SOURCE_NOT_ALLOWED"):
        panel.provision(env)
    assert not (tmp_path / "data/processed/panel_casos.parquet").exists()


def test_provision_size_hash_and_transfer_bounds(tmp_path):
    manifest = json.loads(panel.MANIFEST.read_text())
    wrong = tmp_path / "wrong.parquet"
    wrong.write_bytes(b"x" * manifest["bytes"])
    with pytest.raises(panel.ProvisionError, match="HASH"):
        panel.verify(wrong, manifest)
    with pytest.raises(panel.ProvisionError, match="TRANSFER_LIMIT"):
        panel.copy_bounded(io.BytesIO(b"1234"), io.BytesIO(), 3)


def test_exact_historical_provision_and_no_overwrite(tmp_path):
    source = ROOT / "data/processed/panel_casos.parquet"
    if not source.exists():
        pytest.skip("Exact historical panel is local, never substitute")
    manifest = json.loads(panel.MANIFEST.read_text())
    env = {"EPISENTINEL_RUNTIME_ROOT": str(tmp_path), "EPISENTINEL_PANEL_APPROVED_SHA256": manifest["sha256"], "EPISENTINEL_PANEL_FILE": str(source)}
    target = panel.provision(env)
    assert target.read_bytes() == source.read_bytes()
    before = target.stat().st_mtime_ns
    assert panel.provision(env) == target and target.stat().st_mtime_ns == before
    target.write_bytes(b"damaged")
    with pytest.raises(panel.ProvisionError, match="SIZE"):
        panel.provision(env)
    assert target.read_bytes() == b"damaged"


def test_local_contract_preserved():
    exported = json.loads((ROOT / "docs/api/openapi.json").read_text(encoding="utf-8"))
    assert create_app().openapi() == exported


def test_start_uses_dynamic_port_one_worker_and_drops_storage_credentials(public_env, monkeypatch):
    from deploy import start
    monkeypatch.setattr(start, "provision", lambda: None)
    monkeypatch.setattr(render, "application", lambda: None)
    monkeypatch.setenv("PORT", "12345")
    monkeypatch.setenv("EPISENTINEL_PANEL_URL", "https://storage.example.org/signed?token=test-not-a-real-secret")
    monkeypatch.setenv("EPISENTINEL_PANEL_BEARER", "test-storage-secret")
    captured = []
    monkeypatch.setattr(start.os, "execv", lambda exe, args: captured.append((exe, args)))
    start.main()
    args = captured[0][1]
    assert args[args.index("--port") + 1] == "12345"
    assert args[args.index("--host") + 1] == "0.0.0.0"
    assert args[args.index("--workers") + 1] == "1"
    assert "--factory" in args
    assert "EPISENTINEL_PANEL_URL" not in start.os.environ
    assert "EPISENTINEL_PANEL_BEARER" not in start.os.environ


def test_https_provision_exact_bytes_with_controlled_storage(tmp_path):
    source = ROOT / "data/processed/panel_casos.parquet"
    if not source.exists():
        pytest.skip("Exact historical panel is local, never substitute")
    manifest = json.loads(panel.MANIFEST.read_text())
    requests = []
    class Storage:
        def open(self, request, timeout):
            requests.append(request)
            assert timeout == 20
            return io.BytesIO(source.read_bytes())
    env = {"EPISENTINEL_RUNTIME_ROOT": str(tmp_path), "EPISENTINEL_PANEL_APPROVED_SHA256": manifest["sha256"],
           "EPISENTINEL_PANEL_URL": "https://approved.example.org/panel?token=test-only", "EPISENTINEL_PANEL_HOST": "approved.example.org",
           "EPISENTINEL_PANEL_BEARER": "test-only-storage-token"}
    target = panel.provision(env, opener=Storage())
    assert target.read_bytes() == source.read_bytes()
    assert requests[0].get_header("Authorization") == "Bearer test-only-storage-token"


def test_storage_errors_and_redirect_policy_do_not_leak_credentials(tmp_path, capsys):
    manifest = json.loads(panel.MANIFEST.read_text())
    class BrokenStorage:
        def open(self, request, timeout):
            raise RuntimeError("signed-url-with-test-only-secret")
    env = {"EPISENTINEL_RUNTIME_ROOT": str(tmp_path), "EPISENTINEL_PANEL_APPROVED_SHA256": manifest["sha256"],
           "EPISENTINEL_PANEL_URL": "https://approved.example.org/panel?token=test-only", "EPISENTINEL_PANEL_HOST": "approved.example.org"}
    with pytest.raises(panel.ProvisionError, match="^PANEL_PROVISION_FAILED$"):
        panel.provision(env, opener=BrokenStorage())
    assert not capsys.readouterr().out
    with pytest.raises(panel.ProvisionError, match="REDIRECT_REJECTED"):
        panel.NoRedirect().redirect_request()
