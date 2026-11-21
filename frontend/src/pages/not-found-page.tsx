import { Link } from 'react-router'
import { Compass } from 'lucide-react'
import { Button } from '../components/ui/button'

export function NotFoundPage() {
  return <div className="page not-found"><Compass size={42} strokeWidth={1.2} aria-hidden="true" /><span className="eyebrow">ERROR 404</span><h1>Este destino no está disponible</h1><p>La dirección puede haber cambiado. Vuelve a tu espacio de trabajo para continuar.</p><Button asChild><Link to="/">Volver al dashboard</Link></Button></div>
}
