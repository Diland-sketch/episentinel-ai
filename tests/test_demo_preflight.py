"""B13 operational tests; synthetic fixtures are never demonstration data."""
import hashlib
import ipaddress
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from scripts import preflight_demo as preflight

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    for relative in preflight.REQUIRED_FILES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic operational fixture", encoding="utf-8")
    (tmp_path / "app/analysis_styles.css").write_text("<style>#102F3A #276D70 #8DCABA #D59A70 #F7F5EF</style>", encoding="utf-8")
    artifact = tmp_path / "data/raw/example.csv"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"synthetic source")
    monkeypatch.setattr(preflight, "ARTIFACTS", {"data/raw/example.csv": hashlib.sha256(artifact.read_bytes()).hexdigest()})
    def git(args, **kwargs):
        return SimpleNamespace(stdout=preflight.REFERENCE_COMMIT if args[1] == "rev-parse" else "")
    monkeypatch.setattr(preflight.subprocess, "run", git)
    monkeypatch.setattr(preflight, "demo_coverage", lambda root: {210: {"observed": 3}, 220: {"observed": 2}})
    monkeypatch.setattr(preflight, "saved_results", lambda root: [{"serie": "test", "modelo": "synthetic"}])
    monkeypatch.setattr(preflight, "positional_plan", lambda root: {"origins": [1]*24, "excluded": [1]*2})
    return tmp_path


def test_preflight_is_read_only(prepared):
    before = {str(p): p.read_bytes() for p in prepared.rglob("*") if p.is_file()}
    result = preflight.inspect(prepared, environment=False)
    assert result["verdict"] == "APTO CON OBSERVACIONES"
    assert not any(c["status"] == "error" for c in result["checks"])
    assert before == {str(p): p.read_bytes() for p in prepared.rglob("*") if p.is_file()}


@pytest.mark.parametrize("defect", ["missing", "changed"])
def test_missing_or_changed_artifact_blocks_without_repair(prepared, defect):
    path = prepared / "data/raw/example.csv"
    if defect == "missing":
        path.unlink()
    else:
        path.write_bytes(b"changed fixture")
    result = preflight.inspect(prepared, environment=False)
    assert result["verdict"] == "NO APTO"
    assert next(c for c in result["checks"] if c["check"] == "data/raw/example.csv")["status"] == "error"
    assert not path.exists() if defect == "missing" else path.read_bytes() == b"changed fixture"


def test_missing_guide_blocks_without_generating_it(prepared):
    path = prepared / "docs/GUIA_DEMO_B13.md"
    path.unlink()
    assert preflight.inspect(prepared, environment=False)["verdict"] == "NO APTO"
    assert not path.exists()


def test_missing_dependency_is_reported_without_installing(prepared, monkeypatch):
    monkeypatch.setattr(preflight, "DEPENDENCIES", {"absent-demo-package": "absent_demo"})
    def missing(name):
        raise preflight.importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(preflight.importlib.metadata, "version", missing)
    result = preflight.inspect(prepared)
    assert result["verdict"] == "NO APTO"
    assert next(c for c in result["checks"] if c["check"].startswith("Dependencia"))["status"] == "error"


def test_saved_fallback_uses_standard_library_and_preserves_values(tmp_path, monkeypatch, capsys):
    (tmp_path / "reports").mkdir()
    source = "serie,modelo,mae,rmse,mase\nS,baseline,2.5,3.0,0.4\n"
    path = tmp_path / "reports/comparacion_fase2.csv"
    path.write_text(source, encoding="utf-8")
    def unexpected(*args):
        pytest.fail("Saved-results fallback imported a runtime dependency")
    monkeypatch.setattr(preflight.importlib, "import_module", unexpected)
    assert preflight.main(["--root", str(tmp_path), "--saved-results"]) == 0
    assert "S,baseline,2.5,3.0,0.4" in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == source


def test_b10_mode_only_plans_existing_positional_example():
    plan = preflight.positional_plan(ROOT)
    assert plan["real_execution_authorized"] is False
    assert (plan["horizon"], plan["step"]) == (8, 4)
    assert len(plan["origins"]) == 24 and len(plan["excluded"]) == 2
    assert len(plan["methods"]) == 4
    assert not any("metric" in key or "forecast" in key for key in plan)
    assert [o["cut"] for o in plan["excluded"]] == [775, 827]


@pytest.mark.skipif(not (ROOT / "data/processed/b08_demo.csv").exists(), reason="Real demo CSV is local and not versioned")
def test_real_demo_counts_and_manifest_are_consistent():
    coverage = preflight.demo_coverage(ROOT)
    assert coverage[210]["values"] == (142, 112, 150)
    assert coverage[220]["values"] == (2, 2, None)
    assert coverage[210]["calendar"] == coverage[220]["calendar"] == "unverified"


@pytest.mark.skipif(not all((ROOT / p).exists() for p in ("data/processed/b08_demo.csv", "data/processed/panel_casos.parquet")), reason="Real demonstration artifacts are local")
def test_offline_rehearsal_real_artifacts_and_session_isolation(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from app import historical_app as historical
    from app.analysis_presenter import new_state, set_source
    from app.lab_evidence import PHASES

    attempted = []
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex
    getaddrinfo = socket.getaddrinfo
    def local(host):
        if host in (None, "", "localhost", b"localhost"):
            return True
        try:
            return ipaddress.ip_address(host.decode() if isinstance(host, bytes) else host).is_loopback
        except ValueError:
            return False
    def guarded_connect(sock, address):
        if isinstance(address, tuple) and not local(address[0]):
            attempted.append(address)
            raise AssertionError("External connection forbidden during offline rehearsal")
        return connect(sock, address)
    def guarded_connect_ex(sock, address):
        if isinstance(address, tuple) and not local(address[0]):
            attempted.append(address)
            raise AssertionError("External connection forbidden during offline rehearsal")
        return connect_ex(sock, address)
    def guarded_dns(host, *args, **kwargs):
        if not local(host):
            attempted.append(host)
            raise AssertionError("External DNS forbidden during offline rehearsal")
        return getaddrinfo(host, *args, **kwargs)
    def no_fit(*args, **kwargs):
        raise AssertionError("Navigation must not run a scientific model")
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_dns)
    monkeypatch.setattr(historical, "ajustar_sarima", no_fit)
    monkeypatch.setattr(historical, "tabla_alertas", no_fit)

    def clean(page):
        assert not page.exception
    def click(page, label):
        next(b for b in page.button if b.label == label).click().run()
        clean(page)
    page = AppTest.from_file(str(ROOT / "app/platform_app.py"), default_timeout=30).run()
    clean(page)
    page.radio(key="epi_platform_nav").set_value("Laboratorio de Machine Learning").run()
    for phase in PHASES:
        clean(page)
        assert page.radio(key="epi_science_chapter_widget").value == phase.chapter
        assert page.radio(key=f"epi_science_phase_widget_{phase.chapter}").value == phase.number
        if phase.number < 12:
            click(page, "Fase siguiente →")
    page.radio(key="epi_lab_mode_widget").set_value("Vistas históricas").run()
    for view, plots in (("Panorama", 2), ("Territorio y patrones", 4), ("Pronósticos", 0), ("Señales de alerta", 0), ("Evidencia", 1)):
        page.radio(key="epi_lab_view").set_value(view).run()
        clean(page)
        assert len(page.get("plotly_chart")) == plots
    page.radio(key="epi_platform_nav").set_value("Observatorio Epidemiológico").run()
    state = new_state()
    set_source(state, (ROOT / "data/processed/b08_demo.csv").read_bytes(), "b08_demo.csv")
    assert not state["load"].blocked
    page.session_state.epi_work = state
    page.radio(key="epi_nav").set_value("Analizar datos").run()
    click(page, "Continuar a territorio")
    page.selectbox(key="epi_mun").select("76001").run()
    page.selectbox(key="epi_event").select(210).run()
    page.selectbox(key="epi_profile").select("documented-cali-2020-2021-v1").run()
    click(page, "Analizar observaciones")
    assert [p.observed_count for p in page.session_state.epi_work["result"].series.series[0].points] == [142, 112, 150]
    identity = page.session_state.epi_work["execution_key"]
    page.radio(key="epi_platform_nav").set_value("Laboratorio de Machine Learning").run()
    page.radio(key="epi_platform_nav").set_value("Observatorio Epidemiológico").run()
    clean(page)
    assert page.session_state.epi_work["execution_key"] == identity
    click(page, "Cambiar configuración")
    page.selectbox(key="epi_event").select(220).run()
    assert page.session_state.epi_work["result"] is None
    page.radio(key="epi_platform_nav").set_value("Evidencia y metodología").run()
    clean(page)
    assert not page.get("plotly_chart")
    assert any("No hay una ejecución vigente" in item.value for item in page.info)
    page.radio(key="epi_platform_nav").set_value("Observatorio Epidemiológico").run()
    click(page, "Analizar observaciones")
    result = page.session_state.epi_work["result"]
    assert [p.observed_count for p in result.series.series[0].points] == [2, 2, None]
    assert result.load_diagnostic.sha256 == preflight.ARTIFACTS["data/processed/b08_demo.csv"]
    assert not attempted


def test_cli_remains_printable_with_windows_legacy_console(tmp_path):
    import os
    import subprocess
    import sys
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/comparacion_fase2.csv").write_text(
        "serie,modelo,mae,rmse,mase\nS,baseline → observación,2.5,3.0,0.4\n", encoding="utf-8")
    environment = dict(os.environ, PYTHONIOENCODING="cp1252")
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/preflight_demo.py"),
                             "--root", str(tmp_path), "--saved-results"],
                            env=environment, capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode == 0, result.stderr
    assert "baseline → observación" in result.stdout
