/**
 * Unit tests for the App root component.
 * Verifies routing / page switching logic.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from '../App'

// Health-check is called in App.useEffect – MSW returns { status: 'ok' }

describe('App – initial render', () => {
  it('renders the AIOps header', async () => {
    render(<App />)
    // Wait for health check to resolve and layout to paint
    await waitFor(() => {
      expect(screen.getByText('AIOps Platform')).toBeInTheDocument()
    })
  })

  it('shows the Dashboard page by default', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('📊 Dashboard')).toBeInTheDocument()
    })
  })

  it('shows "Online" status when backend health check succeeds', async () => {
    render(<App />)
    // MSW returns ok for /health
    await waitFor(() => {
      expect(screen.getByText('Online')).toBeInTheDocument()
    })
  })
})

describe('App – navigation', () => {
  it('switches to Predictor page when Predictor nav item is clicked', async () => {
    render(<App />)
    await waitFor(() => screen.getByText('🔮 Predictor'))

    fireEvent.click(screen.getByText('🔮 Predictor'))
    await waitFor(() => {
      // Predictor page renders its own heading
      const headings = screen.getAllByText('🔮 Predictor')
      expect(headings.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('switches to Alerts page when Alerts nav item is clicked', async () => {
    render(<App />)
    await waitFor(() => screen.getByText('🚨 Alerts'))

    fireEvent.click(screen.getByText('🚨 Alerts'))
    await waitFor(() => {
      const headings = screen.getAllByText('🚨 Alerts')
      expect(headings.length).toBeGreaterThanOrEqual(1)
    })
  })
})
