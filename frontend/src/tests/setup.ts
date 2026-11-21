import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

afterEach(() => { cleanup(); vi.restoreAllMocks() })
// axe probes canvas support; jsdom does not implement a rendering context.
beforeEach(() => { vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null) })
beforeEach(() => { vi.spyOn(window, 'fetch').mockRejectedValue(new TypeError('Test: no API configured')) })
class TestResizeObserver { observe() {} unobserve() {} disconnect() {} }
Object.defineProperty(window, 'ResizeObserver', { value: TestResizeObserver })

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false, media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
  })),
})
Object.defineProperty(window, 'scrollTo', { writable: true, value: vi.fn() })
