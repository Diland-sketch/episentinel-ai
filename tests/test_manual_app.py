"""Native form flow, session counters and model isolation."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from tests.test_analysis_app import loaded_app,button
from tests.test_platform_app import prohibit_models
from app import retrospective_app

ROOT=Path(__file__).resolve().parents[1]


def form():
    page=AppTest.from_file(str(ROOT/"app/platform_app.py"),default_timeout=25).run()
    button(page,"Comenzar análisis").click().run()
    page.radio(key="epi_entry_mode").set_value("Registro manual").run()
    assert not page.exception
    return page


def submit(page,count="0",week="52"):
    page.text_input(key="epi_manual_mun").set_value("76001")
    page.selectbox(key="epi_manual_event").select(210)
    page.text_input(key="epi_manual_year").set_value("2020")
    page.text_input(key="epi_manual_week").set_value(week)
    page.text_input(key="epi_manual_count").set_value(count)
    button(page,"Agregar registro manual").click().run()
    assert not page.exception


def metrics(page):return {m.label:m.value for m in page.metric}


def test_real_form_multiple_records_invalid_and_duplicate_counters(monkeypatch):
    prohibit_models(monkeypatch)
    page=form()
    assert metrics(page)["Total del conjunto activo"]=="0"
    assert [m.label for m in page.metric][:3]==["Total del conjunto activo","Válidos entregados por B04","Intentos manuales rechazados"]
    details=next(e for e in page.expander if e.label=="Desglose CSV/manual y procedencia de la sesión")
    assert [m.label for m in details.metric]==["Registros CSV activos","Manuales agregados activos","Rechazados / pendientes activos"]
    submit(page,count="-1")
    assert metrics(page)["Total del conjunto activo"]=="0" and page.error
    submit(page)
    assert metrics(page)["Total del conjunto activo"]=="1"
    submit(page,week="53",count="4")
    assert metrics(page)["Manuales agregados activos"]=="2"
    submit(page,week="53",count="9")
    assert metrics(page)["Total del conjunto activo"]=="2" and page.error
    assert metrics(page)["Intentos manuales rechazados"]=="2"
    assert not page.get("plotly_chart")


def test_manual_analysis_zero_gap_new_session_and_direct_forecast(monkeypatch):
    prohibit_models(monkeypatch)
    def unexpected(*a,**k):raise AssertionError("Navigation trained a model")
    monkeypatch.setattr(retrospective_app,"execute_bounded",unexpected)
    page=form();submit(page);submit(page,week="53",count="4")
    original_id=page.session_state.epi_inputs["session_id"]
    button(page,"Continuar a territorio").click().run()
    page.selectbox(key="epi_mun").select("76001").run()
    page.selectbox(key="epi_event").select(210).run()
    page.selectbox(key="epi_profile").select("documented-cali-2020-2021-v1").run()
    button(page,"Analizar observaciones").click().run()
    assert not page.exception
    assert [p.observed_count for p in page.session_state.epi_work["result"].series.series[0].points]==[0,4,None]
    page.radio(key="epi_platform_nav").set_value("Laboratorio de Machine Learning").run()
    page.radio(key="epi_platform_nav").set_value("Observatorio Epidemiológico").run()
    assert page.session_state.epi_work["result"].status=="completed"
    button(page,"Cambiar fuente o agregar registros").click().run()
    page.radio(key="epi_entry_mode").set_value("Cargar CSV").run()
    assert page.session_state.epi_work["result"] is None
    page.radio(key="epi_entry_mode").set_value("Registro manual").run()
    assert metrics(page)["Total del conjunto activo"]=="2"
    button(page,"Nueva sesión del Observatorio").click().run()
    assert metrics(page)["Total del conjunto activo"]=="0"
    assert page.session_state.epi_inputs["session_id"]!=original_id
    assert page.session_state.epi_work["payload"] is None
    page.radio(key="epi_nav").set_value("Inicio").run()
    button(page,"Abrir pronóstico retrospectivo").click().run()
    assert not page.exception and page.radio(key="epi_demo_section").value=="Pronóstico retrospectivo"
    assert not page.get("plotly_chart")


def test_csv_flow_and_manual_combination_have_consistent_ui_counts():
    page=loaded_app()
    assert metrics(page)["Registros CSV activos"]=="2"
    page.radio(key="epi_entry_mode").set_value("Registro manual").run()
    assert metrics(page)["Total del conjunto activo"]=="0"
    assert any("2 registros del CSV y 0 manuales aceptados" in c.value for c in page.caption)
    page.checkbox(key="epi_manual_include").check().run()
    assert not page.exception and metrics(page)["Total del conjunto activo"]=="2"
    submit(page,count="0")
    assert page.error and metrics(page)["Total del conjunto activo"]=="2"
