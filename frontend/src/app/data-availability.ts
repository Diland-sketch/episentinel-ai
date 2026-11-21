import { createContext, useContext } from 'react'
import type { DataAvailability } from '../lib/api'

import type { Health, Overview, Territories } from '../lib/api-types'

export interface SourceSnapshot { health: Health; overview: Overview; territories: Territories }
export interface ApplicationState {
  availability: DataAvailability; snapshot: SourceSnapshot | null; selectedCode: string
  selectCode: (code: string) => void; retry: () => void
}
export const ApplicationContext = createContext<ApplicationState>({
  availability: { status: 'loading' }, snapshot: null, selectedCode: '', selectCode: () => {}, retry: () => {},
})
export function useInstitutionalData() { return useContext(ApplicationContext) }
export function useDataAvailability() { return useInstitutionalData().availability }
