import { useState } from 'react'
import { MapPinned, Search } from 'lucide-react'
import { useInstitutionalData } from '../app/data-availability'
import { HistoryPanel } from '../features/dashboard/history-panel'
import { SourceContext } from '../components/source-context'
import { Badge } from '../components/ui/badge'

export function ExplorationPage() {
  const { snapshot, selectedCode, selectCode } = useInstitutionalData()
  const [search, setSearch] = useState('')
  const codes = snapshot?.territories.codes.filter(code => code.includes(search.trim())) ?? []
  return <div className="page"><div className="page-heading"><div><div className="eyebrow">CONTEXTO TERRITORIAL</div><h1>Exploración territorial</h1><p>Selecciona un código para consultar su serie original.</p></div><Badge tone="amber">Catálogo candidato</Badge></div>
    <div className="exploration-grid"><section className="panel catalogue-panel"><div className="panel-title-row"><h2>Catálogo municipal</h2><MapPinned size={20} aria-hidden="true" /></div><label className="search-field"><Search size={17} aria-hidden="true" /><input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar por código" aria-label="Buscar código territorial" /></label><p className="catalogue-note">{snapshot ? `${codes.length} códigos coincidentes · validación pendiente` : 'Esperando fuente de datos'}</p><div className="exploration-codes">{codes.map(code => <button key={code} aria-pressed={selectedCode === code} onClick={() => selectCode(code)} className={selectedCode === code ? 'selected' : ''}>{code}<span>{selectedCode === code ? 'En vista' : 'Consultar'}</span></button>)}</div>{snapshot && !codes.length && <p>No hay códigos coincidentes.</p>}</section><HistoryPanel /></div><SourceContext />
  </div>
}
