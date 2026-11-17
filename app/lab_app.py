"""Interactive scientific journey; renders saved evidence without fitting models."""
from html import escape
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from app import historical_app as historical
from app.lab_evidence import (CHAPTERS, PHASES, evidence_signature, load_context,
                              phase_status, split_rows, summary_rows)


@st.cache_data(show_spinner=False)
def cached_context(root, signature):
    return load_context(Path(root))


def choose_phase(number):
    phase = PHASES[number - 1]
    st.session_state.epi_science_chapter = phase.chapter
    st.session_state.epi_science_chapter_widget = phase.chapter
    choices = dict(st.session_state.get("epi_science_choices", {}))
    choices[phase.chapter] = number
    st.session_state.epi_science_choices = choices
    st.session_state[f"epi_science_phase_widget_{phase.chapter}"] = number


def chapter_changed():
    st.session_state.epi_science_chapter = st.session_state.epi_science_chapter_widget


def phase_changed(chapter):
    choices = dict(st.session_state.get("epi_science_choices", {}))
    choices[chapter] = st.session_state[f"epi_science_phase_widget_{chapter}"]
    st.session_state.epi_science_choices = choices


def open_history(view):
    st.session_state.epi_lab_mode = "Vistas históricas"
    st.session_state.epi_lab_mode_widget = "Vistas históricas"
    st.session_state.epi_lab_view = view


def mode_changed():
    st.session_state.epi_lab_mode = st.session_state.epi_lab_mode_widget


def status_class(status):
    return "complete" if status == "Completo con evidencia" else "pending" if status == "Pendiente" else "partial"


def render_sources(phase, context, root):
    with st.expander("Evidencia y reproducción de esta fase"):
        st.caption("Disponibilidad de archivos no equivale a fase completada. Código implementado, reporte guardado y ejecución validada son evidencias distintas.")
        st.dataframe([{"Fuente": relative, "Disponible": "Sí" if context["available"].get(relative) else "No"}
                      for relative in phase.sources], hide_index=True, width="stretch")
        st.markdown("**Cómo contrastar esta evidencia**")
        st.code(phase.reproduce, language=None)
        st.caption("Las instrucciones no se ejecutan desde esta pantalla. No sobrescribir paneles ni evaluaciones históricas.")
        for relative in phase.sources:
            if relative.endswith((".md", ".csv", ".json")) and not relative.startswith("data/raw/") and context["available"].get(relative):
                path = root / relative
                st.download_button("Descargar " + path.name, path.read_bytes(), path.name,
                                   key=f"epi_phase_{phase.number}_download_{relative}")


def render_observed_evidence(phase, context):
    """Present values from artifacts; never compute forecast error or predictions."""
    if phase.number == 2:
        st.markdown("**Verificación local de los originales**")
        st.dataframe([{k: row[k] for k in ("Archivo", "Estado")} for row in context["sources"]], hide_index=True, width="stretch")
        with st.expander("Huellas SHA-256 y referencia B02"):
            st.dataframe(context["sources"], hide_index=True, width="stretch")
        st.caption("Completo se refiere a la recolección de los originales conservados; no a su aceptación como carga nueva ni a cobertura epidemiológica completa.")
    elif phase.number == 4:
        report = context["ingest"]
        fields = ("filas_crudas", "filas_tras_excluir_ajenas", "filas_validas_para_panel")
        if report and all(type(report.get(key)) is int and report[key] >= 0 for key in fields):
            st.dataframe([{"Etapa histórica": label, "Registros": report[key]} for label, key in zip(
                ("Originales", "Tras excluir eventos ajenos", "Aceptados por reglas heredadas"), fields)], hide_index=True, width="stretch")
            st.caption("Cifras del reporte guardado; incluyen el universo territorial heredado. No se reinterpretan como el contrato B03.")
        else:
            st.info("Reporte de limpieza ausente o incompleto. No se reconstruye el embudo con cifras de sustitución.")
    elif phase.number == 5:
        st.markdown('<div class="epi-lab-flow"><span>Conteos observados</span><b>→</b><span>log1p</span><b>→</b><span>SARIMAX</span><b>→</b><span>expm1 · ≥ 0</span></div>', unsafe_allow_html=True)
        st.caption("Esquema del método implementado; no representa una ejecución ni una transformación óptima demostrada.")
    elif phase.number == 6:
        rows = split_rows(context)
        if not rows:
            st.info("Partición no disponible o inválida. No se asignan cortes alternativos en el recorrido científico.")
        else:
            figure = go.Figure()
            for row, color in zip(rows, ("#276D70", "#D59A70", "#8DCABA")):
                figure.add_trace(go.Bar(x=[row["Semanas configuradas"]], y=["Malla histórica"], base=[row["Inicio (posición)"]],
                    orientation="h", name=row["Conjunto"], marker_color=color,
                    text=[str(row["Semanas configuradas"])], textangle=0, textposition="inside",
                    hovertemplate=f'{row["Conjunto"]}<br>Posiciones {row["Inicio (posición)"]}–{row["Fin inclusivo"]}<extra></extra>'))
            figure.update_layout(barmode="overlay", height=230, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  xaxis_title="Posición en la malla técnica; no calendario epidemiológico oficial", yaxis=dict(visible=False), margin=dict(l=10,r=10,t=40,b=40),
                                  legend=dict(orientation="h",y=1.3), font=dict(color="#102F3A"))
            st.plotly_chart(figure, width="stretch", theme=None, config={"displaylogo": False})
            with st.expander("Cortes configurados"):
                st.dataframe(rows, hide_index=True, width="stretch")
    elif phase.number in (7, 8, 10, 11):
        comparison = context["comparison"]
        if comparison is None:
            st.info("No hay una comparación guardada válida disponible. No se muestran métricas de sustitución.")
        else:
            st.caption(f"Archivo de evaluación disponible: {len(comparison)} resultados · {comparison['serie'].nunique()} series · {comparison['modelo'].nunique()} métodos. Ventana histórica 2022; horizonte 52 semanas según el script.")
            if phase.number in (7, 10):
                summary = summary_rows(context)
                st.markdown("**Resultados guardados por método**")
                st.dataframe(summary.rename(columns={"mae": "MAE medio", "rmse": "RMSE medio", "mase": "MASE medio"}).round(4), width="stretch")
                st.caption("Promedios descriptivos entre las series del archivo. MAE/RMSE dependen de la escala; MASE usa referencia estacional de entrenamiento. No es selección de ganador por validación.")
            if phase.number == 10:
                historical.render_comparison()
        if phase.number == 11:
            rolling = (context["split"] or {}).get("rolling_origin")
            if isinstance(rolling, dict):
                st.markdown("**Origen móvil: configuración, no ejecución**")
                st.dataframe([{"Parámetro": key, "Valor configurado": str(rolling[key])}
                              for key in ("initial", "horizon", "step") if key in rolling], hide_index=True, width="stretch")
    elif phase.number == 12:
        st.dataframe([
            {"Elemento": "Aplicación local", "Estado comprobable": "Código disponible" if context["available"].get("app/platform_app.py") else "Código ausente"},
            {"Elemento": "Inferencia B06/B07 desde B08", "Estado comprobable": "No habilitada; contratos temporales pendientes"},
            {"Elemento": "Modelo entrenado persistido", "Estado comprobable": "Sin evidencia entregada de artefacto versionado"},
            {"Elemento": "Despliegue público", "Estado comprobable": "Sin evidencia entregada"},
        ], hide_index=True, width="stretch")


def render_journey():
    root = historical.RAIZ
    context = cached_context(str(root), evidence_signature(root))
    statuses = {phase.number: phase_status(phase, context) for phase in PHASES}
    complete = sum(value == "Completo con evidencia" for value in statuses.values())
    st.markdown(f'<section class="epi-lab-hero"><div class="epi-eyebrow">LABORATORIO / RECORRIDO CIENTÍFICO</div><h1>Doce fases.<br><em>Una cadena de evidencia.</em></h1><p>Del problema al despliegue: explora las decisiones, los resultados disponibles y las preguntas que siguen abiertas.</p><div class="epi-lab-scope">12 fases documentadas · {complete} completa con evidencia local · {sum(v == "Parcial" for v in statuses.values())} parciales · 1 pendiente</div></section>', unsafe_allow_html=True)
    st.caption("Este recorrido describe experimentos del proyecto, no la carga actual del Observatorio. Documentar las doce fases no significa haber completado las doce.")
    cards = ''.join(f'<article><span>0{number}</span><strong>{escape(title)}</strong><small>{sum(p.chapter == number for p in PHASES)} fases · {escape(body)}</small></article>' for number, (title, body) in CHAPTERS.items())
    st.markdown('<div class="epi-lab-chapters">' + cards + '</div>', unsafe_allow_html=True)
    if "epi_science_chapter_widget" not in st.session_state:
        st.session_state.epi_science_chapter_widget = st.session_state.get("epi_science_chapter", 1)
    chapter = st.radio("Capítulo científico", list(CHAPTERS), format_func=lambda n: f"{n}. {CHAPTERS[n][0]}",
                       horizontal=True, key="epi_science_chapter_widget", on_change=chapter_changed)
    options = [p.number for p in PHASES if p.chapter == chapter]
    key = f"epi_science_phase_widget_{chapter}"
    if key not in st.session_state:
        st.session_state[key] = st.session_state.get("epi_science_choices", {}).get(chapter, options[0])
    number = st.radio("Fase del capítulo", options, format_func=lambda n: f"{n:02d} · {PHASES[n-1].title}",
                      horizontal=True, key=key, on_change=phase_changed, args=(chapter,))
    phase = PHASES[number - 1]
    status = statuses[number]
    st.markdown(f'<section class="epi-lab-phase"><div><span class="epi-eyebrow">FASE {number:02d} / 12</span><h2>{escape(phase.title)}</h2><p>{escape(phase.objective)}</p></div><span class="epi-lab-badge {status_class(status)}">{escape(status)}</span></section>', unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("### Metodología utilizada")
        st.write(phase.methodology)
    with right:
        st.markdown("### Resultado comprobado y alcance")
        st.write(phase.result)
    render_observed_evidence(phase, context)
    st.markdown(f'<section class="epi-lab-limits"><span>CONDICIONES DE INTERPRETACIÓN</span><p>{escape(phase.limitations)}</p><strong>Qué falta concretamente</strong><p>{escape(phase.pending)}</p></section>', unsafe_allow_html=True)
    if phase.number == 9:
        st.warning("Ajuste de hiperparámetros pendiente: no hay evidencia ejecutada de búsqueda. No se genera una curva de optimización.")
    if phase.view:
        st.button("Explorar vista histórica · " + phase.view, key=f"epi_science_open_{number}", on_click=open_history, args=(phase.view,))
        st.caption("Abre la visualización existente. Pronósticos y señales mantienen sus botones explícitos de cálculo.")
    render_sources(phase, context, root)
    with st.expander("Mapa de evidencia de las doce fases"):
        st.dataframe([{"Fase": p.number, "Capítulo": CHAPTERS[p.chapter][0], "Objetivo": p.title, "Estado": statuses[p.number],
                       "Archivos disponibles": f"{sum(context['available'].get(s, False) for s in p.sources)}/{len(p.sources)}"}
                      for p in PHASES], hide_index=True, width="stretch")
    if context["errors"]:
        with st.expander("Incidencias de lectura de evidencia"):
            for error in context["errors"]:
                st.warning(error)
    prev, nxt = st.columns(2)
    prev.button("← Fase anterior", disabled=number == 1, on_click=choose_phase, args=(max(1, number-1),), key="epi_science_prev")
    nxt.button("Fase siguiente →", disabled=number == 12, on_click=choose_phase, args=(min(12, number+1),), key="epi_science_next")


def render():
    if "epi_lab_mode_widget" not in st.session_state:
        st.session_state.epi_lab_mode_widget = st.session_state.get("epi_lab_mode", "Recorrido científico")
    mode = st.radio("Explorar el Laboratorio", ("Recorrido científico", "Vistas históricas"), horizontal=True,
                    key="epi_lab_mode_widget", on_change=mode_changed)
    if mode == "Recorrido científico":
        render_journey()
    else:
        st.markdown("## Laboratorio de Machine Learning · Vistas históricas")
        st.caption("Las cinco vistas originales permanecen disponibles. Vuelve al recorrido científico para revisar su trazabilidad.")
        view = st.radio("Recorrido histórico", historical.VIEWS, horizontal=True, key="epi_lab_view")
        historical.render(view)
