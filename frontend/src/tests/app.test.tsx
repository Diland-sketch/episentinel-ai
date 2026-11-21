import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import axe from 'axe-core'
import { App } from '../app/app'
import { DataState } from '../components/data-state'
import { apiConfiguration } from '../lib/api'

function renderApp(route = '/') {
  return render(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>)
}

describe('Dashboard and honest data availability', () => {
  it('renders an honest unavailable state when the real API cannot be reached', async () => {
    const fetchSpy = vi.spyOn(window, 'fetch')
    renderApp()
    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible()
    expect(await screen.findByRole('heading', { name: 'API no disponible' })).toBeVisible()
    expect(screen.getAllByText('No disponible')).toHaveLength(3)
    expect(screen.getByLabelText('Series en el panel: no disponible')).toHaveTextContent('—')
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/health', expect.objectContaining({ method: 'GET' }))
    expect(apiConfiguration.integrationEnabled).toBe(true)
  })

  it('has a keyboard skip link and a labelled main region', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.tab()
    expect(screen.getByRole('link', { name: 'Saltar al contenido' })).toHaveFocus()
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main-content')
  })

  it('supports loading and error messages without displaying fabricated data', () => {
    const view = render(<MemoryRouter><DataState state={{ status: 'loading' }} /></MemoryRouter>)
    expect(screen.getByRole('status')).toHaveTextContent('Consultando la fuente de datos')
    view.rerender(<MemoryRouter><DataState state={{ status: 'error', message: 'La consulta no está disponible.' }} /></MemoryRouter>)
    expect(screen.getByRole('alert')).toHaveTextContent('La consulta no está disponible.')
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })
})

describe('Navigation', () => {
  it.each([
    ['/exploracion', 'Exploración territorial'], ['/predicciones', 'Predicciones'],
    ['/datos', 'Ingreso de datos'], ['/laboratorio', 'Laboratorio ML'], ['/sistema', 'Información del sistema'],
  ])('renders %s and identifies the active sidebar link', (path, title) => {
    renderApp(path)
    expect(screen.getByRole('heading', { level: 1, name: title })).toBeVisible()
    const nav = screen.getByRole('navigation', { name: 'Navegación principal' })
    const activeLink = path === '/sistema'
      ? within(screen.getByRole('complementary')).getByRole('link', { name: title })
      : within(nav).getByRole('link', { name: title })
    expect(activeLink).toHaveAttribute('aria-current', 'page')
    expect(activeLink).toHaveClass('nav-active')
  })

  it('navigates from the dashboard action and moves focus to the content', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('link', { name: 'Explorar catálogo completo' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Exploración territorial' })).toBeVisible()
    expect(screen.getByRole('main')).toHaveFocus()
    expect(document.title).toBe('Exploración territorial · EpiSentinel AI')
  })

  it('collapses and expands the desktop sidebar without losing accessible names', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('button', { name: 'Contraer barra lateral' }))
    expect(screen.getByRole('button', { name: 'Expandir barra lateral' })).toHaveAttribute('aria-expanded', 'false')
    expect(within(screen.getByRole('navigation', { name: 'Navegación principal' })).getByRole('link', { name: 'Predicciones' })).toHaveAccessibleName('Predicciones')
    await user.click(screen.getByRole('button', { name: 'Expandir barra lateral' }))
    expect(screen.getByRole('button', { name: 'Contraer barra lateral' })).toHaveAttribute('aria-expanded', 'true')
  })

  it('opens the mobile drawer, closes with Escape and restores trigger focus', async () => {
    const user = userEvent.setup()
    renderApp()
    const trigger = screen.getByRole('button', { name: 'Abrir menú' })
    await user.click(trigger)
    expect(screen.getByRole('dialog', { name: 'Navegación principal' })).toBeVisible()
    expect(screen.getByRole('navigation', { name: 'Navegación móvil' })).toBeVisible()
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(trigger).toHaveFocus()
  })

  it('traps mobile focus and closes on route selection', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('button', { name: 'Abrir menú' }))
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Cerrar menú' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Abrir menú' }))
    await user.tab({ shift: true })
    expect(screen.getByRole('dialog')).toContainElement(document.activeElement as HTMLElement)
    await user.click(within(screen.getByRole('navigation', { name: 'Navegación móvil' })).getByRole('link', { name: 'Ingreso de datos' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Ingreso de datos' })).toBeVisible()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByText('No se han enviado ni guardado registros desde esta interfaz.')).toBeVisible()
  })

  it('shows a 404 with a working return link', async () => {
    const user = userEvent.setup()
    renderApp('/ruta-inexistente')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Este destino no está disponible')
    await user.click(screen.getByRole('link', { name: 'Volver al dashboard' }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Dashboard')
  })
})

describe('Automated accessibility', () => {
  // jsdom has no layout engine: contrast is checked visually in browser QA.
  it.each(['/', '/exploracion', '/predicciones', '/datos', '/laboratorio', '/sistema', '/404'])('has no axe violations on %s', async route => {
    renderApp(route)
    const result = await axe.run(document.body, { rules: { 'color-contrast': { enabled: false } } })
    expect(result.violations.map(({ id, nodes }) => ({ id, targets: nodes.map(n => n.target) }))).toEqual([])
  })

  it('has no axe violations in the open mobile drawer', async () => {
    renderApp()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir menú' }))
    const result = await axe.run(document.body, { rules: { 'color-contrast': { enabled: false } } })
    expect(result.violations).toEqual([])
  })
})
