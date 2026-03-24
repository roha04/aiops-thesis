/**
 * Unit tests for the Dashboard page.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Dashboard from '../pages/Dashboard'

describe('Dashboard – loading state', () => {
  it('shows loading spinner initially', () => {
    render(<Dashboard />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})

describe('Dashboard – after data loads', () => {
  it('renders the heading', async () => {
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('📊 Dashboard')).toBeInTheDocument()
    })
  })

  it('renders Total Alerts KPI card', async () => {
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Total Alerts (7d)')).toBeInTheDocument()
      // Mock returns total_alerts: 12
      expect(screen.getByText('12')).toBeInTheDocument()
    })
  })

  it('renders Model Accuracy KPI card with correct value', async () => {
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Model Accuracy')).toBeInTheDocument()
      // accuracy 0.92 → "92.0%"
      expect(screen.getByText('92.0%')).toBeInTheDocument()
    })
  })

  it('renders F1 Score KPI card', async () => {
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('F1 Score')).toBeInTheDocument()
      // f1_score 0.895 → "0.895"
      expect(screen.getByText('0.895')).toBeInTheDocument()
    })
  })

  it('renders Critical Issues KPI card', async () => {
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Critical Issues')).toBeInTheDocument()
      // critical_issues: 3
      expect(screen.getByText('3')).toBeInTheDocument()
    })
  })

  it('renders Precision metric', async () => {
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Precision')).toBeInTheDocument()
    })
  })

  it('renders Recall metric', async () => {
    render(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Recall')).toBeInTheDocument()
    })
  })
})
