"""Editorial B08 components. Dynamic HTML is escaped; services stay unchanged."""
from html import escape
from dataclasses import asdict

import streamlit as st

from app.analysis_presenter import (
    EVENT_LABELS, executive_summary, interpretation_sections, observed_figure,
    period_label, point_rows, warning_notes,
)


def hero():
    st.markdown('''<section class="epi-hero"><div class="epi-hero-main"><div class="epi-eyebrow">CENTRO INTELIGENTE DE VIGILANCIA EPIDEMIOLÓGICA</div>
<h1>La vigilancia comienza<br>con <em>datos claros.</em></h1>
<p>Una lectura más profunda del dengue en Colombia: del registro municipal a una interpretación que hace visible lo observado y lo que aún no sabemos.</p>
<div class="epi-hero-foot">INTELIGENCIA EPIDEMIOLÓGICA · EQUIPO DKK</div></div>
<aside class="epi-hero-aside"><span class="epi-aside-kicker">DEL DATO A LA EVIDENCIA</span><div><b>01</b><span>Validar<small>Estructura, identidad y consistencia.</small></span></div><div><b>02</b><span>Construir<small>Series y cobertura por periodo.</small></span></div><div><b>03</b><span>Comprender<small>Una lectura con límites explícitos.</small></span></div><p>La precisión también consiste en reconocer lo que falta.</p></aside></section>''', unsafe_allow_html=True)


def section(kicker, title, body):
    st.markdown(f'<section class="epi-section"><div class="epi-eyebrow">{escape(kicker)}</div><h2>{escape(title)}</h2><p>{escape(body)}</p></section>', unsafe_allow_html=True)


def panel_heading(number, title, body):
    st.markdown(f'<div class="epi-panel-heading"><span>{escape(number)}</span><div><h3>{escape(title)}</h3><p>{escape(body)}</p></div></div>', unsafe_allow_html=True)


def credibility_band():
    items = (("VALIDACIÓN", "Estructura antes de interpretar"), ("TRAZABILIDAD", "Archivo, huella y registros"),
             ("COBERTURA", "Ausencias siempre visibles"), ("VERIFICACIÓN", "Pruebas de integración documentadas"))
    cards = ''.join(f'<div><span>{a}</span><strong>{b}</strong></div>' for a, b in items)
    st.markdown(f'<section class="epi-credibility" aria-label="Capacidades del recorrido">{cards}</section>', unsafe_allow_html=True)


def progress(step):
    labels = (("Datos", "Una fuente verificable"), ("Territorio", "Un contexto explícito"), ("Análisis", "Una lectura responsable"))
    html = ''.join(f'<div class="epi-step {"active" if label == step else ""}"><b>{i:02d}</b><span>{label}<small>{body}</small></span></div>' for i, (label, body) in enumerate(labels, 1))
    st.markdown(f'<div class="epi-progress">{html}</div>', unsafe_allow_html=True)


def render_evidence(result):
    d = result.load_diagnostic
    if d is None:
        st.info("Esta ejecución no llegó a producir un diagnóstico de carga.")
        return
    cfg = result.config
    metadata = cfg.period_grid.metadata if cfg else None
    fields = [("Archivo analizado", d.source, "Conservado en la sesión"),
              ("Identidad del archivo", f"{d.sha256[:14]}…{d.sha256[-8:]}", "SHA-256 · identificación de bytes"),
              ("Configuración aplicada", cfg.version if cfg else "No aplicada", f"Municipio {cfg.territory.code} · " + ", ".join(EVENT_LABELS[e] for e in cfg.event_codes) if cfg else "Sin selección aplicada"),
              ("Malla temporal", f"{len(cfg.period_grid.periods)} periodos · versión {metadata.version}" if cfg else "No aplicada", "Sin fechas inferidas"),
              ("Validación de carga", "Archivo bloqueado" if d.blocked else "Estructura aceptada", f"Contrato CSV · versión {d.contract_version}"),
              ("Advertencias", f"{len(result.warnings)} avisos contextuales", "No equivalen a riesgo epidemiológico")]
    cards = ''.join(f'<div class="epi-evidence-item"><span>{escape(a)}</span><strong>{escape(b)}</strong><small>{escape(c)}</small></div>' for a, b, c in fields)
    st.markdown(f'<section class="epi-evidence"><div class="epi-evidence-top"><div><span class="epi-eyebrow">EVIDENCIA DE ESTA LECTURA</span><h3>Un resultado que puede rastrearse.</h3></div><span class="epi-tag">TRAZABILIDAD CONSERVADA</span></div><div class="epi-evidence-grid">{cards}</div></section>', unsafe_allow_html=True)
    if metadata:
        st.caption("Procedencia de la malla: " + metadata.source)
    notes = warning_notes(result)
    if notes:
        visible = ''.join(f'<li>{escape(note)}</li>' for note in notes[:3])
        st.markdown(f'<div class="epi-evidence-notes"><strong>Condiciones de interpretación</strong><ul>{visible}</ul><p>Elegibilidad no evaluada · Sin pronósticos ni señales ejecutadas.</p></div>', unsafe_allow_html=True)
        with st.expander("Límites y advertencias de esta ejecución"):
            for note in notes:
                st.write("• " + note)
    if result.series:
        with st.expander("Cobertura y trazabilidad por observación"):
            for series in result.series.series:
                st.write(EVENT_LABELS[series.event_code])
                st.dataframe(point_rows(series), hide_index=True, width="stretch")
    with st.expander("Información técnica completa · JSON"):
        st.caption("Detalle para revisión científica. La huella no certifica por sí sola procedencia institucional.")
        st.code(d.sha256, language=None)
        st.json(asdict(result))


def render_result(result):
    if result.status != "completed" or result.series is None:
        st.error("No pudimos construir una serie con esta configuración. No hay resultados parciales.")
        for issue in result.errors:
            st.write(f"{issue.code}: {issue.reason}")
        return
    bundle = result.series
    series = bundle.series[0]
    summary = executive_summary(result)
    first, last = period_label(series.points[0].period), period_label(series.points[-1].period)
    st.markdown(f'<header class="epi-analysis-header"><div><div class="epi-eyebrow">LECTURA MUNICIPAL / OBSERVACIONES</div><h1>Municipio {escape(bundle.territory.code)}</h1><p>{escape(EVENT_LABELS[series.event_code])} <span>·</span> {escape(first)} — {escape(last)}</p><div class="epi-analysis-description">Una visión de los registros disponibles, su cobertura y los límites que deben acompañar cualquier interpretación.</div></div><aside><span class="epi-status">LECTURA CONSTRUIDA</span><small>Configuración {escape(result.config.version)}</small><small>Catálogo territorial pendiente</small></aside></header>', unsafe_allow_html=True)
    st.markdown(f'''<section class="epi-executive" aria-label="Resumen ejecutivo de cobertura">
<article class="epi-summary-primary"><span>OBSERVACIONES DISPONIBLES</span><div class="epi-summary-value">{summary['observed']}<small> / {summary['expected']}</small></div><p>Periodos con conteo informado</p><div class="epi-coverage-track"><i style="width:{100 * summary['observed'] / summary['expected']:.4f}%"></i></div><footer>{summary['coverage_label']} de cobertura en la malla declarada</footer></article>
<article><span>LO QUE FALTA</span><div class="epi-summary-value">{summary['missing']}<small> {'periodo' if summary['missing'] == 1 else 'periodos'}</small></div><p>Sin observación disponible</p><footer>Una ausencia no representa cero casos.</footer></article>
<article class="epi-summary-status"><span>ESTADO DE LA LECTURA</span><h3>Ejecución completa.<br>Elegibilidad no evaluada.</h3><p>{len(bundle.series)} serie municipal construida · {summary['warning_count']} avisos contextuales</p><footer>Sin pronósticos ni señales ejecutadas.</footer></article></section>''', unsafe_allow_html=True)
    with st.container(border=True, key="epi_plot_shell"):
        st.markdown('<div class="epi-chart-heading"><div><span class="epi-eyebrow">LA SERIE OBSERVADA</span><h2>Una evolución que merece contexto.</h2></div><span class="epi-chart-note">CONTEOS DEL ARCHIVO<br>Sin estimaciones añadidas</span></div>', unsafe_allow_html=True)
        if series.coverage.observed_periods:
            st.plotly_chart(observed_figure(series), width="stretch", theme=None,
                            config={"displayModeBar": False, "displaylogo": False, "scrollZoom": False})
        else:
            st.info("Sin observaciones para esta selección. No se dibuja una curva ni se informa un total cero.")
        st.caption("Los huecos se conservan. La franja ámbar identifica periodos sin observación, sin asignarles un conteo. No se infieren fechas epidemiológicas.")
    texts = interpretation_sections(series)
    columns = ''.join(f'<article><span>0{i}</span><h3>{escape(title)}</h3><p>{escape(body)}</p></article>' for i, (title, body) in enumerate(texts, 1))
    st.markdown(f'<section class="epi-interpretation"><div class="epi-eyebrow">LECTURA E INTERPRETACIÓN</div><h2>De los registros a una lectura responsable.</h2><div class="epi-interpretation-grid">{columns}</div></section>', unsafe_allow_html=True)
    with st.expander("Datos observados y ausencias"):
        st.dataframe(point_rows(series), hide_index=True, width="stretch")
    render_evidence(result)
    credibility_band()
