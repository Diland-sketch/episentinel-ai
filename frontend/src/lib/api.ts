import type { Health, Overview, Territories, HistoricalSeries, Methodology, Retrospective, ForecastInput } from './api-types'

/** Consumed routes: docs/api/openapi.json, API 2.0.0 (#35). */
export const apiConfiguration = Object.freeze({
  basePath: (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || '/api/v1',
  integrationEnabled: true,
  contractAvailable: true,
})

export type DataAvailability =
  | { status: 'disconnected' }
  | { status: 'loading' }
  | { status: 'ready' }
  | { status: 'empty' }
  | { status: 'unavailable' }
  | { status: 'error'; message: string }

export class ApiError extends Error {
  constructor(message: string, public readonly status = 0, public readonly code = 'NETWORK_ERROR', public readonly requestId?: string) {
    super(message); this.name = 'ApiError'
  }
}

export function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === 'object' && value !== null && !Array.isArray(value) }
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === 'string')
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
const source = (v: unknown) => isRecord(v) && typeof v.path === 'string' && typeof v.sha256 === 'string' && typeof v.calendar === 'string'
const invalid = () => new ApiError('La respuesta no coincide con el contrato de la API.', 0, 'INVALID_RESPONSE')

async function request<T>(path: string, validate: (value: unknown) => boolean, signal?: AbortSignal, body?: unknown): Promise<T> {
  const timeout = AbortSignal.timeout(body ? 50_000 : 12_000)
  let response: Response
  try {
    response = await fetch(`${apiConfiguration.basePath}${path}`, {
      method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json', Accept: 'application/json' } : { Accept: 'application/json' },
      body: body ? JSON.stringify(body) : undefined, signal: signal ? AbortSignal.any([signal, timeout]) : timeout, cache: 'no-store',
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new ApiError(timeout.aborted ? 'La consulta superó el tiempo de espera.' : 'No se pudo contactar con la API local.', 0, timeout.aborted ? 'TIMEOUT' : 'NETWORK_ERROR')
  }
  let value: unknown
  try { value = await response.json() } catch {
    if ([502, 503, 504].includes(response.status)) throw new ApiError('La API no está disponible.', response.status, 'NETWORK_ERROR')
    throw invalid()
  }
  if (!response.ok) {
    const envelope = isRecord(value) ? value : {}
    const error = isRecord(envelope.error) ? envelope.error : {}
    throw new ApiError(typeof error.message === 'string' ? error.message : 'No se pudo completar la consulta.', response.status,
      typeof error.code === 'string' ? error.code : 'HTTP_ERROR', typeof envelope.request_id === 'string' ? envelope.request_id : undefined)
  }
  if (!validate(value)) throw invalid()
  return value as T
}

export const api = {
  health: (signal?: AbortSignal) => request<Health>('/health', x => isRecord(x) && x.status === 'ok' && typeof x.version === 'string' && typeof x.historical_source_available === 'boolean', signal),
  overview: (signal?: AbortSignal) => request<Overview>('/overview', x => isRecord(x) && source(x.source) && strings(x.limitations) && Array.isArray(x.indicators) && x.indicators.every(i => isRecord(i) && typeof i.name === 'string' && (i.value === null || finite(i.value)) && ['source', 'period', 'universe', 'aggregation', 'validation_status'].every(k => typeof i[k] === 'string')), signal),
  territories: (offset: number, signal?: AbortSignal) => request<Territories>(`/territories?offset=${offset}&limit=1000`, x => isRecord(x) && source(x.source) && strings(x.codes) && x.codes.every(c => /^\d{5}$/.test(c)) && Number.isInteger(x.total) && Number.isInteger(x.offset) && typeof x.catalog_validation === 'string', signal),
  series: (code: string, signal?: AbortSignal) => request<HistoricalSeries>(`/series?series=${encodeURIComponent(code)}&start=0&limit=832`, x => isRecord(x) && x.series === code && source(x.source) && strings(x.limitations) && Array.isArray(x.points) && x.points.every(p => isRecord(p) && Number.isInteger(p.position) && typeof p.technical_date === 'string' && finite(p.observed) && p.observed >= 0), signal),
  methodology: (signal?: AbortSignal) => request<Methodology>('/methodology', x => isRecord(x) && strings(x.forecast_methods) && Array.isArray(x.allowed_cuts) && x.allowed_cuts.every(c => Number.isInteger(c)) && x.horizon === 8 && strings(x.limitations), signal),
  forecast: (body: ForecastInput, signal?: AbortSignal) => request<Retrospective>('/forecasts/retrospective', x => isRecord(x) && isRecord(x.request) && isRecord(x.forecast) && isRecord(x.evaluation) && strings(x.limitations) &&
    x.request.series === body.series && x.request.cut === body.cut && x.request.method === body.method && x.request.horizon === body.horizon && typeof x.request.source_sha256 === 'string' && typeof x.request.request_id === 'string' &&
    x.forecast.status === 'ok' && typeof x.forecast.fit_status === 'string' && (x.forecast.interval_level === null || finite(x.forecast.interval_level)) && Array.isArray(x.forecast.points) && x.forecast.points.length === 8 &&
    Array.isArray(x.evaluation.rows) && x.evaluation.rows.length === 8 && x.evaluation.rows.every(p => isRecord(p) && Number.isInteger(p.position) && typeof p.technical_date === 'string' && finite(p.yhat) && (p.observed === null || finite(p.observed)) && (p.lo === null || finite(p.lo)) && (p.hi === null || finite(p.hi))) &&
    Array.isArray(x.forecast.warnings) && x.forecast.warnings.every(w => isRecord(w) && typeof w.message === 'string') && isRecord(x.evaluation.metrics) && Object.values(x.evaluation.metrics).every(m => m === null || finite(m)), signal, body),
}

export async function loadCatalogue(signal?: AbortSignal): Promise<Territories> {
  const first = await api.territories(0, signal)
  if (first.offset !== 0 || first.total < 0 || first.codes.length > first.total) throw invalid()
  const codes = [...first.codes]
  while (codes.length < first.total) {
    const next = await api.territories(codes.length, signal)
    if (!next.codes.length || next.offset !== codes.length || next.total !== first.total || next.source.sha256 !== first.source.sha256) throw invalid()
    codes.push(...next.codes)
    if (codes.length > first.total) throw invalid()
  }
  if (new Set(codes).size !== codes.length) throw invalid()
  return { ...first, codes }
}
