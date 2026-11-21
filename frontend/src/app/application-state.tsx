import { useEffect, useState, type ReactNode } from 'react'
import { ApplicationContext, type SourceSnapshot } from './data-availability'
import { api, ApiError, loadCatalogue, type DataAvailability } from '../lib/api'

export function ApplicationProvider({ children }: { children: ReactNode }) {
  const [attempt, setAttempt] = useState(0)
  const [availability, setAvailability] = useState<DataAvailability>({ status: 'loading' })
  const [snapshot, setSnapshot] = useState<SourceSnapshot | null>(null)
  const [selection, setSelection] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const health = await api.health(controller.signal)
        if (!health.historical_source_available) { if (!controller.signal.aborted) setAvailability({ status: 'unavailable' }); return }
        const [overview, territories] = await Promise.all([api.overview(controller.signal), loadCatalogue(controller.signal)])
        if (overview.source.sha256 !== territories.source.sha256 || overview.indicators.some(i => i.source !== overview.source.sha256)) throw new ApiError('La fuente cambió durante la consulta. Actualiza para volver a cargarla.', 0, 'SOURCE_CHANGED')
        if (!controller.signal.aborted) { setSnapshot({ health, overview, territories }); setAvailability({ status: territories.total ? 'ready' : 'empty' }) }
      } catch (error) {
        if (controller.signal.aborted) return
        setAvailability(error instanceof ApiError && error.code === 'NETWORK_ERROR' ? { status: 'disconnected' }
          : error instanceof ApiError && error.status === 503 ? { status: 'unavailable' }
          : { status: 'error', message: error instanceof Error ? error.message : 'No se pudo consultar la fuente.' })
      }
    }
    void load()
    return () => controller.abort()
  }, [attempt])
  const selectedCode = snapshot?.territories.codes.includes(selection) ? selection : (snapshot?.territories.codes[0] ?? '')
  function retry() { setAvailability({ status: 'loading' }); setSnapshot(null); setAttempt(value => value + 1) }
  function selectCode(code: string) { if (snapshot?.territories.codes.includes(code)) setSelection(code) }
  return <ApplicationContext value={{ availability, snapshot, selectedCode, selectCode, retry }}>{children}</ApplicationContext>
}

