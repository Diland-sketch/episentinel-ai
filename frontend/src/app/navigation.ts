import { LayoutDashboard, MapPinned, ChartNoAxesCombined, Database, FlaskConical, SlidersHorizontal } from 'lucide-react'

export const navigation = [
  { path: '/', title: 'Dashboard', icon: LayoutDashboard, description: 'Tu perspectiva general de la información epidemiológica.' },
  { path: '/exploracion', title: 'Exploración territorial', icon: MapPinned, description: 'El contexto de cada territorio, en un solo lugar.' },
  { path: '/predicciones', title: 'Predicciones', icon: ChartNoAxesCombined, description: 'Pronósticos con contexto, incertidumbre y trazabilidad.' },
  { path: '/datos', title: 'Ingreso de datos', icon: Database, description: 'Información confiable desde el primer registro.' },
  { path: '/laboratorio', title: 'Laboratorio ML', icon: FlaskConical, description: 'Un espacio para evaluar antes de concluir.' },
  { path: '/sistema', title: 'Información del sistema', icon: SlidersHorizontal, description: 'Disponibilidad, alcance y procedencia de la información.' },
] as const
