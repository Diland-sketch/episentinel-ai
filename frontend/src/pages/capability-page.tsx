import { Link } from 'react-router'
import { ChartNoAxesCombined, Database, FileCheck2, FlaskConical, MapPinned, ShieldCheck } from 'lucide-react'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'

const capabilities = {
  exploration: {
    title: 'Exploración territorial', label: 'EL CONTEXTO DE CADA TERRITORIO', icon: MapPinned,
    description: 'Comprende dónde y cuándo se dispone de información epidemiológica.',
    heading: 'Cada territorio tiene su contexto',
    detail: 'La exploración territorial estará disponible cuando se integre una fuente institucional con cobertura y períodos identificados.',
    items: ['Selección de territorios', 'Series y períodos de referencia', 'Disponibilidad y procedencia'],
    note: 'La ausencia de información no representa ausencia de casos.',
  },
  predictions: {
    title: 'Predicciones', label: 'UNA PERSPECTIVA HACIA ADELANTE', icon: ChartNoAxesCombined,
    description: 'Estimaciones acompañadas de contexto y límites claros.',
    heading: 'Primero la evidencia, después la estimación',
    detail: 'La predicción retrospectiva permitirá contrastar estimaciones con observaciones históricas. Su conexión con el servicio de pronósticos está pendiente.',
    items: ['Corte y horizonte explícitos', 'Métodos y estados de ajuste', 'Intervalos e incertidumbre'],
    note: 'Un pronóstico no equivale a un brote confirmado ni garantiza desempeño futuro.',
  },
  data: {
    title: 'Ingreso de datos', label: 'INFORMACIÓN DESDE EL ORIGEN', icon: Database,
    description: 'Un punto de entrada para información trazable y consistente.',
    heading: 'Una fuente confiable hace la diferencia',
    detail: 'El ingreso de datos necesita reglas institucionales de validación y un servicio de recepción conectado. Esta versión no permite cargar ni guardar registros.',
    items: ['Fuente y versión identificadas', 'Validación antes de incorporar', 'Registro de incidencias'],
    note: 'No se han enviado ni guardado registros desde esta interfaz.',
  },
  laboratory: {
    title: 'Laboratorio ML', label: 'EVALUAR PARA COMPRENDER', icon: FlaskConical,
    description: 'Un espacio para estudiar modelos y sus resultados con rigor.',
    heading: 'Comparaciones que se puedan explicar',
    detail: 'Aquí se presentarán protocolos de evaluación temporal, métodos comparables y resultados trazables cuando se integren los servicios correspondientes.',
    items: ['Protocolos temporales', 'Comparación de métodos', 'Resultados y limitaciones'],
    note: 'No hay experimentos ni métricas de desempeño disponibles en esta versión.',
  },
} as const

export function CapabilityPage({ capability }: { capability: keyof typeof capabilities }) {
  const content = capabilities[capability]
  const Icon = content.icon
  return <div className="page capability-page">
    <div className="page-heading"><div><div className="eyebrow">{content.label}</div><h1>{content.title}</h1><p>{content.description}</p></div><Badge tone="amber">Integración pendiente</Badge></div>
    <section className="capability-panel"><div className="capability-visual" aria-hidden="true"><div className="capability-orbit"><Icon size={40} strokeWidth={1.2} /></div><span>CONTEXTO · TRAZABILIDAD</span></div>
      <div className="capability-content"><Badge>Capacidad en preparación</Badge><h2>{content.heading}</h2><p>{content.detail}</p><ul>{content.items.map(item => <li key={item}><FileCheck2 size={17} aria-hidden="true" />{item}</li>)}</ul><Button asChild variant="outline"><Link to="/sistema">Consultar información del sistema</Link></Button></div></section>
    <div className="context-note"><ShieldCheck size={20} aria-hidden="true" /><p>{content.note}</p></div>
    <Link className="text-link" to="/">Volver al dashboard</Link>
  </div>
}
