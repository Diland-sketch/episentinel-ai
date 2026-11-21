import { Radio, Unplug, LoaderCircle } from 'lucide-react'
import { useDataAvailability } from '../app/data-availability'

export function ConnectionStatus() {
  const { status } = useDataAvailability()
  const label = status === 'ready' || status === 'empty' ? 'API conectada' : status === 'loading' ? 'Consultando API' : status === 'unavailable' ? 'Fuente no disponible' : status === 'error' ? 'Error de consulta' : 'API no disponible'
  const Icon = status === 'ready' || status === 'empty' ? Radio : status === 'loading' ? LoaderCircle : Unplug
  return <span className={`connection-status connection-${status}`} role="status"><Icon size={14} aria-hidden="true" /><span>{label}</span></span>
}
