import { describe, it, expect, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { api, ApiError, loadCatalogue } from '../lib/api'
import { json, health, source, territories, historical } from './api-fixtures'

describe('Existing HTTP contract consumer', () => {
  it('uses only routes in the actual repository OpenAPI document', () => {
    const spec = JSON.parse(readFileSync(resolve(process.cwd(), '../docs/api/openapi.json'), 'utf-8')) as { paths: Record<string, unknown> }
    for (const route of ['/health', '/overview', '/territories', '/series', '/methodology', '/forecasts/retrospective']) {
      expect(spec.paths).toHaveProperty(`/api/v1${route}`)
    }
  })
  it('validates the response envelope rather than trusting an HTML fallback', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('<html>not an API</html>', { status: 200 }))
    await expect(api.health()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
  it('preserves HTTP codes and request identity from structured failures', async () => {
    vi.mocked(fetch).mockResolvedValue(json({ error: { code: 'BUSY', message: 'Slot ocupado' }, request_id: 'http-test' }, 429))
    await expect(api.health()).rejects.toMatchObject({ status: 429, code: 'BUSY', requestId: 'http-test' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('rejects a malformed health payload', async () => {
    vi.mocked(fetch).mockResolvedValue(json({ ...health, historical_source_available: 'yes' }))
    await expect(api.health()).rejects.toBeInstanceOf(ApiError)
  })
  it('rejects invalid series without replacing values or interpreting calendar dates', async () => {
    const data = historical('05001'); data.points[0]!.observed = -1
    vi.mocked(fetch).mockResolvedValue(json(data))
    await expect(api.series('05001')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
  it('loads every page of the real catalogue and keeps codes as strings', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(json({ ...territories, codes: ['05001'] }))
      .mockResolvedValueOnce(json({ ...territories, codes: ['76001'], offset: 1 }))
    expect((await loadCatalogue()).codes).toEqual(['05001', '76001'])
    expect(fetch).toHaveBeenNthCalledWith(2, '/api/v1/territories?offset=1&limit=1000', expect.any(Object))
  })
  it.each(['empty-page', 'changed-source', 'duplicate', 'wrong-offset'])('rejects inconsistent catalogue pagination: %s', async failure => {
    vi.mocked(fetch).mockResolvedValueOnce(json({ ...territories, codes: ['05001'] }))
    vi.mocked(fetch).mockResolvedValueOnce(json({ ...territories, codes: failure === 'empty-page' ? [] : failure === 'duplicate' ? ['05001'] : ['76001'], offset: failure === 'wrong-offset' ? 0 : 1, source: failure === 'changed-source' ? { ...source, sha256: 'b'.repeat(64) } : source }))
    await expect(loadCatalogue()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
  it('distinguishes connection failure and does not retry on its own', async () => {
    await expect(api.health()).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
