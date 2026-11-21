import { Routes, Route, useLocation } from 'react-router'
import { useEffect, useRef } from 'react'
import { ApplicationProvider } from './application-state'
import { AppLayout } from '../components/layout/app-layout'
import DashboardPage from '../features/dashboard/dashboard-page'
import { CapabilityPage } from '../pages/capability-page'
import { SystemPage } from '../pages/system-page'
import { NotFoundPage } from '../pages/not-found-page'
import { ExplorationPage } from '../pages/exploration-page'
import { PredictionsPage } from '../pages/predictions-page'

function RouteFocus() {
  const { pathname } = useLocation()
  const previous = useRef(pathname)
  useEffect(() => {
    if (previous.current !== pathname) {
      document.getElementById('main-content')?.focus()
      window.scrollTo({ top: 0, behavior: 'instant' })
      previous.current = pathname
    }
  }, [pathname])
  return null
}

export function App() {
  return <ApplicationProvider><RouteFocus /><Routes><Route element={<AppLayout />}>
    <Route index element={<DashboardPage />} />
    <Route path="exploracion" element={<ExplorationPage />} />
    <Route path="predicciones" element={<PredictionsPage />} />
    <Route path="datos" element={<CapabilityPage capability="data" />} />
    <Route path="laboratorio" element={<CapabilityPage capability="laboratory" />} />
    <Route path="sistema" element={<SystemPage />} />
    <Route path="*" element={<NotFoundPage />} />
  </Route></Routes></ApplicationProvider>
}
