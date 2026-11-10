"""EpiSentinel AI - dashboard de la Fase 2 (demo).

Ejecutar desde la raiz del repo:  streamlit run app/streamlit_app.py

Lee lo que produce el pipeline:
  data/processed/panel_casos.parquet   (scripts/build_panel.py)
  data/processed/municipios.csv        (scripts/build_lookup.py)
  configs/split.json                   (particion temporal)
  reports/comparacion_fase2.csv        (scripts/evaluate_fase2.py)
  reports/ingest_report.json           (scripts/build_lookup.py)
"""
import json
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from episentinel.baselines.ingenua_estacional import pronosticar_ingenua_estacional, pronosticar_ultimo_valor
from episentinel.detection.alertas import tabla_alertas
from episentinel.evaluation.forecast_metrics import mae, mase, rmse
from episentinel.models.sarima import ajustar_sarima, pronosticar

st.set_page_config(page_title="EpiSentinel AI", page_icon="◈", layout="wide")

AZUL, NARANJA, VERDE, GRIS, ROJO, AMARILLO = "#167566", "#B87823", "#438B68", "#80948A", "#BA4C48", "#C49338"
COLOR_NIVEL = {"verde": VERDE, "amarillo": AMARILLO, "rojo": ROJO}
RAIZ = Path(__file__).resolve().parents[1]
st.markdown((RAIZ / "app/styles.css").read_text(encoding="utf-8"), unsafe_allow_html=True)
pio.templates["episentinel"] = go.layout.Template(
    layout=dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Segoe UI, Arial, sans-serif", color="#17352F", size=12),
                colorway=[AZUL, NARANJA, VERDE, GRIS],
                xaxis=dict(showgrid=False, zeroline=False, automargin=True),
                yaxis=dict(gridcolor="#E4EAE5", zeroline=False, automargin=True),
                margin=dict(l=15, r=20, t=65, b=35), separators=",.",
                hoverlabel=dict(bgcolor="white", font_size=13)))
pio.templates.default = "plotly_white+episentinel"


def metric(container, label, value, detail=None, **kwargs):
    detail = "" if detail is None else str(detail)
    container.markdown(f'<div class="metric-card"><div class="metric-label">{escape(str(label))}</div><div class="metric-value">{escape(str(value))}</div><div class="metric-detail">{escape(detail)}</div></div>', unsafe_allow_html=True)


def intro(kicker, title, body):
    st.markdown(f'<div class="section-head"><span class="eyebrow">{escape(kicker)}</span><h2>{escape(title)}</h2><p>{escape(body)}</p></div>', unsafe_allow_html=True)


def insight(title, body):
    st.markdown(f'<div class="insight"><span class="eyebrow">{escape(title)}</span><p>{escape(body)}</p></div>', unsafe_allow_html=True)


if not (RAIZ / "data/processed/panel_casos.parquet").exists():
    st.title("EpiSentinel AI")
    st.info("Todavía no hay datos procesados para mostrar. Prepara el panel de casos y vuelve a cargar la página.")
    with st.expander("Preparación de datos"):
        st.code("python scripts/build_panel.py\npython scripts/build_lookup.py", language="bash")
    st.stop()



# ----------------------------------------------------------------- datos
@st.cache_data
def cargar():
    panel = pd.read_parquet(RAIZ / "data/processed/panel_casos.parquet")
    panel.columns = pd.to_datetime(panel.columns)
    panel.index = panel.index.astype(str).str.zfill(5)
    ruta = RAIZ / "data/processed/municipios.csv"
    if ruta.exists():
        nombres = pd.read_csv(ruta, dtype={"cod_mun": str, "cod_dpto": str}).set_index("cod_mun")
    else:
        nombres = pd.DataFrame({"municipio": panel.index, "departamento": panel.index.str[:2], "cod_dpto": panel.index.str[:2]},
                               index=panel.index)
    nombres = nombres.reindex(panel.index)
    nombres["municipio"] = nombres["municipio"].fillna(pd.Series(panel.index, index=panel.index))
    nombres["departamento"] = nombres["departamento"].fillna("Sin dato")
    nombres["cod_dpto"] = nombres["cod_dpto"].fillna(pd.Series(panel.index.str[:2], index=panel.index))
    split = json.loads((RAIZ / "configs/split.json").read_text(encoding="utf-8")) if (RAIZ / "configs/split.json").exists() \
        else {"train_end": 727, "val_end": 779, "test_end": 831}
    comp = pd.read_csv(RAIZ / "reports/comparacion_fase2.csv", dtype={"serie": str}) if (RAIZ / "reports/comparacion_fase2.csv").exists() else None
    rep = json.loads((RAIZ / "reports/ingest_report.json").read_text(encoding="utf-8")) if (RAIZ / "reports/ingest_report.json").exists() else None
    return panel, nombres, split, comp, rep


panel, nombres, split, comparacion, reporte = cargar()
TRAIN_END, VAL_END, TEST_END = split["train_end"], split["val_end"], split["test_end"]
FECHAS = panel.columns
ES_EXTERIOR = nombres["cod_dpto"] == "01"


def serie_de(tipo: str, clave: str) -> pd.Series:
    if tipo == "Nacional (solo Colombia)":
        return panel.loc[~ES_EXTERIOR].sum(axis=0)
    if tipo == "Departamento":
        return panel.loc[nombres["departamento"] == clave].sum(axis=0)
    return panel.loc[clave]


def titulo_de(tipo: str, clave: str) -> str:
    return "Total nacional (sin Exterior)" if tipo.startswith("Nacional") else (f"Departamento: {clave}" if tipo == "Departamento" else clave)


# ----------------------------------------------------------------- barra lateral
st.sidebar.markdown('<div class="brand"><span class="brand-mark">◈</span><div>EpiSentinel<span>INTELIGENCIA EPIDEMIOLÓGICA</span></div></div>', unsafe_allow_html=True)
st.sidebar.caption("OBSERVATORIO / DENGUE")
pagina = st.sidebar.radio("Recorrido", ["Panorama", "Territorio y patrones", "Pronósticos", "Señales de alerta", "Evidencia"], label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.markdown("**Territorio de análisis**")
tipo = st.sidebar.selectbox("Nivel territorial", ["Nacional (solo Colombia)", "Departamento", "Municipio"])
if tipo == "Departamento":
    deps = sorted(nombres.loc[~ES_EXTERIOR, "departamento"].unique())
    clave = st.sidebar.selectbox("Departamento", deps, index=deps.index("Valle") if "Valle" in deps else 0)
elif tipo == "Municipio":
    totales = panel.sum(axis=1)
    candidatos = totales[~ES_EXTERIOR].sort_values(ascending=False).index
    etiquetas = {c: f"{nombres.loc[c, 'municipio']} ({nombres.loc[c, 'departamento']}) · {c}" for c in candidatos}
    cod = st.sidebar.selectbox("Municipio (ordenados por casos totales)", list(candidatos), format_func=lambda c: etiquetas[c])
    clave = cod
else:
    clave = "Nacional"
serie = serie_de(tipo, clave)
nombre_serie = titulo_de(tipo, clave) if tipo != "Municipio" else etiquetas[clave]
st.sidebar.divider()
st.sidebar.markdown(
    f"**Datos:** SIVIGILA (INS), dengue 210+220\n\n**Periodo:** {FECHAS[0].year}–{FECHAS[-1].year}\n\n"
    f"**Partición:** entrenamiento 2007–2020 · validación 2021 · prueba 2022")

st.markdown(f'<div class="topline"><span>OBSERVATORIO DE DENGUE</span><span class="status-pill">PROTOTIPO ACADÉMICO · DATOS HISTÓRICOS</span></div><div class="hero"><h1>Entender el pasado.<br><span>Detectar lo inusual.</span></h1><p>Casos, patrones y señales para explorar la vigilancia del dengue en Colombia.</p></div><div class="territory"><span class="territory-dot"></span><strong>{escape(nombre_serie)}</strong><span>SIVIGILA · 2007–2022</span></div>', unsafe_allow_html=True)


def sombreado(fig, y_max):
    fig.add_vrect(x0=FECHAS[TRAIN_END + 1], x1=FECHAS[VAL_END], fillcolor=NARANJA, opacity=0.06, line_width=0)
    fig.add_vrect(x0=FECHAS[VAL_END + 1], x1=FECHAS[-1], fillcolor=VERDE, opacity=0.08, line_width=0)
    return fig


# ================================================================= RESUMEN
if pagina == "Panorama":
    intro("01 / PANORAMA", "Una mirada al comportamiento histórico", "Empieza por los casos observados. Después explora los patrones, las estimaciones y las señales de alerta.")
    anios_posicion = FECHAS[0].year + np.arange(len(serie)) // 52
    anual = pd.Series(serie.values).groupby(anios_posicion).sum()
    c1, c2, c3, c4 = st.columns(4)
    metric(c1, "Casos acumulados", f"{int(serie.sum()):,}".replace(",", "."), "Dengue + dengue grave", delta_color="off")
    metric(c2, "Año con más casos", str(anual.idxmax()), f"{int(anual.max()):,} casos en esta serie".replace(",", "."), delta_color="off")
    metric(c3, "Promedio semanal", f"{serie.mean():,.1f}".replace(",", "_").replace(".", ",").replace("_", "."), "En toda la ventana histórica", delta_color="off")
    metric(c4, "Semanas observadas", str(len(serie)), "Malla de 52 semanas por año", delta_color="off")
    st.markdown("### ¿Cómo han cambiado los casos?")

    fig = go.Figure(go.Scatter(x=FECHAS, y=serie.values, mode="lines", line=dict(color=AZUL, width=1.8), fill="tozeroy", fillcolor="rgba(22,117,102,0.07)", name="Casos"))
    fig.add_vrect(x0=FECHAS[0], x1=FECHAS[TRAIN_END], fillcolor=AZUL, opacity=0.04, line_width=0)
    sombreado(fig, serie.max())
    for txt, x in [("Entrenamiento", FECHAS[360]), ("Val.", FECHAS[VAL_END - 26]), ("Prueba", FECHAS[TEST_END - 26])]:
        fig.add_annotation(x=x, y=1.06, yref="paper", text=txt, showarrow=False, font=dict(size=11, color=GRIS))
    fig.update_layout(title="Casos semanales de dengue", height=380, margin=dict(t=60, b=30), yaxis_title="Casos por semana")
    st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False})

    colores = [AZUL if a <= 2020 else (NARANJA if a == 2021 else VERDE) for a in anual.index]
    figb = go.Figure(go.Bar(x=anual.index, y=anual.values, marker_color=colores))
    figb.update_layout(title="El histórico, año a año", height=300, margin=dict(t=50, b=30))
    st.plotly_chart(figb, width="stretch", theme=None, config={"displaylogo": False})

    st.caption("Colores del histórico anual: verde petróleo = entrenamiento · ocre = validación · verde claro = prueba.")
    insight("LECTURA DEL TERRITORIO", f"{anual.idxmax()} reúne el mayor total anual de esta serie. Los conteos describen lo observado: no equivalen a riesgo por habitante ni confirman un brote.")
    with st.expander("Alcance y límites de estos datos"):
        st.write("Se excluyen los códigos del exterior de las vistas territoriales. La semana 53 se suma a la 52; las fechas de la malla no equivalen al calendario epidemiológico oficial. Este tratamiento está pendiente de revisión.")
        st.write("El panel completa las combinaciones sin registros con cero. Esto no permite distinguir ausencia de casos de ausencia de notificación.")
    if reporte:
        with st.expander("Limpieza de los datos (qué se excluyó y por qué)", expanded=False):
            embudo = pd.DataFrame({
                "Etapa": ["Filas descargadas (3 archivos)", "Tras excluir filas de eventos ajenos", "Tras excluir municipio desconocido (código ...000)"],
                "Filas": [reporte["filas_crudas"], reporte["filas_tras_excluir_ajenas"], reporte["filas_validas_para_panel"]],
                "Excluidas": [0, reporte["filas_ajenas_excluidas"], reporte["filas_invalidas_adicionales"]],
            })
            st.dataframe(embudo, hide_index=True, width="stretch")
            st.caption(f"Filas con semana 53 (plegadas a la 52): {reporte['filas_semana_53']} · duplicados por clave: {reporte['filas_clave_duplicada']}")

# ================================================================= EXPLORACION
elif pagina == "Territorio y patrones":
    intro("02 / EXPLORACIÓN", "Dónde y cuándo se concentran los casos", "El primer gráfico responde al territorio elegido. Las comparaciones de municipios y departamentos muestran todo Colombia.")
    n_y = len(serie) // 52
    M = serie.values[: n_y * 52].reshape(n_y, 52).astype(float)
    cols = st.columns([1.1, 1])
    fh = go.Figure(go.Heatmap(z=np.log1p(M), customdata=M, hovertemplate="Año %{y} · semana %{x}<br>%{customdata:,.0f} casos<extra></extra>", x=list(range(1, 53)), y=list(range(FECHAS[0].year, FECHAS[0].year + n_y)),
                              colorscale=[[0,"#F0F3E9"],[0.45,"#9BC3A9"],[1,AZUL]], colorbar=dict(title="log(1+casos)")))
    fh.update_layout(title="Casos por año y semana epidemiológica", height=420, yaxis=dict(autorange="reversed"), xaxis_title="Semana")
    cols[0].plotly_chart(fh, width="stretch", theme=None)
    Mn = M / np.where(M.mean(axis=1, keepdims=True) == 0, 1, M.mean(axis=1, keepdims=True))
    fp = go.Figure()
    for i in range(n_y):
        fp.add_trace(go.Scatter(x=list(range(1, 53)), y=Mn[i], mode="lines", line=dict(color="rgba(31,111,178,0.18)", width=1), showlegend=False))
    fp.add_trace(go.Scatter(x=list(range(1, 53)), y=Mn.mean(axis=0), mode="lines", line=dict(color=AZUL, width=3), name="Perfil medio"))
    fp.update_layout(title="Perfil semanal (cada año ÷ su media): ¿hay estacionalidad?", height=420, xaxis_title="Semana", yaxis_title="Relativo a la media del año")
    cols[1].plotly_chart(fp, width="stretch", theme=None)
    st.caption("Los mapas de calor usan escala logarítmica para distinguir valores pequeños; el cursor muestra el conteo real. Si hubiera una estacionalidad anual marcada, las líneas claras se parecerían entre sí y el perfil medio mostraría picos definidos. "
               "En este conjunto de datos dominan los ciclos epidémicos de varios años sobre el patrón anual.")

    st.subheader("Municipios con más casos a lo largo del tiempo")
    n_top = st.slider("Número de municipios", 10, 40, 20)
    tops = panel.sum(axis=1)[~ES_EXTERIOR].sort_values(ascending=False).head(n_top).index
    sem_anio = panel.loc[tops].T.groupby(FECHAS[0].year + np.arange(len(FECHAS)) // 52).sum().T
    fm = go.Figure(go.Heatmap(z=np.log1p(sem_anio.values), customdata=sem_anio.values, hovertemplate="%{y} · %{x}<br>%{customdata:,.0f} casos<extra></extra>", x=sem_anio.columns, y=[f"{nombres.loc[c, 'municipio']} ({c})" for c in tops],
                              colorscale=[[0,"#F0F3E9"],[0.45,"#9BC3A9"],[1,AZUL]], colorbar=dict(title="log(1+casos)")))
    fm.update_layout(height=max(350, 22 * n_top + 120), yaxis=dict(autorange="reversed"), title="Casos por municipio y año (mapa de calor)")
    st.plotly_chart(fm, width="stretch", theme=None, config={"displaylogo": False})

    st.subheader("Departamentos por año")
    dep = panel.loc[~ES_EXTERIOR].groupby(nombres.loc[~ES_EXTERIOR, "departamento"]).sum()
    dep_anio = dep.T.groupby(FECHAS[0].year + np.arange(len(FECHAS)) // 52).sum().T
    dep_anio = dep_anio.loc[dep_anio.sum(axis=1).sort_values(ascending=False).index]
    fd = go.Figure(go.Heatmap(z=np.log1p(dep_anio.values), customdata=dep_anio.values, hovertemplate="%{y} · %{x}<br>%{customdata:,.0f} casos<extra></extra>", x=dep_anio.columns, y=dep_anio.index, colorscale=[[0,"#F0F3E9"],[0.45,"#9BC3A9"],[1,AZUL]], colorbar=dict(title="log(1+casos)")))
    fd.update_layout(height=620, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fd, width="stretch", theme=None, config={"displaylogo": False})
    st.caption("No hay mapa geográfico porque el conjunto de datos no trae coordenadas; el mapa coroplético queda para la Fase 3 (DIVIPOLA/DANE).")

# ================================================================= PRONOSTICO
@st.cache_data(show_spinner="Ajustando el modelo…")
def _pronostico(datos_serie: pd.Series, llave: str, origen: int, pasos: int, modelo: str, estacional: bool):
    train = datos_serie.iloc[: origen + 1]
    pasos = min(pasos, len(datos_serie) - origen - 1) if origen < len(datos_serie) - 1 else pasos
    if modelo == "Ingenua estacional":
        p = pronosticar_ingenua_estacional(train, pasos).to_frame("yhat")
    elif modelo == "Último valor":
        p = pronosticar_ultimo_valor(train, pasos).to_frame("yhat")
    else:
        res = ajustar_sarima(train.astype(float), order=(1, 1, 1), seasonal_order=(1, 0, 1, 52) if estacional else (0, 0, 0, 0))
        fechas = pd.date_range(train.index[-1] + pd.Timedelta(days=7), periods=pasos, freq="7D")
        p = pronosticar(res, pasos, fechas)
    return p


if pagina == "Pronósticos":
    intro("03 / PRONÓSTICOS", "Lo esperado frente a lo observado", "Simula un corte en el pasado: el modelo aprende hasta ese punto y estima las semanas siguientes.")
    st.markdown("Elige el **punto de corte**: el modelo solo ve datos hasta esa fecha y pronostica las semanas siguientes.")
    c1, c2, c3 = st.columns(3)
    modelo = c1.radio("Modelo", ["SARIMA", "Ingenua estacional", "Último valor"], horizontal=True)
    pasos = c2.slider("Horizonte (semanas)", 4, 52, 8, step=4)
    est = c3.checkbox("SARIMA con componente estacional (S=52)", value=True, disabled=(modelo != "SARIMA"))
    opciones = list(range(VAL_END - 52, TEST_END - 3, 4))
    origen = st.select_slider("Último dato que ve el modelo", options=opciones, value=VAL_END,
                              format_func=lambda i: f"{FECHAS[0].year + i // 52} · semana {i % 52 + 1:02d}")
    p = _pronostico(serie, nombre_serie, origen, pasos, modelo, est)
    real = serie.reindex(p.index)
    ctx = serie.iloc[max(0, origen - 104): origen + 1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ctx.index, y=ctx.values, mode="lines", name="Histórico", line=dict(color=GRIS, width=1.3)))
    if "lo" in p:
        fig.add_trace(go.Scatter(x=list(p.index) + list(p.index[::-1]), y=list(p["hi"]) + list(p["lo"][::-1]), fill="toself",
                                 fillcolor="rgba(31,111,178,0.18)", line=dict(width=0), name="IC 95 %", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=p.index, y=p["yhat"], mode="lines", name=f"Pronóstico ({modelo})", line=dict(color=AZUL if modelo == "SARIMA" else NARANJA, width=2.2, dash="solid" if modelo == "SARIMA" else "dash")))
    fig.add_trace(go.Scatter(x=real.index, y=real.values, mode="lines+markers", name="Observado", line=dict(color="black", width=1.5), marker=dict(size=4)))
    fig.update_layout(height=430, margin=dict(t=40), yaxis_title="Casos por semana", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False})
    m1, m2, m3 = st.columns(3)
    metric(m1, "Error absoluto medio · MAE", f"{mae(real.values, p['yhat'].values):.1f}")
    metric(m2, "Error cuadrático · RMSE", f"{rmse(real.values, p['yhat'].values):.1f}")
    metric(m3, "Error escalado · MASE", f"{mase(real.values, p['yhat'].values, serie.iloc[: origen + 1].values):.2f}")
    insight("CÓMO LEERLO", "La línea del pronóstico es la estimación; la línea oscura muestra lo que realmente ocurrió. La banda representa incertidumbre. En las tres métricas de error, menor es mejor. Los pronósticos no son alertas de brote.")
    if "lo" in p:
        dentro = float(((real >= p["lo"]) & (real <= p["hi"])).mean())
        st.caption(f"Cobertura observada del IC 95 % en este tramo: {dentro:.0%}. "
                   "A horizontes largos el intervalo se ensancha mucho y deja de ser informativo para detectar anomalías: por eso las alertas usan un paso adelante.")

# ================================================================= ALERTAS
@st.cache_data(show_spinner="Calculando alertas…")
def _alertas(datos_serie: pd.Series, llave: str, estacional: bool):
    return tabla_alertas(datos_serie, TRAIN_END, order=(1, 1, 1), seasonal_order=(1, 0, 1, 52) if estacional else (0, 0, 0, 0))


if pagina == "Señales de alerta":
    intro("04 / SEÑALES", "Semanas que merecen una revisión", "Contrasta los casos observados con su comportamiento previo. Una señal invita a revisar; no confirma un brote.")
    st.markdown('<div class="signal-key"><span><i class="dot green"></i>Sin señal · 0 reglas</span><span><i class="dot amber"></i>Atención · 1 regla</span><span><i class="dot red"></i>Coincidencia · 2 o más reglas</span></div>', unsafe_allow_html=True)
    st.info("Análisis histórico de 2021–2022. Estas señales no describen la situación epidemiológica actual.")
    st.markdown(
        "Tres reglas complementarias sobre las semanas **posteriores al entrenamiento (2021–2022)**, "
        "cada una usando solo información anterior a la semana evaluada: **SARIMA un paso adelante** (observado > límite superior del IC 95 %), "
        "**EARS C2** (CDC) y **canal endémico** (zona de epidemia, > p90 de los últimos 5 años).")
    est_a = st.checkbox("SARIMA con componente estacional (S=52)", value=True, key="est_alertas")
    ta = _alertas(serie, nombre_serie, est_a)
    cA, cB, cC, cD = st.columns(4)
    metric(cA, "Semanas evaluadas", len(ta))
    metric(cB, "Coincidencia · 2+ reglas", int((ta["nivel"] == "rojo").sum()))
    metric(cC, "Atención · 1 regla", int((ta["nivel"] == "amarillo").sum()))
    metric(cD, "Sin reglas activadas", int((ta["nivel"] == "verde").sum()))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(ta.index) + list(ta.index[::-1]), y=list(ta["hi"]) + list(ta["lo"][::-1]), fill="toself",
                             fillcolor="rgba(31,111,178,0.15)", line=dict(width=0), name="IC 95 % un paso", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ta.index, y=ta["yhat"], mode="lines", line=dict(color=AZUL, width=1.4, dash="dot"), name="Esperado (SARIMA)"))
    fig.add_trace(go.Scatter(x=ta.index, y=ta["obs"], mode="lines", line=dict(color="black", width=1.6), name="Observado"))
    for nivel in ["amarillo", "rojo"]:
        sel = ta[ta["nivel"] == nivel]
        fig.add_trace(go.Scatter(x=sel.index, y=sel["obs"], mode="markers", name=nivel.capitalize(),
                                 marker=dict(color=COLOR_NIVEL[nivel], size=11 if nivel == "rojo" else 8, line=dict(color="white", width=1))))
    fig.update_layout(height=450, margin=dict(t=30), yaxis_title="Casos por semana", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False})

    det = ta[ta["nivel"] != "verde"][["obs", "yhat", "hi", "alerta_sarima", "alerta_ears", "alerta_canal", "nivel"]].copy()
    det.columns = ["Observado", "Esperado", "Límite sup. IC95", "SARIMA", "EARS C2", "Canal endémico", "Nivel"]
    posiciones = serie.index.get_indexer(det.index)
    det.index = [f"{FECHAS[0].year + i // 52} · S{i % 52 + 1:02d}" for i in posiciones]
    det.index.name = "Año · semana"
    st.subheader("Semanas con alerta")
    if det.empty:
        st.info("Ninguna regla marcó alertas en este periodo para la serie elegida.")
    else:
        st.dataframe(det.round(1).replace({True: "Sí", False: "—"}), width="stretch")
        st.download_button("Descargar semanas señaladas", det.to_csv().encode("utf-8-sig"), "episentinel_senales.csv", "text/csv")
    st.warning("**Estas alertas no están validadas.** No existen etiquetas oficiales de brote para este conjunto de datos; "
               "son semanas candidatas a revisión, no brotes confirmados. Medir qué tan buenas son (precisión, exhaustividad, tiempo de detección) "
               "requiere etiquetas de referencia (boletines del INS), tarea de la Fase 3.")

# ================================================================= EVALUACION
if pagina == "Evidencia":
    intro("05 / EVIDENCIA", "Qué respaldan los resultados de hoy", "Compara los métodos y conoce los límites de la evaluación antes de sacar conclusiones.")
    st.caption("Esta comparación guardada es global: no cambia con el territorio lateral. El agregado nacional evaluado incluye Exterior; el panorama lo excluye.")
    st.markdown("Comparación sobre el **año de prueba 2022**: el modelo se entrena con 2007–2021 y pronostica 52 semanas, sin reajustarse.")
    if comparacion is None:
        st.info("Ejecuta `python scripts/evaluate_fase2.py` para generar reports/comparacion_fase2.csv.")
    else:
        nom = {"NACIONAL": "Nacional"}
        nom.update({c: nombres.loc[c, "municipio"] for c in comparacion["serie"].unique() if c in nombres.index})
        nom_modelo = {"ingenua_estacional": "Ingenua estacional", "ingenua_ultimo_valor": "Ingenua: último valor",
                      "sarima_estacional": "SARIMA (1,1,1)(1,0,1)[52]", "sarima_sin_estacional": "SARIMA (1,1,1) sin estacional"}
        color_modelo = {"Ingenua estacional": NARANJA, "Ingenua: último valor": GRIS, "SARIMA (1,1,1)(1,0,1)[52]": AZUL, "SARIMA (1,1,1) sin estacional": "#9DC3E6"}
        comparacion = comparacion.assign(Serie=comparacion["serie"].map(lambda s: nom.get(s, s)), Modelo=comparacion["modelo"].map(nom_modelo))
        fig = go.Figure()
        for modelo_n, g in comparacion.groupby("Modelo", sort=False):
            fig.add_trace(go.Bar(x=g["Serie"], y=g["mase"], name=modelo_n, marker_color=color_modelo.get(modelo_n, GRIS)))
        fig.update_layout(barmode="group", height=420, yaxis_title="MASE (menor es mejor)", legend=dict(orientation="h", y=1.12),
                          title="Error escalado (MASE) por serie y modelo")
        st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False})
        promedio = comparacion.groupby("Modelo")["mase"].mean().sort_values()
        insight("RESULTADO PRELIMINAR", f"{promedio.index[0]} obtiene el menor MASE promedio ({promedio.iloc[0]:.3f}) entre las {comparacion['serie'].nunique()} series evaluadas. Una sola ventana no demuestra qué método será mejor en otros periodos o territorios.")
        prom = comparacion.groupby("Modelo", sort=False)["mase"].mean().round(3).rename("MASE promedio").to_frame()
        c1, c2 = st.columns([1, 2])
        c1.dataframe(prom, width="stretch")
        c2.markdown(
            "**Cómo leerlo.** SARIMA mejora a la ingenua estacional en la mayoría de series, pero la regla de *repetir el último valor* "
            "obtiene un error promedio menor, y las dos variantes de SARIMA muestran resultados cercanos. "
            "Con una sola ventana de prueba, 6 series y un horizonte de 52 semanas, **la ventaja de SARIMA no está demostrada**; "
            "la validación de origen móvil con horizonte corto (8 semanas) es la siguiente prueba.")
        det_cols = [c for c in ["Serie", "Modelo", "mae", "rmse", "mase", "cobertura_ic95"] if c in comparacion.columns]
        with st.expander("Tabla completa"):
            st.dataframe(comparacion[det_cols].round(3), hide_index=True, width="stretch")
st.markdown('<div class="footer"><strong>EpiSentinel AI</strong><span>Equipo DKK · Universidad Popular del Cesar</span><span>Investigación académica · Datos históricos 2007–2022</span></div>', unsafe_allow_html=True)

