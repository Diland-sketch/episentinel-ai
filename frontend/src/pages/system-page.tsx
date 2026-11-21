import { Database, FileCheck2, ShieldCheck, Unplug } from 'lucide-react'
import { Badge } from '../components/ui/badge'
import { useInstitutionalData } from '../app/data-availability'
import { SourceContext } from '../components/source-context'
import { Button } from '../components/ui/button'

export function SystemPage() {
  const { availability, snapshot, retry } = useInstitutionalData()
  return <div className="page system-page"><div className="page-heading"><div><div className="eyebrow">TRANSPARENCIA Y CONTEXTO</div><h1>Información del sistema</h1><p>Conoce qué información está disponible y cómo interpretarla.</p></div><Badge>Versión 2.0 · I1</Badge></div>
    <section className="system-panel"><div className="system-panel-heading"><Unplug size={22} aria-hidden="true" /><div><h2>{snapshot ? 'Fuente histórica conectada' : 'Disponibilidad de la fuente'}</h2><p>{snapshot ? 'Consultas de lectura al panel original a través de FastAPI.' : 'Consulta el estado del servicio sin sustituir información ausente.'}</p></div><Badge tone={snapshot ? 'teal' : 'amber'}>{snapshot ? 'Disponible' : availability.status}</Badge></div><dl className="system-details"><div><dt>API REST</dt><dd>{snapshot ? `Versión ${snapshot.health.version}` : 'Sin respuesta confirmada'}</dd></div><div><dt>Datos consultados por esta interfaz</dt><dd>{snapshot ? 'Panel histórico y catálogo candidato' : 'No disponibles'}</dd></div><div><dt>Ingreso desde esta interfaz</dt><dd>Pendiente de integración</dd></div><div><dt>Pronósticos</dt><dd>Retrospectivos · ejecución explícita</dd></div></dl><Button variant="outline" onClick={retry}>Volver a consultar disponibilidad</Button></section>
    <div className="system-guidance"><article><Database aria-hidden="true" /><h2>Una fuente, una identidad</h2><p>Los conjuntos institucionales deberán conservar origen, versión, período y cobertura. No se atribuyen datos históricos a esta sesión.</p></article><article><FileCheck2 aria-hidden="true" /><h2>Disponibilidad explícita</h2><p>Un valor no disponible se identifica como tal. No se reemplaza por cero ni se presenta como una medición realizada.</p></article><article><ShieldCheck aria-hidden="true" /><h2>Interpretación responsable</h2><p>Los pronósticos requieren una evaluación adecuada y no confirman brotes. La incertidumbre debe acompañar a cada resultado.</p></article></div>
    <SourceContext />
  </div>
}
