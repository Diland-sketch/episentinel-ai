"""Platform navigation uses synthetic artifacts; it never rewrites the historical data."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import historical_app as historical
from app.analysis_presenter import new_state, set_source, set_selection, read_profiles, make_config, execute

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "app/platform_app.py"
OBS, LAB, EVIDENCE = "Observatorio Epidemiológico", "Laboratorio de Machine Learning", "Evidencia y metodología"


@pytest.fixture
def artifacts(tmp_path, monkeypatch):
    for name in ("data/processed", "reports", "configs"):
        (tmp_path / name).mkdir(parents=True)
    dates = pd.date_range("2007-01-01", periods=832, freq="7D")
    panel = pd.DataFrame([10 + np.arange(832) % 9, 4 + np.arange(832) % 5], index=["76001", "05001"], columns=dates)
    panel.to_parquet(tmp_path / "data/processed/panel_casos.parquet")
    pd.DataFrame([
        {"cod_mun": "76001", "municipio": "Cali", "departamento": "Valle", "cod_dpto": "76"},
        {"cod_mun": "05001", "municipio": "Medellín", "departamento": "Antioquia", "cod_dpto": "05"},
    ]).to_csv(tmp_path / "data/processed/municipios.csv", index=False)
    (tmp_path / "configs/split.json").write_text(json.dumps(dict(train_end=727, val_end=779, test_end=831)))
    pd.DataFrame([
        dict(serie=series, modelo=model, mae=2., rmse=3., mase=.2)
        for series in ("NACIONAL", "76001")
        for model in ("ingenua_estacional", "ingenua_ultimo_valor", "sarima_estacional", "sarima_sin_estacional")
    ]).to_csv(tmp_path / "reports/comparacion_fase2.csv", index=False)
    monkeypatch.setattr(historical, "RAIZ", tmp_path)
    return tmp_path


def app():
    result = AppTest.from_file(str(ENTRY), default_timeout=20).run()
    assert not result.exception
    return result


def prohibit_models(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Navigation executed a historical model")
    monkeypatch.setattr(historical, "ajustar_sarima", unexpected)
    monkeypatch.setattr(historical, "tabla_alertas", unexpected)


@pytest.mark.parametrize("view,plots", [("Panorama", 2), ("Territorio y patrones", 4), ("Pronósticos", 0), ("Señales de alerta", 0), ("Evidencia", 1)])
def test_five_views_without_implicit_training(artifacts, monkeypatch, view, plots):
    prohibit_models(monkeypatch)
    page = app()
    page.radio(key="epi_platform_nav").set_value(LAB).run()
    page.radio(key="epi_lab_view").set_value(view).run()
    assert not page.exception
    assert len(page.get("plotly_chart")) == plots
    assert any("no proceden del CSV actual" in alert.value for alert in page.info)


def test_missing_panel_does_not_hide_saved_comparison_or_observatory(artifacts):
    (artifacts / "data/processed/panel_casos.parquet").unlink()
    page = app()
    page.radio(key="epi_platform_nav").set_value(LAB).run()
    assert page.warning and not page.exception
    page.radio(key="epi_lab_view").set_value("Evidencia").run()
    assert not page.exception and len(page.get("plotly_chart")) == 1
    page.radio(key="epi_platform_nav").set_value(EVIDENCE).run()
    page.radio(key="epi_evidence_source").set_value("Resultados históricos").run()
    assert not page.exception and len(page.get("plotly_chart")) == 1
    page.radio(key="epi_platform_nav").set_value(OBS).run()
    assert not page.exception and any(b.label == "Comenzar análisis" for b in page.button)


def test_missing_comparison_and_lookup_are_explicit(artifacts):
    (artifacts / "reports/comparacion_fase2.csv").unlink()
    (artifacts / "data/processed/municipios.csv").unlink()
    page = app()
    page.radio(key="epi_platform_nav").set_value(LAB).run()
    assert not page.exception and len(page.get("plotly_chart")) == 2
    page.radio(key="epi_lab_view").set_value("Evidencia").run()
    assert not page.exception and not page.get("plotly_chart")
    assert any("No está disponible" in item.value for item in page.info)


def test_observatory_result_survives_all_destinations(artifacts, monkeypatch):
    prohibit_models(monkeypatch)
    page = app()
    state = new_state()
    set_source(state, b"cod_mun,ano,semana,cod_eve,conteo\n76001,2020,52,210,0\n", "synthetic.csv")
    profile = read_profiles(ROOT / "configs/ui_period_grids.json")[0]
    for field, value in (("municipality", "76001"), ("event", 210), ("profile", profile["id"])):
        set_selection(state, field, value)
    execute(state, make_config("76001", 210, profile))
    key = state["execution_key"]
    page.session_state.epi_work = state
    page.radio(key="epi_nav").set_value("Analizar datos").run()
    assert len(page.get("plotly_chart")) == 1
    page.radio(key="epi_platform_nav").set_value(LAB).run()
    page.radio(key="epi_lab_view").set_value("Señales de alerta").run()
    page.radio(key="epi_platform_nav").set_value(EVIDENCE).run()
    assert not page.exception and page.session_state.epi_work["execution_key"] == key
    page.radio(key="epi_platform_nav").set_value(OBS).run()
    assert page.radio(key="epi_nav").value == "Analizar datos"
    assert not page.exception and len(page.get("plotly_chart")) == 1
    assert page.session_state.epi_work["execution_key"] == key
    assert page.session_state.epi_work["payload"].startswith(b"cod_mun")


def test_forecast_requires_click_and_configuration_change_hides_old_result(artifacts, monkeypatch):
    prohibit_models(monkeypatch)
    page = app()
    page.radio(key="epi_platform_nav").set_value(LAB).run()
    page.radio(key="epi_lab_view").set_value("Pronósticos").run()
    page.radio[2].set_value("Último valor").run()
    assert not page.get("plotly_chart")
    next(b for b in page.button if b.label == "Calcular pronóstico histórico").click().run()
    assert not page.exception and len(page.get("plotly_chart")) == 1
    saved = page.session_state.epi_lab_forecast[1].copy()
    page.radio(key="epi_lab_view").set_value("Panorama").run()
    page.radio(key="epi_lab_view").set_value("Pronósticos").run()
    # The model widget resets when unmounted: a different request cannot show saved results.
    assert not page.exception and not page.get("plotly_chart")
    page.radio[2].set_value("Último valor").run()
    assert len(page.get("plotly_chart")) == 1
    pd.testing.assert_frame_equal(saved, page.session_state.epi_lab_forecast[1])
    page.slider[0].set_value(12).run()
    assert not page.exception and not page.get("plotly_chart")


def test_documentation_is_available_without_any_historical_data(artifacts):
    page = app()
    page.radio(key="epi_platform_nav").set_value(EVIDENCE).run()
    page.radio(key="epi_evidence_source").set_value("Metodología y contratos").run()
    assert not page.exception
    assert any(e.label == "Contrato de señales B07" for e in page.expander)
    assert any("B06-I1" in item.value for item in page.info)


def test_embedded_b08_rejects_invalid_csv(artifacts):
    page = app()
    state = new_state()
    set_source(state, b"invalid,columns\n1,2\n", "invalid.csv")
    page.session_state.epi_work = state
    page.radio(key="epi_nav").set_value("Analizar datos").run()
    assert not page.exception and page.error
    assert page.session_state.epi_work["result"] is None
    assert not any(b.label == "Continuar a territorio" for b in page.button)
