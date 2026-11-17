"""Framework-free B08 state and presentation adapters; epidemiology stays in B03/B05."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import plotly.graph_objects as go

from episentinel.data.csv_loader import load_csv
from episentinel.data.epidemiological_series import CalendarMetadata, MunicipalIdentity, PeriodGrid
from episentinel.services.isolated_pipeline import PipelineConfig, run_pipeline

EVENT_LABELS = {210: "Dengue · 210", 220: "Dengue grave · 220", 580: "Mortalidad por dengue · 580"}


def new_state():
    return dict(payload=None, filename=None, source_key=None, load=None, result=None,
                execution_key=None, selection=dict(municipality=None, event=None, profile=None),
                step="Datos", error=None)


def invalidate(state):
    state.update(result=None, execution_key=None, error=None)


def set_source(state, payload, filename):
    key = None if payload is None else (hashlib.sha256(payload).hexdigest(), filename)
    if key == state["source_key"]:
        return False
    state.clear()
    state.update(new_state())
    state.update(payload=payload, filename=filename, source_key=key)
    if payload is not None:
        try:
            state["load"] = load_csv(payload, source_name=filename)
        except (OSError, TypeError) as exc:
            state["error"] = str(exc)
    return True


def set_selection(state, field, value):
    if state["selection"][field] != value:
        state["selection"][field] = value
        invalidate(state)


def read_profiles(path):
    profiles = json.loads(Path(path).read_text(encoding="utf-8"))["profiles"]
    if len({p["id"] for p in profiles}) != len(profiles):
        raise ValueError("Identificadores de perfil repetidos")
    for p in profiles:
        make_config("05001", 210, p)  # delegates metadata/domain validation to B03
    return profiles


def make_config(municipality, event, profile):
    return PipelineConfig(profile["config_version"], MunicipalIdentity(municipality), (event,),
                          PeriodGrid(profile["periods"], CalendarMetadata(**profile["calendar_metadata"])))


def fingerprint(state, config):
    identity = {"file": state["source_key"], "config": asdict(config)}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def ensure_current(state, config):
    if state["result"] is not None and (config is None or state["execution_key"] != fingerprint(state, config)):
        invalidate(state)
        return False
    return state["result"] is not None


def execute(state, config):
    loaded = state["load"]
    if loaded is None or loaded.blocked:
        invalidate(state)
        raise ValueError("Primero carga un CSV aceptado")
    invalidate(state)
    result = run_pipeline(state["payload"], config=config, source_name=state["filename"])
    state.update(result=result, execution_key=fingerprint(state, config), step="Análisis")
    return result


def period_label(period):
    return f"{period[0]} · S{period[1]:02d}"


def point_rows(series):
    return [{"Periodo": period_label(p.period), "Conteo observado": p.observed_count,
             "Estado": "Observado" if p.observation_status == "observed" else "Sin observación",
             "Origen": "; ".join(f"{r.source or 'entrada'} · registro {r.record or r.input_position}" for r in p.source_refs)}
            for p in series.points]


def narrative(series):
    c = series.coverage
    base = f"Hay observaciones en {c.observed_periods} de {c.expected_periods} periodos declarados."
    if c.observed_periods == 0:
        return base + " No hay un conteo observado que representar; esta ausencia no significa cero casos."
    if c.missing_periods:
        return base + f" En {len(c.missing_periods)} no conocemos el conteo; no se interpretan como cero. La curva conserva esos huecos."
    return base + " La cobertura se refiere únicamente a esta malla; no demuestra notificación completa ni ausencia de subregistro."


def observed_figure(series):
    labels = [period_label(p.period) for p in series.points]
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=labels, y=[p.observed_count for p in series.points],
        mode="lines+markers", connectgaps=False, name="Conteo observado",
        line=dict(color="#276D70", width=3.5), marker=dict(size=11, color="#102F3A", line=dict(color="#FFFFFF", width=2.5)),
        hovertemplate="%{x}<br>Conteo observado: %{y}<extra></extra>"))
    missing = [period_label(p.period) for p in series.points if p.observed_count is None]
    if missing:
        figure.add_trace(go.Scatter(x=missing, y=[0.5] * len(missing), yaxis="y2", mode="markers",
            marker=dict(symbol="square", size=11, color="#E3B45C", line=dict(color="#FFFFFF", width=1)), name="Sin observación",
            hovertemplate="%{x}<br>Sin observación; no equivale a cero<extra></extra>"))
    maximum = max((p.observed_count for p in series.points if p.observed_count is not None), default=0)
    figure.update_layout(height=310 if len(labels) <= 12 else 390, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial", color="#24353D", size=12),
        margin=dict(l=48, r=16, t=35, b=55), legend=dict(orientation="h", y=1.12, font=dict(size=12)),
        xaxis=dict(anchor="free", position=0, type="category", categoryorder="array", categoryarray=labels, title="Periodos declarados; sin fechas inferidas", automargin=True),
        yaxis=dict(title="Conteo observado", domain=[0.24 if missing else 0, 1], rangemode="tozero", dtick=1 if maximum <= 10 else None, gridcolor="#E9EEEA", zerolinecolor="#CCD8D2", automargin=True),
        yaxis2=dict(domain=[0.04, 0.12], range=[0, 1], visible=False, fixedrange=True),
        hovermode="closest")
    return figure


def issue_rows(report):
    advice = {"integer": "Usa enteros sin decimales, signos ni separadores de miles.",
              "duplicate": "Revisa las claves repetidas; no se suman automáticamente.",
              "schema": "Conserva exactamente los cinco encabezados del contrato.",
              "territory": "Esta carga acepta candidatos municipales; separa Exterior y desconocidos.",
              "code": "Conserva el código municipal como texto de cinco dígitos.",
              "empty": "El archivo necesita encabezado y al menos una observación.",
              "csv": "Revisa comillas, delimitador coma y codificación UTF-8.",
              "range": "Revisa el año, la semana (1–53) y el evento (210, 220 o 580).",
              "row_width": "Cada registro debe tener cinco campos."}
    return [{"Registro": i["record"], "Columna": i["column"] or "Archivo", "Código": i["code"],
             "Qué revisar": advice.get(i["code"], "Revisa el campo indicado en el detalle técnico.")}
            for i in report["errors"]]


def executive_summary(result):
    """Display-only indicators; coverage is relative to the declared grid."""
    series = result.series.series[0]
    coverage = series.coverage
    return dict(observed=coverage.observed_periods, expected=coverage.expected_periods,
                missing=len(coverage.missing_periods),
                coverage_label=f"{100 * coverage.observed_periods / coverage.expected_periods:.0f} %",
                warning_count=len(result.warnings),
                execution="Lectura construida" if result.status == "completed" else "Ejecución pendiente",
                eligibility="No evaluada", config_version=result.config.version)


def interpretation_sections(series):
    return (
        ("Qué muestran estos datos", narrative(series)),
        ("Qué sí puede concluirse", "Podemos describir los conteos informados y localizar los periodos sin observación dentro de la malla seleccionada. Un cero solo representa una observación explícita del archivo."),
        ("Qué sigue siendo incierto", "La cobertura de esta malla no demuestra notificación completa ni ausencia de subregistro. No se han asignado fechas epidemiológicas ni evaluado elegibilidad analítica. Estas observaciones no confirman brotes ni riesgo clínico."),
    )


def warning_notes(result):
    """Group context for readers; full original warnings remain in diagnostics."""
    codes = {w.code for w in result.warnings}
    notes = []
    if codes & {"pending_calendar", "pending_week_53"}:
        notes.append("Calendario por verificar; S53 se conserva y no se infieren fechas.")
    if "pending_territory" in codes:
        notes.append("Identidad municipal candidata; validación con catálogo oficial pendiente.")
    if "coverage_incomplete" in codes:
        notes.append("Hay periodos sin observación. No se sustituyen por cero.")
    if "no_selected_observations" in codes:
        notes.append("No hay observaciones para la selección vigente.")
    if "eligibility_not_evaluated" in codes:
        notes.append("Elegibilidad no evaluada; no se ejecutaron pronósticos ni señales.")
    if "pending_event_comparability" in codes:
        notes.append("Los eventos se mantienen independientes; no se presume que puedan sumarse.")
    return notes
