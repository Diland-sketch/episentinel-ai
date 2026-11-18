"""New guided B08 experience. Historical app/streamlit_app.py remains unchanged."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
from app.session_input import (CSV_MODE, MANUAL_MODE, new_inputs, observe_work, change_csv,
                               change_mode, combine, clear_active)
from app.input_components import render_manual, render_counters, render_partition_context

from app.analysis_components import (hero, progress, render_evidence, render_result, section,
                                     credibility_band, panel_heading)
from app.analysis_presenter import (
    EVENT_LABELS, ensure_current, execute, invalidate, issue_rows, make_config,
    new_state, read_profiles, set_selection, set_source,
)


def main(embedded=False):
    if not embedded:
        st.set_page_config(page_title="EpiSentinel AI · Centro de vigilancia", page_icon="◈",
                       layout="wide", initial_sidebar_state="collapsed")
    if not embedded:
        st.markdown((ROOT / "app/analysis_styles.css").read_text(encoding="utf-8"), unsafe_allow_html=True)
    if "epi_work" not in st.session_state:
        st.session_state.epi_work = new_state()
    state = st.session_state.epi_work
    if "epi_inputs" not in st.session_state:
        st.session_state.epi_inputs = new_inputs()
    inputs = st.session_state.epi_inputs
    observe_work(inputs, state)
    try:
        profiles = read_profiles(ROOT / "configs/ui_period_grids.json")
        profile_error = None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        profiles, profile_error = [], str(exc)
    by_id = {p["id"]: p for p in profiles}

    def go(nav=None, step=None):
        if nav:
            st.session_state.epi_nav = nav
        if step:
            state["step"] = step

    def reset_selection():
        for key in ("epi_mun", "epi_event", "epi_profile"):
            st.session_state.pop(key, None)

    def upload_changed():
        upload = st.session_state.epi_upload
        if change_csv(inputs, state, None if upload is None else upload.getvalue(), None if upload is None else upload.name):
            reset_selection()
            st.session_state.pop("epi_manual_include", None)

    def remove_source():
        clear_active(inputs, state)
        reset_selection()
        st.session_state.pop("epi_upload", None)
        st.session_state.pop("epi_manual_include", None)

    def entry_changed():
        change_mode(inputs, state, st.session_state.epi_entry_mode)
        reset_selection()
        st.session_state.epi_manual_include = inputs["include_csv"]

    def combined_changed():
        if combine(inputs, state, st.session_state.epi_manual_include):
            reset_selection()
        st.session_state.epi_manual_include = inputs["include_csv"]

    def restart_observatory():
        state.clear()
        state.update(new_state())
        inputs.clear()
        inputs.update(new_inputs())
        for key in ("epi_upload", "epi_entry_mode", "epi_manual_include", "epi_mun", "epi_event", "epi_profile",
                    "epi_manual_mun", "epi_manual_event", "epi_manual_year", "epi_manual_week", "epi_manual_count"):
            st.session_state.pop(key, None)
        st.session_state.epi_nav = "Analizar datos"

    def open_retrospective():
        st.session_state.epi_platform_nav = "Laboratorio de Machine Learning"
        st.session_state.epi_lab_mode = "Demostración aplicada"
        st.session_state.epi_lab_mode_widget = "Demostración aplicada"
        st.session_state.epi_demo_section = "Pronóstico retrospectivo"

    def open_planner():
        st.session_state.epi_platform_nav = "Laboratorio de Machine Learning"
        st.session_state.epi_lab_mode = "Demostración aplicada"
        st.session_state.epi_lab_mode_widget = "Demostración aplicada"
        st.session_state.epi_demo_section = "Diseño temporal"

    def selection_changed(field, key):
        set_selection(state, field, st.session_state[key])

    def selected_config():
        selection = state["selection"]
        if not all(v is not None for v in selection.values()) or selection["profile"] not in by_id:
            return None
        return make_config(selection["municipality"], selection["event"], by_id[selection["profile"]])

    try:
        cfg = selected_config()
    except (ValueError, TypeError, KeyError):
        cfg = None
    ensure_current(state, cfg)
    if not embedded:
        st.markdown('<div class="epi-brand"><span class="epi-mark">E</span><div>EpiSentinel <b>AI</b><small>VIGILANCIA CON EVIDENCIA</small></div><span class="epi-academic">PROTOTIPO ACADÉMICO</span></div>', unsafe_allow_html=True)
    if embedded and "epi_nav" not in st.session_state:
        st.session_state.epi_nav = st.session_state.get("epi_observatory_nav", "Inicio")
    with st.container(key="epi_secondary_nav"):
        nav = st.radio("Recorrido del Observatorio" if embedded else "Navegación principal", ("Inicio", "Analizar datos", "Evidencia"),
                       horizontal=True, key="epi_nav", label_visibility="collapsed")
    if embedded:
        st.session_state.epi_observatory_nav = nav
    st.markdown('<div class="epi-rule"></div>', unsafe_allow_html=True)
    if nav == "Inicio":
        hero()
        start, forecast = st.columns(2)
        start.button("Comenzar análisis", type="primary", on_click=go, kwargs=dict(nav="Analizar datos", step="Datos"))
        if embedded:
            forecast.button("Abrir pronóstico retrospectivo", on_click=open_retrospective,
                            help="Experimento histórico independiente del conjunto del Observatorio; entrar no entrena.")
        section("DE LOS REGISTROS A SU CONTEXTO", "Un recorrido claro para preguntas importantes.",
                "Carga un CSV o registra conteos manuales, elige un municipio y explora su evolución con la calidad y las limitaciones a la vista.")
        credibility_band()
        with st.container(border=True, key="epi_method_panel"):
            panel_heading("UN RECORRIDO CON FUNDAMENTO", "La evidencia no es un anexo.",
                          "Cada lectura conserva el vínculo entre archivo, configuración y observaciones. La profundidad científica está disponible sin interrumpir la comprensión.")
            st.write("Validación estructural · Series por evento · Cobertura explícita · Pruebas de integración documentadas")
    elif nav == "Evidencia":
        section("TRANSPARENCIA", "La evidencia también forma parte del resultado.",
                "Esta experiencia muestra observaciones, no brotes confirmados ni predicciones.")
        if state["result"] is not None:
            render_evidence(state["result"])
        else:
            st.info("Aún no hay una ejecución vigente. Completa el recorrido para consultar su evidencia.")
        with st.expander("Metodología y límites del prototipo", expanded=True):
            st.write("CSV canónico → validación B04 → ejecución B05 → series por periodos B03.")
            st.write("Una semana ausente no se interpreta como cero. S53 se conserva sin inventar fechas. La elegibilidad de modelos no se ha evaluado.")
            st.write("Las nuevas cargas no acreditan por sí solas procedencia institucional. Para los originales del proyecto se documentó el conjunto 4hyg-wa9d del Portal Nacional de Datos Abiertos, atribuido al INS, con licencia actual CC BY-SA 4.0.")
            st.link_button("Consultar conjunto de referencia", "https://www.datos.gov.co/Salud-y-Protecci-n-Social/Datos-de-Vigilancia-en-Salud-P-blica-de-Colombia/4hyg-wa9d/about_data")
    else:
        progress(state["step"])
        if state["step"] == "Datos":
            section("01 / DATOS", "Empieza por una fuente clara.", "Carga un CSV o registra observaciones manuales. Ambos usan el contrato canónico B04.")
            if "epi_entry_mode" not in st.session_state:
                st.session_state.epi_entry_mode = inputs["mode"]
            st.radio("Método de ingreso", (CSV_MODE, MANUAL_MODE), horizontal=True,
                     key="epi_entry_mode", on_change=entry_changed)
            st.caption("Cambiar de fuente invalida la lectura anterior. CSV y manual no se mezclan automáticamente.")
            with st.container(border=True, key="epi_upload_panel"):
                if inputs["mode"] == CSV_MODE:
                    st.file_uploader("Archivo CSV canónico", type=["csv"], key="epi_upload", on_change=upload_changed,
                                     help="UTF-8 y cinco columnas: cod_mun, ano, semana, cod_eve, conteo.")
                    st.download_button("Descargar plantilla de encabezados", "cod_mun,ano,semana,cod_eve,conteo\n".encode(), "plantilla_episentinel.csv", "text/csv")
                    st.caption("La plantilla no contiene observaciones. El archivo cargado se conserva solo en esta sesión al navegar.")
                    demo = ROOT / "data/processed/b08_demo.csv"
                    with st.expander("Demostración con observaciones reales"):
                        st.write("Derivación local trazable: Cali, eventos 210 y 220, tres periodos documentados. No contiene conteos simulados ni un calendario oficial.")
                        if demo.exists():
                            st.download_button("Descargar CSV real de demostración", demo.read_bytes(), "b08_demo.csv", "text/csv")
                            st.caption("Descarga este archivo y selecciónalo en el control de carga. Licencia de datos de referencia: CC BY-SA 4.0; transformaciones documentadas en DEMO_B08.md.")
                        else:
                            st.info("El archivo real de demostración aún no está preparado en esta instalación. Consulta docs/DEMO_B08.md.")
                    if inputs["manual_rows"]:
                        st.caption(f"{len(inputs['manual_rows'])} registros manuales conservados en memoria, fuera del conjunto CSV activo.")
                else:
                    csv_ready = inputs["csv_load"] is not None and not inputs["csv_load"].blocked
                    if "epi_manual_include" not in st.session_state:
                        st.session_state.epi_manual_include = inputs["include_csv"]
                    st.checkbox("Combinar explícitamente con el CSV aceptado", key="epi_manual_include",
                                disabled=not csv_ready, on_change=combined_changed,
                                help="Revalida todas las claves CSV + manuales con B04; se rechaza cualquier duplicado o conflicto.")
                    if inputs["include_csv"]:
                        st.info("Conjunto combinado autorizado: CSV validado + registros manuales. El conjunto completo se revalida al agregar.")
                    else:
                        st.caption("Solo registros manuales; ningún archivo ni registro histórico se suma al conjunto.")
                    render_manual(inputs, state, reset_selection)
                loaded = state["load"]
                if state["error"]:
                    st.error("No se pudo leer el archivo. Intenta cargarlo de nuevo.")
                if loaded:
                    st.write("**Archivo actual:**" if inputs["mode"] == CSV_MODE else "**Fuente lógica en memoria:**", state["filename"])
                    if loaded.blocked:
                        st.error("Hay problemas que corregir. El archivo no puede pasar al análisis.")
                        st.dataframe(issue_rows(loaded.report), hide_index=True, width="stretch")
                        with st.expander("Diagnóstico técnico original"):
                            st.json(loaded.report)
                    else:
                        st.success("Archivo aceptado. Puedes seleccionar territorio y evento." if inputs["mode"] == CSV_MODE else "Conjunto manual aceptado por B04. Puedes seleccionar territorio y evento.")
                        st.button("Continuar a territorio", type="primary", on_click=go, kwargs=dict(step="Territorio"))
                    st.button("Retirar archivo" if inputs["mode"] == CSV_MODE else "Vaciar registros manuales", on_click=remove_source)
            render_counters(inputs, state)
        elif state["step"] == "Territorio":
            render_counters(inputs, state)
            loaded = state["load"]
            if not loaded or loaded.blocked:
                st.warning("Primero necesitas un archivo aceptado.")
                st.button("Volver a datos", on_click=go, kwargs=dict(step="Datos"))
            else:
                section("02 / TERRITORIO", "Una selección explícita. Una lectura más precisa.", "Elige un municipio y un evento. No se suman categorías automáticamente.")
                with st.container(border=True, key="epi_config_panel"):
                    panel_heading("02", "Define el contexto de tu lectura.", "Selecciona territorio, evento y una configuración temporal con procedencia. Ninguna categoría se combina automáticamente.")
                    municipalities = sorted({r["cod_mun"] for r in loaded.data})
                    if state["selection"]["municipality"] not in municipalities:
                        set_selection(state, "municipality", None)
                    selector_columns = st.columns(2, gap="large")
                    with selector_columns[0]:
                        options = [("municipality", "epi_mun", "Municipio · código", municipalities, None)]
                        for field, key, label, values, formatter in options:
                            if key not in st.session_state:
                                st.session_state[key] = state["selection"][field]
                            st.selectbox(label, values, index=None, key=key, on_change=selection_changed,
                                         args=(field, key), placeholder="Selecciona un municipio")
                    mun = state["selection"]["municipality"]
                    events = sorted({r["cod_eve"] for r in loaded.data if r["cod_mun"] == mun})
                    with selector_columns[1]:
                        if state["selection"]["event"] not in events:
                            set_selection(state, "event", None)
                            st.session_state.pop("epi_event", None)
                        if "epi_event" not in st.session_state:
                            st.session_state.epi_event = state["selection"]["event"]
                        st.selectbox("Evento", events, index=None, format_func=lambda e: EVENT_LABELS[e], key="epi_event",
                                     on_change=selection_changed, args=("event", "epi_event"), placeholder="Selecciona un evento", disabled=not events)
                    if "epi_profile" not in st.session_state:
                        st.session_state.epi_profile = state["selection"]["profile"] if state["selection"]["profile"] in by_id else None
                    st.selectbox("Periodos de análisis", list(by_id), index=None, format_func=lambda p: by_id[p]["label"],
                                 key="epi_profile", on_change=selection_changed, args=("profile", "epi_profile"),
                                 placeholder="Selecciona una configuración del equipo", disabled=not profiles)
                    if profile_error:
                        st.warning("La configuración temporal no está disponible. No se puede iniciar el análisis.")
                    selected_profile = by_id.get(state["selection"]["profile"])
                    if selected_profile:
                        st.info("Malla provisional: solo los periodos declarados. No se asignan fechas ni se acredita continuidad oficial.")
                        st.write("**Procedencia:**", selected_profile["calendar_metadata"]["source"])
                        st.caption(f"Versión: {selected_profile['calendar_metadata']['version']} · Verificación: {'pendiente' if selected_profile['calendar_metadata']['verification'] == 'unverified' else 'declarada con evidencia'}")
                    st.caption("Código municipal sintácticamente válido; validación con catálogo oficial pendiente.")
                cfg = selected_config()
                def analyse():
                    try:
                        execute(state, selected_config())
                    except (ValueError, TypeError) as exc:
                        invalidate(state)
                        state["error"] = str(exc)
                st.button("Analizar observaciones", type="primary", disabled=cfg is None, on_click=analyse)
                if state["error"]:
                    st.error(state["error"])
                st.button("Volver a datos", on_click=go, kwargs=dict(step="Datos"))
        else:
            render_counters(inputs, state)
            if state["result"] is None:
                st.info("No hay resultados vigentes. Completa la configuración y vuelve a ejecutar.")
            else:
                render_result(state["result"])
            config_action, source_action = st.columns(2)
            config_action.button("Cambiar configuración", on_click=go, kwargs=dict(step="Territorio"))
            source_action.button("Cambiar fuente o agregar registros", on_click=go, kwargs=dict(step="Datos"))
    if nav != "Inicio":
        render_partition_context(inputs, state, open_planner if embedded else None)
        st.button("Nueva sesión del Observatorio", on_click=restart_observatory, key="epi_new_observatory")
    st.markdown('<footer class="epi-footer"><strong>EpiSentinel AI</strong><span>Equipo DKK · Prototipo académico</span><span>Observaciones con contexto. Límites siempre visibles.</span></footer>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
