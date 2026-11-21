import { NavLink } from 'react-router'
import { PanelLeftClose, PanelLeftOpen, ShieldCheck } from 'lucide-react'
import { navigation } from '../../app/navigation'
import { Button } from '../ui/button'

export function Brand({ compact = false }: { compact?: boolean }) {
  return <div className="brand"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
    {!compact && <div><span className="brand-name">EpiSentinel <b>AI</b></span><span className="brand-subtitle">Inteligencia epidemiológica</span></div>}
  </div>
}

export function Sidebar({ collapsed = false, onCollapse, onNavigate, mobile = false }:
  { collapsed?: boolean; onCollapse?: () => void; onNavigate?: () => void; mobile?: boolean }) {
  return <div className={`sidebar-inner ${collapsed ? 'is-collapsed' : ''}`}>
    <div className="sidebar-brand"><Brand compact={collapsed} /></div>
    <div className="nav-section-label" aria-hidden="true">{collapsed ? '—' : 'ESPACIO DE TRABAJO'}</div>
    <nav aria-label={mobile ? 'Navegación móvil' : 'Navegación principal'}>
      {navigation.slice(0, 5).map(({ path, title, icon: Icon }) => <NavLink key={path} to={path} end={path === '/'} onClick={onNavigate}
        title={collapsed ? title : undefined} className={({ isActive }) => `nav-link ${isActive ? 'nav-active' : ''}`}>
        <Icon size={19} aria-hidden="true" /><span className={collapsed ? 'sr-only' : ''}>{title}</span>
      </NavLink>)}
    </nav>
    <div className="sidebar-bottom">
      {!collapsed && <div className="sidebar-note"><ShieldCheck size={20} aria-hidden="true" /><strong>Una fuente. Todo el contexto.</strong><p>Histórico verificable.<br />Pronósticos trazables.</p></div>}
      <NavLink to="/sistema" onClick={onNavigate} title={collapsed ? 'Información del sistema' : undefined} className={({ isActive }) => `nav-link ${isActive ? 'nav-active' : ''}`}>
        <ShieldCheck size={19} aria-hidden="true" /><span className={collapsed ? 'sr-only' : ''}>Información del sistema</span>
      </NavLink>
      {!mobile && <Button variant="ghost" className="collapse-button" onClick={onCollapse} aria-label={collapsed ? 'Expandir barra lateral' : 'Contraer barra lateral'} aria-expanded={!collapsed}>
        {collapsed ? <PanelLeftOpen size={19} aria-hidden="true" /> : <><PanelLeftClose size={19} aria-hidden="true" /><span>Contraer menú</span></>}
      </Button>}
      {!collapsed && <div className="sidebar-version">EPISENTINEL AI <span>2.0 · I1</span></div>}
    </div>
  </div>
}
