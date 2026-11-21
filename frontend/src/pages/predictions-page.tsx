import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { ChartNoAxesCombined, Play, Timer, TriangleAlert } from 'lucide-react'
import { api, ApiError } from '../lib/api'
import type { Methodology, Retrospective } from '../lib/api-types'
import { useInstitutionalData } from '../app/data-availability'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { SourceContext } from '../components/source-context'

const ForecastChart = lazy(() => import('../features/dashboard/forecast-chart'))
const methodNames: Record<string, string> = { ultimo_valor: 'Último valor', ingenua_estacional: 'Ingenua estacional', sarima_sin_estacional: 'SARIMA sin estacionalidad', sarima_estacional: 'SARIMA estacional' }

export function PredictionsPage() {
  const { snapshot, availability, selectedCode, selectCode } = useInstitutionalData()
  const [metadata, setMetadata] = useState<Methodology | null>(null)
  const [metadataError, setMetadataError] = useState('')
  const [metadataAttempt, setMetadataAttempt] = useState(0)
  const [cutChoice, setCutChoice] = useState('')
  const [methodChoice, setMethodChoice] = useState('ultimo_valor')
  const [pending, setPending] = useState(false)
  const [result, setResult] = useState<{ key: string; data: Retrospective } | null>(null)
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null)
  const requestController = useRef<AbortController | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    void api.methodology(controller.signal).then(data => { if (!controller.signal.aborted) { setMetadata(data); setMetadataError('') } }).catch((error: unknown) => {
      if (!controller.signal.aborted) setMetadataError(error instanceof Error ? error.message : 'No se pudo consultar la metodología.')
    })
    return () => controller.abort()
  }, [metadataAttempt])
  useEffect(() => () => requestController.current?.abort(), [])
  const cut = cutChoice && metadata?.allowed_cuts.includes(Number(cutChoice)) ? Number(cutChoice) : metadata?.allowed_cuts[0]
  const method = metadata?.forecast_methods.includes(methodChoice) ? methodChoice : metadata?.forecast_methods[0]
  const key = `${snapshot?.overview.source.sha256}:${selectedCode}:${cut}:${method}`
  const visible = result?.key === key ? result.data : null
  const error = failure?.key === key ? failure.message : ''
  const canExecute = availability.status === 'ready' && !!selectedCode && cut !== undefined && !!method && !pending
  async function execute(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canExecute || cut === undefined || !method || !snapshot) return
    const controller = new AbortController(); requestController.current = controller
    setPending(true); setResult(null); setFailure(null)
    try {
      const data = await api.forecast({ series: selectedCode, cut, method, horizon: 8 }, controller.signal)
      if (data.request.source_sha256 !== snapshot.overview.source.sha256) throw new ApiError('La fuente cambió. Actualiza antes de volver a ejecutar.', 0, 'SOURCE_CHANGED')
      if (!controller.signal.aborted) setResult({ key, data })
    } catch (reason) {
      if (!controller.signal.aborted) setFailure({ key, message: reason instanceof ApiError ? `${reason.message} (${reason.code})${reason.requestId ? ` · Solicitud ${reason.requestId}` : ''}` : 'No se pudo completar el pronóstico.' })
    } finally { if (!controller.signal.aborted) setPending(false) }
  }
  return <div className="page"><div className="page-heading"><div><div className="eyebrow">OBSERVAR · ESTIMAR · CONTRASTAR</div><h1>Predicciones</h1><p>Un corte explícito. Ocho pasos para contrastar con la historia.</p></div><Badge>Retrospectivo · B06</Badge></div>
    <section className="panel forecast-configuration" aria-labelledby="forecast-config-title"><div className="panel-title-row"><h2 id="forecast-config-title">Preparar predicción retrospectiva</h2><ChartNoAxesCombined size={21} aria-hidden="true" /></div>
      <form onSubmit={execute}><div className="forecast-fields"><label>Territorio<select value={selectedCode} disabled={pending || availability.status !== 'ready'} onChange={e => selectCode(e.target.value)}>{!selectedCode && <option value="">Sin catálogo disponible</option>}{snapshot?.territories.codes.map(code => <option key={code} value={code}>{code} · Candidato municipal</option>)}</select></label>
      <label>Método<select value={method ?? ''} disabled={pending || !metadata} onChange={e => setMethodChoice(e.target.value)}>{!metadata && <option value="">Consultando métodos…</option>}{metadata?.forecast_methods.map(m => <option key={m} value={m}>{methodNames[m] ?? m}</option>)}</select></label>
      <label>Corte inclusivo<select value={cut ?? ''} disabled={pending || !metadata} onChange={e => setCutChoice(e.target.value)}>{!metadata && <option value="">Consultando cortes…</option>}{metadata?.allowed_cuts.map(c => <option key={c} value={c}>Posición {c}</option>)}</select></label>
      <div className="horizon-note"><span>Horizonte</span><strong>{metadata?.horizon ?? '—'} <small>posiciones</small></strong></div></div>
      <div className="forecast-submit"><p><Timer size={16} aria-hidden="true" />Ejecución explícita · hasta 45 s en el servidor · sin reintento automático</p><Button type="submit" disabled={!canExecute}><Play size={16} aria-hidden="true" />{pending ? 'Calculando…' : 'Ejecutar predicción'}</Button></div></form>
      {metadataError && <div className="inline-error" role="alert"><p>{metadataError}</p><Button variant="outline" size="small" onClick={() => { setMetadataError(''); setMetadataAttempt(n => n + 1) }}>Consultar metodología</Button></div>}
      {availability.status !== 'ready' && <p className="inline-hint">Se necesita una fuente histórica disponible para ejecutar.</p>}
    </section>
    {pending && <section className="panel forecast-pending" role="status"><span className="pending-pulse" /><h2>Consultando el modelo seleccionado</h2><p>Se utiliza solo el prefijo anterior al corte. No cambies de configuración mientras termina la consulta.</p></section>}
    {error && <section className="panel inline-error" role="alert"><TriangleAlert aria-hidden="true" /><div><h2>El modelo no produjo una salida válida</h2><p>{error}</p><p>No se publica una curva parcial ni se sustituye el método.</p></div></section>}
    {visible ? <section className="panel forecast-output" aria-labelledby="forecast-result-title"><div className="panel-title-row"><div><span className="eyebrow">RESULTADO DE LA SOLICITUD</span><h2 id="forecast-result-title">Estimación y observación · {visible.request.series}</h2></div><Badge tone="teal">{visible.forecast.fit_status}</Badge></div><Suspense fallback={<p role="status">Preparando visualización…</p>}><ForecastChart rows={visible.evaluation.rows} /></Suspense>
      <div className="forecast-metrics">{Object.entries(visible.evaluation.metrics).map(([name, value]) => <div key={name}><span>{name}</span><strong>{value === null ? 'No disponible' : value.toLocaleString('es-CO', { maximumFractionDigits: 3 })}</strong></div>)}</div>
      <p className="inline-hint">Intervalo nominal: {visible.forecast.interval_level === null ? 'no disponible para este método' : `${visible.forecast.interval_level * 100}%`}. No es cobertura epidemiológica validada.</p>
      <details><summary>Datos y advertencias de la ejecución</summary><p className="source-path">Identidad: {visible.request.request_id}</p><ul>{visible.forecast.warnings.map((w, i) => <li key={i}>{w.message}</li>)}</ul><div className="accessible-table"><table><caption>Ocho objetivos retrospectivos</caption><thead><tr><th>Posición</th><th>Fecha técnica</th><th>Observado</th><th>Estimación</th><th>Inferior</th><th>Superior</th></tr></thead><tbody>{visible.evaluation.rows.map(r => <tr key={r.position}><td>{r.position}</td><td>{r.technical_date.slice(0, 10)}</td><td>{r.observed ?? 'No disponible'}</td><td>{r.yhat}</td><td>{r.lo ?? 'No disponible'}</td><td>{r.hi ?? 'No disponible'}</td></tr>)}</tbody></table></div></details>
    </section> : !pending && !error && <section className="forecast-idle"><ChartNoAxesCombined size={34} strokeWidth={1.4} aria-hidden="true" /><h2>Tu próxima consulta empieza aquí</h2><p>Selecciona un territorio, un método y un corte. El resultado aparecerá al ejecutar la predicción.</p></section>}
    <div className="context-note"><TriangleAlert size={18} aria-hidden="true" /><p>Evaluación retrospectiva sobre datos ya examinados. No confirma brotes ni demuestra desempeño futuro.</p></div><SourceContext />
  </div>
}
