"""Unified Platform I2. No historical model is executed on navigation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
from app.analysis_app import main as render_observatory
from app.analysis_components import section, render_evidence
from app.analysis_presenter import ensure_current, make_config, read_profiles
from app.historical_app import render_comparison, render_notice
from app.lab_app import render as render_lab

DESTINATIONS = ("Observatorio Epidemiológico", "Laboratorio de Machine Learning", "Evidencia y metodología")
DOCUMENTS = (
    ("Demostración B08", "docs/DEMO_B08.md"),
    ("Procedencia de los datos", "docs/PROCEDENCIA_B02.md"),
    ("Contrato de series B03", "docs/CONTRATO_SERIES_B03.md"),
    ("Contrato CSV", "docs/CONTRATO_CSV.md"),
    ("Contrato de carga B04", "docs/B04_CSV_LOADER.md"),
    ("Contrato de ejecución B05", "docs/CONTRATO_PIPELINE_B05.md"),
    ("Contrato de señales B07", "docs/CONTRATO_SENALES_B07.md"),
    ("Decisiones técnicas históricas", "docs/DECISIONES_TECNICAS.md"),
    ("Estado histórico del proyecto", "docs/ESTADO_DEL_PROYECTO.md"),
    ("Plataforma I1", "docs/PLATAFORMA_I1.md"),
    ("Laboratorio de doce fases · I2", "docs/PLATAFORMA_I2.md"),
)


def session_evidence():
    state = st.session_state.get("epi_work")
    if state is None:
        st.info("Aún no hay una ejecución vigente del Observatorio.")
        return
    config = None
    try:
        profiles = {p["id"]: p for p in read_profiles(ROOT / "configs/ui_period_grids.json")}
        selection = state["selection"]
        if all(v is not None for v in selection.values()) and selection["profile"] in profiles:
            config = make_config(selection["municipality"], selection["event"], profiles[selection["profile"]])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    ensure_current(state, config)
    if state["result"] is None:
        st.info("No hay una ejecución vigente. Completa el recorrido del Observatorio.")
    else:
        render_evidence(state["result"])


def main():
    st.set_page_config(page_title="EpiSentinel AI · Plataforma", page_icon="◈", layout="wide", initial_sidebar_state="collapsed")
    st.markdown((ROOT / "app/analysis_styles.css").read_text(encoding="utf-8"), unsafe_allow_html=True)
    st.markdown('<div class="epi-brand"><span class="epi-mark">E</span><div>EpiSentinel <b>AI</b><small>VIGILANCIA CON EVIDENCIA</small></div><span class="epi-academic">PLATAFORMA I2 · ACADÉMICA</span></div>', unsafe_allow_html=True)
    destination = st.radio("Ambiente de trabajo", DESTINATIONS, horizontal=True, key="epi_platform_nav", label_visibility="collapsed")
    if destination == DESTINATIONS[0]:
        render_observatory(embedded=True)
    elif destination == DESTINATIONS[1]:
        render_lab()
    else:
        section("TRANSPARENCIA", "Evidencia y metodología", "Consulta por separado la ejecución de la sesión, los resultados históricos y sus contratos.")
        source = st.radio("Fuente de evidencia", ("Sesión del Observatorio", "Resultados históricos", "Metodología y contratos"), horizontal=True, key="epi_evidence_source")
        if source == "Sesión del Observatorio":
            session_evidence()
        elif source == "Resultados históricos":
            render_notice()
            render_comparison()
        else:
            st.info("B06-I1 ofrece dos baselines sobre una serie fechada compatible. B03 entrega periodos sin fechas: su conexión sigue pendiente del calendario. B07 conserva tres estados; canal y SARIMA un paso no están integrados allí. El Observatorio I1 no ejecuta estos servicios.")
            for title, relative in DOCUMENTS:
                with st.expander(title):
                    path = ROOT / relative
                    if path.exists():
                        st.caption(relative)
                        st.download_button("Descargar documento", path.read_bytes(), path.name, "text/markdown", key="epi_doc_" + path.stem)
                        st.markdown(path.read_text(encoding="utf-8"))
                    else:
                        st.info("Documento no disponible en esta instalación.")


if __name__ == "__main__":
    main()
