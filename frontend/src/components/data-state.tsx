import { Database, LoaderCircle, TriangleAlert } from 'lucide-react'
import type { DataAvailability } from '../lib/api'
import { Button } from './ui/button'
import { Link } from 'react-router'

export function DataState({ state }: { state: DataAvailability }) {
  if (state.status === 'loading') return <div className="data-state" role="status"><LoaderCircle className="loading-icon" aria-hidden="true" /><h3>Consultando la fuente de datos</h3><p>La información se mostrará cuando termine la consulta.</p></div>
  if (state.status === 'error') return <div className="data-state" role="alert"><TriangleAlert aria-hidden="true" /><h3>No pudimos consultar la información</h3><p>{state.message}</p><Button asChild variant="outline"><Link to="/sistema">Consultar estado del sistema</Link></Button></div>
  if (state.status === 'ready') return null
  return <div className="data-state"><div className="empty-icon"><Database size={24} strokeWidth={1.5} aria-hidden="true" /></div>
    <h3>{state.status === 'disconnected' ? 'API no disponible' : state.status === 'unavailable' ? 'Fuente histórica no disponible' : 'Sin información para mostrar'}</h3>
    <p>{state.status === 'disconnected' ? 'No hay conexión con el servicio. Puedes volver a consultar sin perder tu selección.' : state.status === 'unavailable' ? 'La API no dispone de un panel histórico compatible. No se generan datos sustitutos.' : 'La fuente no contiene territorios disponibles. No se interpretan las ausencias como cero.'}</p>
    <Button asChild variant="outline" size="small"><Link to="/datos">Conocer el ingreso de datos</Link></Button>
  </div>
}
