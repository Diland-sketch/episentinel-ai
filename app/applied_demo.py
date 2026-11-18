"""Applied demonstration: saved evidence, B10 plans and recorded synthetic benchmarks."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from episentinel.evaluation.temporal_protocol import TemporalProtocol
from episentinel.evaluation.rolling_origin import plan_rolling_origin
from app.experimental_presenter import percentage_protocol, partition_rows, partition_figure, origin_rows, rolling_figure
from app.visual_theme import style_figure

METHODS = {"ingenua_ultimo_valor":"Último valor", "ingenua_estacional":"Ingenua estacional",
           "sarima_estacional":"SARIMA estacional", "sarima_sin_estacional":"SARIMA no estacional"}


def saved_results(root, context):
    st.markdown("### IA retrospectiva · resultados guardados")
    st.info("Visualización de resultados históricos. No procede del CSV de la sesión ni representa predicciones futuras.")
    frame = context["comparison"]
    if frame is None:
        st.warning("Comparación guardada ausente o inválida. No se calculan métricas de sustitución.")
        for message in context["errors"]:
            st.caption(message)
        return
    labels = {"NACIONAL":"Agregado nacional histórico · incluye Exterior"}
    lookup = root / "data/processed/municipios.csv"
    if lookup.exists():
        names = pd.read_csv(lookup,dtype={"cod_mun":str})
        if {"cod_mun","municipio"}.issubset(names.columns):
            labels.update({str(row.cod_mun):f"{row.municipio} · {row.cod_mun}" for row in names.itertuples()})
    selected = st.selectbox("Serie evaluada y guardada", list(frame["serie"].unique()),
                           format_func=lambda code:labels.get(code,code), key="epi_demo_series")
    metric = st.selectbox("Métrica guardada", ("mae","rmse","mase"),format_func=str.upper,key="epi_demo_metric")
    rows = frame.loc[frame["serie"]==selected].copy()
    rows["Método"] = rows["modelo"].map(lambda key:METHODS.get(key,key))
    fig = go.Figure(go.Bar(x=rows["Método"],y=rows[metric],marker_color="#276D70",
                         hovertemplate="%{x}<br>Valor guardado: %{y:.4f}<extra></extra>"))
    fig.update_layout(title=f"{metric.upper()} retrospectivo · {labels.get(selected,selected)}",height=350,yaxis_title=metric.upper())
    st.plotly_chart(style_figure(fig),width="stretch",theme=None)
    columns=[c for c in ("Método","mae","rmse","mase","cobertura_ic95","tiempo_s") if c in rows]
    st.dataframe(rows[columns].rename(columns={"cobertura_ic95":"Cobertura IC nominal 95 %","tiempo_s":"Ajuste registrado (s)"}),hide_index=True,width="stretch")
    st.write("Menor MAE, RMSE o MASE significa menor error en esta evaluación. MAE y RMSE conservan la escala de conteos; MASE usa la referencia estacional del entrenamiento. Un valor no garantiza desempeño fuera de esta ventana.")
    st.caption("Los intervalos no disponibles se mantienen nulos. tiempo_s=0 en los baselines es el valor predeterminado del script histórico, no una medición de tiempo nulo.")
    st.warning("No hay predicciones por periodo guardadas en los artefactos revisados. No se reconstruye una curva observada/pronosticada a partir de estas métricas.")
    st.caption("Falta un artefacto versionado por serie, método, corte y periodo con observado, predicción, intervalos disponibles, configuración y procedencia. Su generación requiere un incremento de evaluación autorizado.")
    st.markdown("**Qué implementa la IA del proyecto:** SARIMA ajusta parámetros de un modelo de series temporales; los baselines sirven como referencias. Esta pantalla compara sus errores guardados, no ejecuta aprendizaje ni un modelo epidemiológico oficialmente validado.")
    st.caption("Experimento: entrenamiento 2007–2021, prueba retrospectiva de 52 posiciones en 2022. La selección territorial usó el histórico completo; 2022 ya fue examinado. No se afirma evaluación libre de fuga ni superioridad general de SARIMA. Panel heredado 210+220, faltantes rellenados con cero y S53 plegada; esas reglas no se aplican a B08.")
    path = root / "reports/comparacion_fase2.csv"
    st.caption(f"Fuente: reports/comparacion_fase2.csv · SHA-256 {hashlib.sha256(path.read_bytes()).hexdigest()}")


def experimental_design():
    st.markdown("### Diseña un experimento temporal")
    st.info("Configurador sin ejecución · B10. No cambia el experimento histórico, no selecciona hiperparámetros ni genera métricas.")
    st.caption("Malla de planificación independiente de la serie histórica y del CSV de sesión. 832 es el ejemplo posicional de B10, no un calendario ni una configuración ya evaluada.")
    total = st.number_input("Total de posiciones declaradas",min_value=3,max_value=10000,value=832,step=1,key="epi_demo_total")
    mode = st.radio("Definir particiones",("Porcentajes","Límites enteros"),horizontal=True,key="epi_demo_partition_mode")
    left,right = st.columns(2)
    if mode=="Porcentajes":
        train = left.number_input("Entrenamiento (%)",min_value=1,max_value=98,value=80,step=1,key="epi_demo_train_pct")
        validation = right.number_input("Validación (%)",min_value=1,max_value=98,value=10,step=1,key="epi_demo_val_pct")
        st.caption(f"Prueba solicitada: {100-train-validation} %. Se redondean hacia abajo entrenamiento y validación; prueba recibe el resto exacto. Consulta los porcentajes efectivos.")
    else:
        train = left.number_input("Fin exclusivo de entrenamiento",min_value=1,max_value=9999,value=728,step=1,key="epi_demo_train_end")
        validation = right.number_input("Fin exclusivo de validación",min_value=1,max_value=9999,value=780,step=1,key="epi_demo_val_end")
    try:
        protocol = percentage_protocol(total,train,validation) if mode=="Porcentajes" else TemporalProtocol(train,validation,total)
        plan = plan_rolling_origin(protocol)
    except ValueError as exc:
        st.error("Configuración rechazada: " + str(exc))
        st.write("Debe cumplirse 0 < fin de entrenamiento < fin de validación < total. Validación y prueba necesitan al menos ocho posiciones cada una. Porcentajes positivos con suma inferior a 100 %.")
        return
    st.plotly_chart(partition_figure(protocol),width="stretch",theme=None)
    st.dataframe(partition_rows(protocol),hide_index=True,width="stretch")
    a,b,c=st.columns(3)
    a.metric("Ventanas de validación",sum(o.partition=="validation" for o in plan.origins))
    b.metric("Ventanas de prueba",sum(o.partition=="test" for o in plan.origins))
    c.metric("Ventanas descartadas",len(plan.excluded))
    partition=st.radio("Ventanas a inspeccionar",("validation","test"),format_func=lambda p:"Validación" if p=="validation" else "Prueba",horizontal=True,key="epi_demo_windows")
    st.plotly_chart(rolling_figure(plan,partition),width="stretch",theme=None)
    st.caption("Se muestran hasta 40 ventanas completas y todas las colas descartadas de la partición. La tabla conserva el plan completo. Horizonte fijo 8 · paso 4 · entrenamiento expansivo · cohorte inicial fija · cuatro métodos B06. Las posiciones no acreditan semanas ni fechas epidemiológicas.")
    with st.expander("Plan completo y ventanas descartadas"):
        st.dataframe(origin_rows(plan),hide_index=True,width="stretch")
        if plan.excluded:
            st.dataframe([{"Partición":o.partition,"Corte inclusivo":o.cut,"Código":o.reason,
                           "Motivo":"No caben ocho objetivos dentro de la partición"} for o in plan.excluded],hide_index=True,width="stretch")
    st.download_button("Descargar plan posicional",json.dumps(asdict(plan),ensure_ascii=False,indent=2),"plan_posicional_sin_ejecucion.json","application/json",key="epi_demo_download_plan")
    st.warning("Antes de evaluar: acreditar calendario, continuidad, cobertura y elegibilidad; fijar universo y criterios causales de cohorte; congelar decisiones tras validación. Prueba se reserva para evaluación, nunca para elegir hiperparámetros. Este plan no impone por sí solo ese control de acceso.")


def scalability(root,context):
    st.markdown("### Escalabilidad · benchmark sintético registrado")
    st.info("Datos artificiales y deterministas. Evidencia de rendimiento de software, no evaluación epidemiológica ni pronósticos.")
    report=root/"docs/benchmarks/science_demo_i1.json"
    if not report.exists():
        st.warning("Aún no existe una ejecución de benchmark registrada. La navegación no ejecuta el benchmark.")
        return
    try:
        result=json.loads(report.read_text(encoding="utf-8"))
        records=result["results"]
        if result.get("schema")!="episentinel-synthetic-benchmark-v1" or not isinstance(records,list):
            raise ValueError("Formato de benchmark no reconocido")
    except (OSError,ValueError,KeyError) as exc:
        st.error("No se pudo leer la evidencia del benchmark: "+str(exc))
        return
    st.dataframe([{"Filas artificiales":r["rows"],"Bytes CSV":r.get("csv_bytes"),"Ingesta/sintaxis (s)":r.get("ingestion_s"),
                   "Validación/resto B04 (s)":r.get("validation_s"),"Construcción B03 (s)":r.get("construction_s"),
                   "B05 total (s)":r.get("pipeline_s"),"Pico Python (MiB)":r.get("python_peak_mib"),
                   "Estado":r["status"],"Errores":str(r.get("errors",[]))} for r in records],hide_index=True,width="stretch")
    valid=[r for r in records if r["status"]=="completed"]
    if valid:
        fig=go.Figure(go.Scatter(x=[r["rows"] for r in valid],y=[r["pipeline_s"] for r in valid],mode="markers",marker=dict(color="#276D70",size=11)))
        fig.update_layout(title="B05 observado en procesos aislados · datos artificiales",height=320,xaxis_title="Filas sintéticas",yaxis_title="Segundos con instrumentación")
        st.plotly_chart(style_figure(fig),width="stretch",theme=None)
    st.caption("Ingesta/sintaxis mide lectura UTF-8, CSV y cabeceras dentro de B04. Validación es el tiempo restante de B04, incluidos diagnósticos y copias; B03 mide construcción. B05 incluye además orquestación y copias: las etapas no suman todo el total. tracemalloc mide asignaciones Python bajo instrumentación, no memoria RSS máxima del sistema. Entrada en memoria: no mide lectura de disco. No hay extrapolación a producción.")
    historical=context["ingest"]
    if historical and isinstance(historical.get("filas_crudas"),int):
        st.write(f"Referencia de volumen histórico: {historical['filas_crudas']:,} filas crudas documentadas en reports/ingest_report.json. Es otro esquema y otras reglas; no es una medición de B04/B05 sobre originales.")
    else:
        st.caption("Referencia de volumen histórico no disponible; no se sustituye con una cifra estimada.")
    st.caption(f"Entorno: Python {result['environment']['python']} · {result['environment']['platform']} · fecha UTC {result['created_utc']}")
    st.caption("Protocolo, límites, huellas de código y errores de cada proceso disponibles en el registro descargable. Ejecutar de nuevo requiere una orden explícita en terminal; nunca ocurre al navegar.")
    st.download_button("Descargar benchmark y metodología",report.read_bytes(),report.name,"application/json",key="epi_demo_benchmark_download")


def render(root,context):
    preferences=st.session_state.setdefault("epi_applied_preferences",{})
    keys=("epi_demo_section","epi_demo_series","epi_demo_metric","epi_demo_total","epi_demo_partition_mode",
          "epi_demo_train_pct","epi_demo_val_pct","epi_demo_train_end","epi_demo_val_end","epi_demo_windows")
    for key in keys:
        if key not in st.session_state and key in preferences:
            st.session_state[key]=preferences[key]
    st.markdown("## Demostración científica aplicada")
    section=st.radio("Componente de demostración",("Resultados guardados","Diseño temporal","Escalabilidad","Pronóstico retrospectivo"),horizontal=True,key="epi_demo_section")
    if section=="Resultados guardados": saved_results(root,context)
    elif section=="Diseño temporal": experimental_design()
    elif section=="Escalabilidad": scalability(root,context)
    else:
        from app.retrospective_app import render as render_retrospective
        render_retrospective(root)
    for key in keys:
        if key in st.session_state:
            preferences[key]=st.session_state[key]
