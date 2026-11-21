/** Explicitly synthetic HTTP fixtures, imported only by tests. Never production data. */
import type { HistoricalSeries, Overview, Territories, Methodology } from '../lib/api-types'
export const source = { path: 'test/synthetic-panel.parquet', sha256: 'a'.repeat(64), calendar: 'technical_7D_not_official' }
export const health = { status: 'ok', version: '2.0.0', historical_source_available: true }
export const overview: Overview = {
  source, limitations: ['Synthetic test fixture; not epidemiological evidence.'],
  indicators: [
    { name: 'historical_rows', value: 2 }, { name: 'municipal_candidates', value: 2 }, { name: 'technical_positions', value: 20 },
  ].map(i => ({ ...i, source: source.sha256, period: '2020-01-01/2020-05-13', universe: 'synthetic tests', aggregation: 'test count', validation_status: 'structural_only_not_epidemiological' })),
}
export const territories: Territories = { source, codes: ['05001', '76001'], total: 2, offset: 0, catalog_validation: 'pending' }
export const methodology: Methodology = { forecast_methods: ['ultimo_valor', 'sarima_sin_estacional'], allowed_cuts: [727, 779], horizon: 8, limitations: ['Synthetic test configuration'] }
export const historical = (code: string): HistoricalSeries => ({ source, series: code, limitations: ['Technical dates'], points: [
  { position: 0, technical_date: '2020-01-01T00:00:00', observed: 0 },
  { position: 1, technical_date: '2020-01-08T00:00:00', observed: 4 },
] })
export function json(value: unknown, status = 200) { return new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } }) }
export function fixtureFetch(input: RequestInfo | URL): Promise<Response> {
  const path = String(input)
  if (path.endsWith('/health')) return Promise.resolve(json(health))
  if (path.endsWith('/overview')) return Promise.resolve(json(overview))
  if (path.includes('/territories')) return Promise.resolve(json(territories))
  if (path.includes('/series?')) return Promise.resolve(json(historical(new URL(path, 'http://localhost').searchParams.get('series') ?? '')))
  if (path.endsWith('/methodology')) return Promise.resolve(json(methodology))
  return Promise.resolve(json({ error: { code: 'UNEXPECTED_TEST_ROUTE', message: path } }, 404))
}
