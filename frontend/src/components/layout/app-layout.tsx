import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router'
import { ChevronRight, CircleHelp, Menu } from 'lucide-react'
import { navigation } from '../../app/navigation'
import { Button } from '../ui/button'
import { Sheet, SheetContent, SheetTrigger } from '../ui/sheet'
import { Sidebar } from './sidebar'
import { ConnectionStatus } from '../connection-status'

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { pathname } = useLocation()
  const title = navigation.find(item => item.path === pathname)?.title ?? 'Página no encontrada'
  useEffect(() => { document.title = `${title} · EpiSentinel AI` }, [title])
  useEffect(() => {
    const media = window.matchMedia('(min-width: 1024px)')
    const closeOnDesktop = () => { if (media.matches) setMobileOpen(false) }
    media.addEventListener('change', closeOnDesktop)
    return () => media.removeEventListener('change', closeOnDesktop)
  }, [])

  return <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
    <a className="skip-link" href="#main-content">Saltar al contenido</a>
    <aside className="desktop-sidebar" aria-label="Barra lateral"><Sidebar collapsed={collapsed} onCollapse={() => setCollapsed(value => !value)} /></aside>
    <div className="workspace">
      <header className="app-header">
        <div className="header-left">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild><Button className="mobile-menu" variant="ghost" size="icon" aria-label="Abrir menú" aria-expanded={mobileOpen}><Menu size={22} aria-hidden="true" /></Button></SheetTrigger>
            <SheetContent><Sidebar mobile onNavigate={() => setMobileOpen(false)} /></SheetContent>
          </Sheet>
          <nav aria-label="Breadcrumb"><ol className="breadcrumb"><li><Link to="/">Espacio de trabajo</Link></li><li aria-hidden="true"><ChevronRight size={13} /></li><li aria-current="page">{title}</li></ol></nav>
          <span className="header-mobile-title">{title}</span>
        </div>
        <div className="header-right"><ConnectionStatus />
          <span className="header-divider" /><Button asChild variant="ghost" size="icon"><Link to="/sistema" aria-label="Consultar información del sistema"><CircleHelp size={20} aria-hidden="true" /></Link></Button>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}><Outlet /></main>
      <footer className="app-footer"><span>EpiSentinel AI <span className="footer-divider">/</span> Inteligencia epidemiológica</span><Link to="/sistema">Alcance y procedencia</Link></footer>
    </div>
  </div>
}
