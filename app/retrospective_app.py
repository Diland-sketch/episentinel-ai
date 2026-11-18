"""Explicit historical experiment UI. B03/B05 Observatory is never a data source."""
import json
from pathlib import Path
import plotly.graph_objects as go
import streamlit as st
from app.retrospective import ROOT,load_panel,candidates,allowed_plan,prepare,execute_bounded,evidence
from app.visual_theme import style_figure

LABELS={"ultimo_valor":"Último valor","ingenua_estacional":"Ingenua estacional",
        "sarima_sin_estacional":"SARIMA no estacional","sarima_estacional":"SARIMA estacional"}


@st.cache_data(show_spinner=False)
def cached_panel(root,signature):return load_panel(Path(root))


def figure(record):
    request=record["request"]; rows=record["evaluation"]["rows"]; result=record["forecast"]
    fig=go.Figure()
    start=max(0,len(request["values"])-52)
    fig.add_trace(go.Scatter(x=list(range(start,len(request["values"]))),y=request["values"][start:],
        name="Observado · entrenamiento",mode="lines",line=dict(color="#80948A"),connectgaps=False))
    x=[r["position"] for r in rows]
    if result["interval_level"] is not None and rows:
        fig.add_trace(go.Scatter(x=x+x[::-1],y=[r["hi"] for r in rows]+[r["lo"] for r in rows][::-1],
            mode="lines",fill="toself",fillcolor="rgba(39,109,112,.18)",line=dict(width=0),name=f"Intervalo nominal {result['interval_level']:.0%}",hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x,y=[r["observed"] for r in rows],mode="lines+markers",name="Observado · evaluación",
        line=dict(color="#A95C2B"),connectgaps=False))
    fig.add_trace(go.Scatter(x=[request["cut"]+i+1 for i in range(len(result["points"]))],y=[p["yhat"] for p in result["points"]],
        mode="lines+markers",name="Pronóstico B06",line=dict(color="#276D70",dash="dash"),connectgaps=False))
    fig.add_vline(x=request["cut"],line_dash="dot",line_color="#102F3A")
    fig.update_layout(title="Observado frente a pronóstico · ensayo retrospectivo",height=420,xaxis_title="Posición técnica · corte señalado",yaxis_title="Conteo histórico 210+220",yaxis_rangemode="tozero")
    return style_figure(fig)


def render(root=ROOT):
    st.markdown("### Pronóstico retrospectivo experimental · B06")
    st.warning("Experimento retrospectivo con datos históricos: no confirma brotes ni es una predicción epidemiológica validada. No utiliza el CSV de la sesión del Observatorio.")
    st.caption("Panel heredado: 210+220, ausencias completadas con cero, S53 sumada a S52. Fechas técnicas originales 7D, sin atribución a calendario epidemiológico oficial. Catálogo retrospectivo manual, sin ranking por conteos futuros; no certifica una cohorte causal. El histórico y su prueba ya fueron examinados.")
    path=Path(root)/"data/processed/panel_casos.parquet"
    try:
        stat=path.stat(); frame,digest=cached_panel(str(root),(stat.st_mtime_ns,stat.st_size))
    except (OSError,ValueError) as exc:
        st.session_state.pop("epi_ia_result",None)
        st.error("Panel incompatible o no disponible: "+str(exc));return
    preferences=st.session_state.setdefault("epi_ia_settings",{})
    for key,value in preferences.items():
        if key not in st.session_state:st.session_state[key]=value
    codes=candidates(frame)
    if not codes:st.error("No hay municipios disponibles");return
    code=st.selectbox("1 · Serie histórica municipal · código",codes,index=codes.index("76001") if "76001" in codes else 0,key="epi_ia_series")
    left,right=st.columns(2)
    method=left.selectbox("2 · Método B06",list(LABELS),index=2,format_func=LABELS.get,key="epi_ia_method")
    origins=allowed_plan().origins
    cuts=[o.cut for o in origins]
    cut=right.selectbox("Corte inclusivo permitido · B10",cuts,index=cuts.index(779),
        format_func=lambda c:f"{c} · {'validación' if c<779 else 'prueba ya explorada'} · {frame.columns[c].date()} (técnica)",key="epi_ia_cut")
    preferences.update({"epi_ia_series":code,"epi_ia_method":method,"epi_ia_cut":cut})
    st.caption("Horizonte fijo: 8 posiciones · paso de orígenes 4 · límites exclusivos 728/780/832. Entrenamiento [0, corte+1). Objetivos posteriores solo para evaluación; no se eligen hiperparámetros desde esta pantalla. Una configuración distinta no hereda métricas de un ensayo anterior.")
    try: request=prepare(frame,digest,code,cut,method)
    except ValueError as exc:
        st.session_state.pop("epi_ia_result",None);st.error(str(exc));return
    saved=st.session_state.get("epi_ia_result")
    if saved and saved["request"]["request_id"]!=request["request_id"]:
        st.session_state.pop("epi_ia_result",None);saved=None
    st.caption("Un proceso a la vez · máximo 832 observaciones de entrenamiento · horizonte 8 · límite de 45 s · sin reintentos ni cambio automático de método.")
    if st.button("3 · Ejecutar pronóstico retrospectivo",type="primary",key="epi_ia_run"):
        st.session_state.pop("epi_ia_result",None)
        with st.spinner("Ejecutando B06 sobre el prefijo. No se envían objetivos futuros al modelo…"):
            result=execute_bounded(request)
            saved=evidence(request,result,frame.loc[code])
        st.session_state.epi_ia_result=saved
    if saved is None:
        st.info("No hay un ensayo vigente para esta configuración. Pulsa Ejecutar; navegar y configurar no entrenan modelos.");return
    result=saved["forecast"]; evaluation=saved["evaluation"]
    st.markdown("#### 4 · Interpretar el ensayo ejecutado")
    st.caption(f"Solicitud {request['request_id'][:16]} · serie {code} · corte {cut} · {LABELS[method]} · 8 pasos")
    if result["status"]!="ok":
        error=result["error"] or {}
        st.error(f"{error.get('code','ERROR')}: {error.get('message','Sin resultado válido')}. No se presenta una curva parcial.")
    else:
        st.success(f"Ejecución correcta · ajuste: {result['fit_status']}")
        st.plotly_chart(figure(saved),width="stretch",theme=None)
        st.caption(f"B06 recibió {len(request['values'])} observaciones hasta el corte; la gráfica muestra las últimas 52 del entrenamiento y ocho posiciones posteriores. La banda es incertidumbre nominal, no una señal de alerta.")
        st.dataframe([{"Posición":r["position"],"Fecha técnica":r["technical_date"][:10],"Observado":r["observed"],
                       "Pronóstico B06":r["yhat"],"Límite inferior":r["lo"],"Límite superior":r["hi"]} for r in evaluation["rows"]],hide_index=True,width="stretch")
        metrics=evaluation["metrics"]
        cols=st.columns(3)
        for col,name in zip(cols,("MAE","RMSE","MASE")):
            value=metrics.get(name);col.metric(name,"No disponible" if value is None else f"{value:.4f}")
        if result["interval_level"] is not None:
            st.write(f"Intervalo nominal {result['interval_level']:.0%}; cobertura retrospectiva: {metrics.get('Cobertura intervalo nominal','No disponible')}; ancho medio: {metrics.get('Ancho medio intervalo','No disponible')}.")
        else:st.caption("Este baseline no proporciona intervalos ni diagnóstico de convergencia.")
        st.write("La línea discontinua es la estimación real devuelta por B06 desde el corte; la línea de evaluación muestra lo observado después. Menor error en estos ocho objetivos no demuestra superioridad general ni calibración epidemiológica.")
        st.caption("MASE usa únicamente el prefijo del origen, con retardo técnico heredado 52. Ningún objetivo se usa para ajustar. No se declara independencia de una prueba ya explorada ni validación causal de selección territorial.")
    for reason in evaluation["limitations"]:st.warning(reason)
    if result["diagnostics"]:
        diagnostic=result["diagnostics"]
        st.write(f"Convergencia: {diagnostic.get('converged')} · iteraciones: {diagnostic.get('iterations','no informadas')} · parámetros finitos: {diagnostic.get('parametros_finitos')}.")
    with st.expander("Diagnósticos, advertencias y procedencia del ensayo"):
        st.caption("Fechas técnicas y panel originales sin modificación. Detalle exportable, separado de reportes históricos.")
        st.json({"source_sha256":digest,"error":result["error"],"diagnostics":result["diagnostics"],"warnings":result["warnings"],"parameters":result["parameters"],"environment":saved["environment"]})
    st.download_button("Exportar evidencia completa del ensayo",json.dumps(saved,allow_nan=False,ensure_ascii=False,indent=2),
        f"ia_i1_{code}_{cut}_{method}.json","application/json",key="epi_ia_export")
