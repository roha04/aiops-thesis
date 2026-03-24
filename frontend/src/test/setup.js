import '@testing-library/jest-dom'
import { server } from './server'
import { beforeAll, afterEach, afterAll } from 'vitest'

// jsdom does not implement ResizeObserver (used by recharts ResponsiveContainer)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Start MSW before all tests in any file that imports this setup
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
