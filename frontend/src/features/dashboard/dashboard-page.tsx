import { Link } from 'react-router'
import { Activity, ChartNoAxesCombined, Database, Fingerprint, Layers3, MapPinned, RefreshCw, ScanLine } from 'lucide-react'
import { useInstitutionalData } from '../../app/data-availability'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { SourceContext } from '../../components/source-context'
import { HistoryPanel } from './history-panel'

const indicators = [
  { name: 'historical_rows', label: 'Series en el panel', detail: 'Incluye territorios especiales', icon: Database },
  { name: 'municipal_candidates', label: 'Candidatos municipales', detail: 'Catálogo retrospectivo · no acreditado', icon: MapPinned },
  { name: 'technical_positions', label: 'Posiciones históricas', detail: 'Malla técnica · no calendario oficial', icon: Layers3 },
]

export default function DashboardPage() {
  const { snapshot, availability, selectedCode, selectCode, retry } = useInstitutionalData()
  const ready = availability.status === 'ready'
  const period = snapshot?.overview.indicators[0]?.period.split('/')
  return <div className="page dashboard-page">
    <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line" />INTELIGENCIA EPIDEMIOLÓGICA</div><h1>Dashboard</h1><p>El histórico, el territorio y la próxima decisión.</p></div><div className="heading-actions"><span className="dataset-label"><Database size={15} aria-hidden="true" />Panel histórico</span><Button variant="outline" size="small" onClick={retry} disabled={availability.status === 'loading'}><RefreshCw size={15} aria-hidden="true" />Actualizar</Button></div></div>
    <section className="workspace-brief" aria-labelledby="brief-title"><span className="brief-icon"><ScanLine size={23} aria-hidden="true" /></span><div><h2 id="brief-title">Del dato al contexto territorial.</h2><p>Consulta observaciones históricas y prepara un pronóstico retrospectivo.</p></div><Button asChild><Link to="/predicciones"><ChartNoAxesCombined size={17} aria-hidden="true" />Nueva predicción</Link></Button></section>
    <section className="executive-metrics" aria-label="Indicadores estructurales del histórico">{indicators.map(({ name, label, detail, icon: Icon }) => {
      const indicator = snapshot?.overview.indicators.find(i => i.name === name)
      const value = indicator?.value
      return <article key={name}><div className="metric-label"><span>{label}</span><Icon size={18} aria-hidden="true" /></div>
        <strong className={availability.status === 'loading' ? 'metric-loading' : ''} aria-label={`${label}: ${value == null ? 'no disponible' : value}`}>{value == null ? '—' : value.toLocaleString('es-CO')}</strong>
        <div className="metric-detail">{value == null ? 'No disponible' : detail}</div>
        {indicator && <details className="metric-provenance"><summary>Procedencia del indicador</summary><dl><dt>Universo</dt><dd>{indicator.universe}</dd><dt>Regla</dt><dd>{indicator.aggregation}</dd><dt>Estado</dt><dd>{indicator.validation_status}</dd><dt>Período técnico</dt><dd>{indicator.period}</dd></dl></details>}
      </article>
    })}</section>
    <div className="dashboard-grid"><HistoryPanel />
      <div className="dashboard-rail"><section className="territory-panel panel" aria-labelledby="territory-title"><div className="panel-title-row"><div><span className="eyebrow">CATÁLOGO DE LA FUENTE</span><h2 id="territory-title">Territorios disponibles</h2></div><MapPinned size={20} aria-hidden="true" /></div>
        <p className="panel-description">Códigos candidatos para exploración retrospectiva.</p>
        {ready && snapshot ? <><div className="territory-list">{snapshot.territories.codes.slice(0, 3).map(code => <button key={code} className={selectedCode === code ? 'selected' : ''} onClick={() => selectCode(code)} aria-pressed={selectedCode === code}><span className="territory-symbol"><MapPinned size={17} aria-hidden="true" /></span><span><strong>{code}</strong><small>Candidato municipal</small></span><span className="territory-select-label">{selectedCode === code ? 'En vista' : 'Explorar'}</span></button>)}</div><p className="catalogue-note">{snapshot.territories.total.toLocaleString('es-CO')} códigos en el selector completo.</p></>
          : <div className="catalogue-empty"><MapPinned size={25} aria-hidden="true" /><p>{availability.status === 'loading' ? 'Consultando el catálogo…' : 'El catálogo aparecerá al consultar una fuente disponible.'}</p></div>}
        <Button asChild variant="outline" className="full-width"><Link to="/exploracion">Explorar catálogo completo</Link></Button>
      </section>
      <section className="prediction-launch" aria-labelledby="prediction-launch-title"><span className="launch-icon"><Activity size={22} aria-hidden="true" /></span><span className="eyebrow">PRONÓSTICO RETROSPECTIVO</span><h2 id="prediction-launch-title">Contrasta el próximo paso.</h2><p>Ocho estimaciones, un corte explícito y su contraste con lo observado.</p><Button asChild><Link to="/predicciones">Preparar una predicción</Link></Button><span className="launch-footnote">La ejecución comienza solo al solicitarla.</span></section></div>
    </div>
    <div className="data-scope-bar"><div><Fingerprint size={17} aria-hidden="true" /><span>{snapshot ? `Histórico ${period?.[0]?.slice(0, 4) ?? ''}–${period?.[1]?.slice(0, 4) ?? ''}` : 'Fuente pendiente de consulta'}</span></div><Badge tone="amber">Validación territorial pendiente</Badge><span>Datos técnicos retrospectivos. No acreditan riesgo ni confirman brotes.</span></div>
    <SourceContext />
  </div>
}
