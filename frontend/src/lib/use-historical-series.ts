import { useEffect, useState } from 'react'
import { api, ApiError } from './api'
import type { HistoricalSeries } from './api-types'

type SeriesState = { key: string; status: 'loading' | 'ready' | 'error'; data: HistoricalSeries | null; message?: string }
export function useHistoricalSeries(code: string, sourceHash: string) {
  const key = `${code}:${sourceHash}`
  const [state, setState] = useState<SeriesState>({ key: '', status: 'loading', data: null })
  useEffect(() => {
    if (!code || !sourceHash) return
    const controller = new AbortController()
    void api.series(code, controller.signal).then(data => {
      if (data.source.sha256 !== sourceHash) throw new ApiError('La fuente de la serie cambió. Actualiza el dashboard.', 0, 'SOURCE_CHANGED')
      if (!controller.signal.aborted) setState({ key, status: 'ready', data })
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ key, status: 'error', data: null, message: error instanceof Error ? error.message : 'No se pudo cargar la serie.' })
    })
    return () => controller.abort()
  }, [code, sourceHash, key])
  return state.key === key ? state : { key, status: 'loading' as const, data: null }
}
