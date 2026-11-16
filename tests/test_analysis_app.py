"""UI state tests; real browser upload is checked separately, not simulated by these tests."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.analysis_presenter import new_state, set_source

ROOT = Path(__file__).resolve().parents[1]
CSV = b"cod_mun,ano,semana,cod_eve,conteo\n76001,2020,52,210,0\n76001,2020,53,220,2\n"


def button(app, label):
    return next(b for b in app.button if b.label == label)


def loaded_app(payload=CSV):
    app = AppTest.from_file(str(ROOT / "app/analysis_app.py"), default_timeout=15).run()
    state = new_state()
    set_source(state, payload, "synthetic.csv")
    app.session_state.epi_work = state
    app.radio(key="epi_nav").set_value("Analizar datos").run()
    return app


def test_home_identity_and_native_navigation():
    app = AppTest.from_file(str(ROOT / "app/analysis_app.py"), default_timeout=15).run()
    assert not app.exception
    assert app.radio(key="epi_nav").value == "Inicio"
    assert button(app, "Comenzar análisis")
    assert any("La vigilancia comienza" in m.value for m in app.markdown)
    button(app, "Comenzar análisis").click().run()
    assert not app.exception and app.session_state.epi_work["step"] == "Datos"


def test_blocked_csv_has_no_forward_button_or_result():
    app = loaded_app(b"bad,data\n1,2\n")
    assert not app.exception and app.error
    assert not any(b.label == "Continuar a territorio" for b in app.button)
    assert app.session_state.epi_work["result"] is None


def test_selection_analysis_evidence_and_invalidation():
    app = loaded_app()
    button(app, "Continuar a territorio").click().run()
    assert button(app, "Analizar observaciones").disabled
    app.selectbox(key="epi_mun").select("76001").run()
    app.selectbox(key="epi_event").select(220).run()
    app.selectbox(key="epi_profile").select("documented-cali-2020-2021-v1").run()
    button(app, "Analizar observaciones").click().run()
    assert not app.exception
    result = app.session_state.epi_work["result"]
    assert result.status == "completed"
    assert [p.observed_count for p in result.series.series[0].points] == [None, 2, None]
    assert len(app.get("plotly_chart")) == 1
    app.radio(key="epi_nav").set_value("Evidencia").run()
    assert not app.exception
    app.radio(key="epi_nav").set_value("Analizar datos").run()
    button(app, "Cambiar configuración").click().run()
    app.selectbox(key="epi_event").select(210).run()
    assert not app.exception and app.session_state.epi_work["result"] is None
    assert not app.get("plotly_chart")


def test_remove_file_clears_session():
    app = loaded_app()
    button(app, "Retirar archivo").click().run()
    assert not app.exception
    assert app.session_state.epi_work["load"] is None


def test_absent_profile_blocks_execution(monkeypatch):
    import app.analysis_presenter as presenter
    def unavailable(path):
        raise OSError("synthetic missing configuration")
    monkeypatch.setattr(presenter, "read_profiles", unavailable)
    app = loaded_app()
    button(app, "Continuar a territorio").click().run()
    assert not app.exception
    assert button(app, "Analizar observaciones").disabled
    assert app.warning


def test_executive_results_and_evidence_keep_json_in_secondary_expander():
    app = loaded_app()
    button(app, "Continuar a territorio").click().run()
    app.selectbox(key="epi_mun").select("76001").run()
    app.selectbox(key="epi_event").select(210).run()
    app.selectbox(key="epi_profile").select("documented-cali-2020-2021-v1").run()
    button(app, "Analizar observaciones").click().run()
    assert not app.exception
    assert any("Resumen ejecutivo" in m.value for m in app.markdown)
    assert any("Qué sigue siendo incierto" in m.value for m in app.markdown)
    technical = next(e for e in app.expander if e.label == "Información técnica completa · JSON")
    assert len(technical.json) == 1 and len(app.json) == 1
    assert any("Identidad del archivo" in m.value for m in app.markdown)
    assert len(app.get("plotly_chart")) == 1
