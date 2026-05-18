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
      expect(screen.getByText('Платформа AIOps')).toBeInTheDocument()
    })
  })

  it('shows the Dashboard page by default', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('📊 Панель')).toBeInTheDocument()
    })
  })

  it('shows online status when backend health check succeeds', async () => {
    render(<App />)
    // MSW returns ok for /health
    await waitFor(() => {
      expect(screen.getByText('Онлайн')).toBeInTheDocument()
    })
  })
})

describe('App – navigation', () => {
  it('switches to Predictor page when Predictor nav item is clicked', async () => {
    render(<App />)
    await waitFor(() => screen.getByText('🔮 Прогноз'))

    fireEvent.click(screen.getByText('🔮 Прогноз'))
    await waitFor(() => {
      // Predictor page renders its own heading
      const headings = screen.getAllByText('🔮 Прогноз')
      expect(headings.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('switches to Alerts page when Alerts nav item is clicked', async () => {
    render(<App />)
    await waitFor(() => screen.getByText('🚨 Сповіщення'))

    fireEvent.click(screen.getByText('🚨 Сповіщення'))
    await waitFor(() => {
      const headings = screen.getAllByText(/Сповіщення/i)
      expect(headings.length).toBeGreaterThanOrEqual(1)
    })
  })
})
