import { lazy, Suspense, useState } from 'react'
import { Link } from 'react-router'
import { ChartNoAxesCombined, ChevronDown, Waves } from 'lucide-react'
import { useInstitutionalData } from '../../app/data-availability'
import { useHistoricalSeries } from '../../lib/use-historical-series'
import { Button } from '../../components/ui/button'
import { DataState } from '../../components/data-state'

const HistoricalChart = lazy(() => import('./historical-chart'))

export function HistoryPanel() {
  const { snapshot, availability, selectedCode, selectCode, retry } = useInstitutionalData()
  const series = useHistoricalSeries(selectedCode, snapshot?.overview.source.sha256 ?? '')
  const [windowSize, setWindowSize] = useState<'full' | 'recent'>('full')
  const points = windowSize === 'recent' ? series.data?.points.slice(-104) : series.data?.points
  const ready = availability.status === 'ready'
  return <section className="history-panel panel" aria-labelledby="history-title">
    <div className="panel-title-row"><div><span className="eyebrow">EXPLORACIÓN HISTÓRICA</span><h2 id="history-title">El comportamiento de los datos</h2></div><Waves size={20} aria-hidden="true" /></div>
    <div className="chart-toolbar"><div className="select-wrap"><label htmlFor="history-territory">Código territorial</label><div><select id="history-territory" disabled={!ready} value={selectedCode} onChange={event => selectCode(event.target.value)}>
      {!selectedCode && <option value="">Sin catálogo disponible</option>}
      {snapshot?.territories.codes.map(code => <option key={code} value={code}>{code} · Candidato municipal</option>)}
    </select><ChevronDown size={15} aria-hidden="true" /></div></div>
    <div className="segmented-control" role="group" aria-label="Ventana de la serie"><button disabled={!ready} aria-pressed={windowSize === 'full'} onClick={() => setWindowSize('full')}>Completa</button><button disabled={!ready} aria-pressed={windowSize === 'recent'} onClick={() => setWindowSize('recent')}>Últimas 104</button></div></div>
    {!ready ? <div className="chart-unavailable"><DataState state={availability} />{availability.status !== 'loading' && <Button variant="outline" size="small" onClick={retry}>Volver a consultar</Button>}</div>
      : series.status === 'loading' ? <div className="chart-skeleton" role="status"><span>Consultando la serie {selectedCode}…</span><div /><div /><div /></div>
      : series.status === 'error' ? <DataState state={{ status: 'error', message: series.message ?? 'La serie no está disponible.' }} />
      : !points?.length ? <DataState state={{ status: 'empty' }} />
      : <><div className="chart-caption"><span><i />Conteo observado · {selectedCode}</span><span>{points.length} posiciones</span></div>
        <Suspense fallback={<div className="chart-skeleton" role="status">Preparando visualización…</div>}><HistoricalChart points={points} code={selectedCode} /></Suspense>
        <div className="chart-footnote"><span>Fechas técnicas de 7 días · eventos 210 + 220 del panel heredado</span><details><summary>Ver valores accesibles</summary><div className="accessible-table"><table><caption>Serie original {selectedCode}; ventana seleccionada</caption><thead><tr><th>Posición</th><th>Fecha técnica</th><th>Observado</th></tr></thead><tbody>{points.map(p => <tr key={p.position}><td>{p.position}</td><td>{p.technical_date.slice(0, 10)}</td><td>{p.observed}</td></tr>)}</tbody></table></div></details></div></>}
    <div className="chart-action"><span>De la observación al pronóstico.</span><Button asChild variant="outline" size="small"><Link to="/predicciones"><ChartNoAxesCombined size={16} aria-hidden="true" />Preparar predicción</Link></Button></div>
  </section>
}
