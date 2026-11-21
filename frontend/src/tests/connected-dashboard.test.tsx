import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import axe from 'axe-core'
import { App } from '../app/app'
import { fixtureFetch, json, health, historical, overview, source, territories } from './api-fixtures'

vi.mock('../features/dashboard/historical-chart', () => ({ default: ({ code }: { code: string }) => <div role="img" aria-label={`Synthetic test chart ${code}`} /> }))
vi.mock('../features/dashboard/forecast-chart', () => ({ default: () => <div role="img" aria-label="Synthetic forecast chart" /> }))
beforeEach(() => { vi.mocked(fetch).mockImplementation(fixtureFetch) })
const renderApp = (route = '/') => render(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>)
const postCount = () => vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST').length

describe('Dashboard connected to the contract', () => {
  it('shows structural indicators, real source identity and the complete catalogue without fitting models', async () => {
    renderApp()
    expect(await screen.findByText('API conectada')).toBeVisible()
    expect(screen.getByLabelText('Series en el panel: 2')).toBeVisible()
    expect(screen.getByLabelText('Posiciones históricas: 20')).toBeVisible()
    expect(await screen.findByRole('img', { name: 'Synthetic test chart 05001' })).toBeVisible()
    expect(screen.getByLabelText('Código territorial')).toHaveValue('05001')
    expect(screen.getByTitle(source.sha256)).toBeVisible()
    expect(postCount()).toBe(0)
  })
  it('does not turn a missing source or empty catalogue into zeros', async () => {
    vi.mocked(fetch).mockResolvedValue(json({ ...health, historical_source_available: false }))
    renderApp()
    expect(await screen.findByRole('heading', { name: 'Fuente histórica no disponible' })).toBeVisible()
    expect(screen.getByLabelText('Series en el panel: no disponible')).toHaveTextContent('—')
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('reports an empty catalogue independently from connection health', async () => {
    vi.mocked(fetch).mockImplementation(input => String(input).includes('/territories') ? Promise.resolve(json({ ...territories, codes: [], total: 0 })) : fixtureFetch(input))
    renderApp()
    expect(await screen.findByRole('heading', { name: 'Sin información para mostrar' })).toBeVisible()
    expect(screen.getByText('API conectada')).toBeVisible()
    expect(postCount()).toBe(0)
  })
  it('does not publish indicators from inconsistent source identities', async () => {
    vi.mocked(fetch).mockImplementation(input => String(input).includes('/overview') ? Promise.resolve(json({ ...overview, source: { ...source, sha256: 'b'.repeat(64) } })) : fixtureFetch(input))
    renderApp()
    expect(await screen.findByText('La fuente cambió durante la consulta. Actualiza para volver a cargarla.')).toBeVisible()
    expect(screen.getByLabelText('Series en el panel: no disponible')).toHaveTextContent('—')
  })
  it('ignores a late response for the previously selected territory', async () => {
    let resolveOld!: (response: Response) => void
    vi.mocked(fetch).mockImplementation(input => String(input).includes('series=05001') ? new Promise(resolve => { resolveOld = resolve }) : fixtureFetch(input))
    renderApp()
    await screen.findByText('API conectada')
    await waitFor(() => expect(resolveOld).toBeDefined())
    await userEvent.selectOptions(screen.getByLabelText('Código territorial'), '76001')
    expect(await screen.findByRole('img', { name: 'Synthetic test chart 76001' })).toBeVisible()
    await act(async () => { resolveOld(json(historical('05001'))) })
    expect(screen.queryByRole('img', { name: 'Synthetic test chart 05001' })).not.toBeInTheDocument()
  })
  it('exposes unchanged observations in an accessible table', async () => {
    renderApp()
    await screen.findByRole('img', { name: 'Synthetic test chart 05001' })
    await userEvent.click(screen.getByText('Ver valores accesibles'))
    const table = screen.getByRole('table')
    expect(table).toHaveTextContent('2020-01-01')
    expect(table).toHaveTextContent('2020-01-08')
    expect(table.querySelectorAll('tbody tr')).toHaveLength(2)
    expect(table.querySelector('tbody tr td:last-child')).toHaveTextContent('0')
  })
  it('executes a forecast only after the explicit button and invalidates results when controls change', async () => {
    const user = userEvent.setup()
    const result = {
      request: { series: '05001', cut: 727, method: 'ultimo_valor', horizon: 8, source_sha256: source.sha256, request_id: 'synthetic-test-only' },
      forecast: { status: 'ok', fit_status: 'no_requiere_ajuste', interval_level: null, warnings: [], points: Array.from({ length: 8 }, () => ({})) },
      evaluation: { rows: Array.from({ length: 8 }, (_, i) => ({ position: 728 + i, technical_date: '2021-01-01', yhat: 4, observed: 3, lo: null, hi: null })), metrics: { MAE: 1 } }, limitations: ['Synthetic test only'],
    }
    vi.mocked(fetch).mockImplementation(input => String(input).includes('/forecasts/') ? Promise.resolve(json(result)) : fixtureFetch(input))
    renderApp('/predicciones')
    const button = await screen.findByRole('button', { name: 'Ejecutar predicción' })
    await waitFor(() => expect(button).toBeEnabled())
    expect(postCount()).toBe(0)
    await user.click(button)
    expect(await screen.findByRole('heading', { name: 'Estimación y observación · 05001' })).toBeVisible()
    expect(postCount()).toBe(1)
    expect(fetch).toHaveBeenCalledWith('/api/v1/forecasts/retrospective', expect.objectContaining({ method: 'POST', body: JSON.stringify({ series: '05001', cut: 727, method: 'ultimo_valor', horizon: 8 }) }))
    await user.selectOptions(screen.getByLabelText('Corte inclusivo'), '779')
    expect(screen.queryByRole('heading', { name: 'Estimación y observación · 05001' })).not.toBeInTheDocument()
    expect(postCount()).toBe(1)
  })
  it('shows structured forecast failures without a partial curve or silent fallback', async () => {
    vi.mocked(fetch).mockImplementation(input => String(input).includes('/forecasts/') ? Promise.resolve(json({ error: { code: 'NO_CONVERGENCIA', message: 'El ajuste no convergió' }, request_id: 'test-failure' }, 422)) : fixtureFetch(input))
    renderApp('/predicciones')
    const button = await screen.findByRole('button', { name: 'Ejecutar predicción' })
    await waitFor(() => expect(button).toBeEnabled())
    await userEvent.click(button)
    expect(await screen.findByRole('alert')).toHaveTextContent('NO_CONVERGENCIA')
    expect(screen.queryByRole('img', { name: 'Synthetic forecast chart' })).not.toBeInTheDocument()
    expect(postCount()).toBe(1)
  })
  it('has no axe violations with connected data', async () => {
    renderApp()
    await screen.findByRole('img', { name: 'Synthetic test chart 05001' })
    const result = await axe.run(document.body, { rules: { 'color-contrast': { enabled: false } } })
    expect(result.violations).toEqual([])
  })
})
