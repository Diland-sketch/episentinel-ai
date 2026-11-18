"""Native input widgets and session provenance; scientific validation belongs to B04/B05/B03."""
import json
import streamlit as st
from app.analysis_presenter import EVENT_LABELS,issue_rows
from app.session_input import MANUAL_MODE,add_manual,counters,partition_context,provenance


def render_manual(inputs,work,reset_selection):
    st.caption("Un conteo por municipio, periodo y evento. Registro declarado por el usuario; no es un paciente ni necesariamente una semana nueva.")
    with st.form("epi_manual_form",clear_on_submit=False):
        a,b,c,d,e=st.columns([1.3,2,1,1,1])
        code=a.text_input("Municipio · cod_mun",key="epi_manual_mun",help="Cinco dígitos; conserva ceros iniciales.")
        event=b.selectbox("Evento · cod_eve",list(EVENT_LABELS),index=None,format_func=EVENT_LABELS.get,key="epi_manual_event",placeholder="Selecciona evento")
        year=c.text_input("Año · ano",key="epi_manual_year",help="Cuatro dígitos, 1000–9999.")
        week=d.text_input("Semana · semana",key="epi_manual_week",help="Entero 1–53. Calendario oficial pendiente.")
        count=e.text_input("Conteo · conteo",key="epi_manual_count",help="Entero no negativo; cero explícito válido, vacío no equivale a cero.")
        submitted=st.form_submit_button("Agregar registro manual",type="primary")
    if submitted:
        if add_manual(inputs,work,dict(cod_mun=code,ano=year,semana=week,cod_eve=event,conteo=count)):
            reset_selection()
    feedback=inputs["feedback"]
    if feedback:
        (st.success if feedback["accepted"] else st.error)(feedback["message"])
        if feedback["report"]:
            st.dataframe(issue_rows(feedback["report"]),hide_index=True,width="stretch")
    if inputs["manual_rows"]:
        with st.expander("Registros manuales aceptados en esta sesión"):
            st.dataframe(inputs["manual_rows"],hide_index=True,width="stretch")


def render_counters(inputs,work):
    values=counters(inputs,work)
    with st.container(key="epi_input_summary"):
        a,b,c=st.columns(3)
        a.metric("Total del conjunto activo",values["total"])
        b.metric("Válidos entregados por B04",values["valid"])
        c.metric("Intentos manuales rechazados",values["rejected_attempts"])
        st.caption("Los registros aceptados en esta sesión no se agregan al entrenamiento histórico. Los intentos rechazados no entran al total activo.")
    with st.expander("Desglose CSV/manual y procedencia de la sesión"):
        a,b,c=st.columns(3)
        a.metric("Registros CSV activos",values["csv"])
        b.metric("Manuales agregados activos",values["manual"])
        c.metric("Rechazados / pendientes activos",f"{values['rejected']} / {values['pending']}")
        st.caption("B04 bloquea una carga CSV completa si tiene errores; las demás filas quedan pendientes. No se suman registros históricos.")
        csv_stored=inputs["csv_load"].report["summary"]["rows_read"] if inputs["csv_load"] else 0
        st.caption(f"En memoria de esta sesión: {csv_stored} registros del CSV y {len(inputs['manual_rows'])} manuales aceptados. Los contadores superiores corresponden solo al conjunto activo.")
        loaded=work["load"]
        if loaded:st.caption(f"Conjunto {inputs['session_id'][:8]} · versión local {inputs['version']} · SHA-256 {loaded.sha256[:16]}… · origen {inputs['mode']}")
    result=work["result"]
    if result is not None and result.status=="completed" and result.series is not None:
        for series in result.series.series:
            st.caption(f"Serie {result.series.territory.code}/{series.event_code}: {series.coverage.observed_periods} observaciones construidas en {series.coverage.expected_periods} posiciones declaradas; {len(series.coverage.missing_periods)} ausentes. Sin entrenamiento.")


def render_partition_context(inputs,work,on_plan=None):
    context=partition_context(inputs,work)
    with st.expander("Conjunto activo, procedencia y relación con particiones"):
        st.info("Este conjunto no está habilitado para entrenamiento. No hay posiciones elegibles acreditadas ni asignación a entrenamiento, validación o prueba.")
        for reason in context["reasons"]:st.write("• "+reason)
        if context["series"]:
            st.dataframe(context["series"],hide_index=True,width="stretch")
            st.dataframe(context["rows"],hide_index=True,width="stretch")
        st.caption("El planificador posicional B10 del Laboratorio es independiente del conjunto de esta sesión. Sus ejemplos de 832 posiciones y métricas históricas no se atribuyen a estos registros.")
        if on_plan is not None:
            st.button("Abrir planificador B10 · ejemplo independiente",on_click=on_plan,key="epi_input_plan_link")
        st.dataframe([context["identity"]],hide_index=True,width="stretch")
        origins=provenance(inputs)
        if origins:
            st.dataframe(origins[:100],hide_index=True,width="stretch")
            st.caption("Procedencia de los primeros 100 registros. La numeración enlaza el CSV activo con registros del archivo original o declaraciones manuales; no es asignación de entrenamiento.")
        if work["load"] and not work["load"].blocked:
            st.download_button("Descargar conjunto activo CSV",work["payload"],"conjunto_activo.csv","text/csv",key="epi_active_csv_download")
            manifest={"identity":context["identity"],"mode":inputs["mode"],"include_csv_explicit":inputs["include_csv"],
                "counters":counters(inputs,work),"manual_declarations":inputs["manual_rows"] if inputs["mode"]==MANUAL_MODE else [],
                "provenance_preview":origins,"provenance_rule":"CSV original logical records retain order; manual declarations follow them in insertion order. Preview limited to 100.",
                "training_assignment":None,"eligibility":"not_accredited"}
            st.download_button("Descargar manifiesto de procedencia",json.dumps(manifest,ensure_ascii=False,indent=2),
                               "procedencia_conjunto.json","application/json",key="epi_active_manifest_download")
