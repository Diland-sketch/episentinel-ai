import { Fingerprint, Info } from 'lucide-react'
import { useInstitutionalData } from '../app/data-availability'

export function SourceContext() {
  const { snapshot } = useInstitutionalData()
  if (!snapshot) return null
  return <div className="source-context"><div className="source-identity"><Fingerprint size={17} aria-hidden="true" /><span>Fuente verificable</span><code title={snapshot.overview.source.sha256}>SHA-256 {snapshot.overview.source.sha256.slice(0, 12)}…</code></div>
    <details><summary><Info size={15} aria-hidden="true" />Contexto y límites del histórico</summary><ul>{snapshot.overview.limitations.map(text => <li key={text}>{text}</li>)}</ul><p className="source-path">{snapshot.overview.source.path}</p></details>
  </div>
}
