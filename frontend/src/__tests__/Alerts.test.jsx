/**
 * Unit tests for the Alerts page.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Alerts from '../pages/Alerts'

describe('Alerts – page rendering', () => {
  it('shows loading spinner initially', () => {
    render(<Alerts />)
    expect(screen.getByText(/loading alerts/i)).toBeInTheDocument()
  })

  it('renders the page heading after data loads', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('🚨 Recent Alerts')).toBeInTheDocument()
    })
  })

  it('renders the alerts table headers', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('Timestamp')).toBeInTheDocument()
      expect(screen.getByText('Pipeline')).toBeInTheDocument()
      expect(screen.getByText('Severity')).toBeInTheDocument()
      expect(screen.getByText('Message')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
    })
  })
})

describe('Alerts – data display', () => {
  it('renders pipeline ids from mock data', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('jenkins-deploy')).toBeInTheDocument()
    })
  })

  it('renders CRITICAL severity badge', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('CRITICAL')).toBeInTheDocument()
    })
  })

  it('renders WARNING severity badge', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('WARNING')).toBeInTheDocument()
    })
  })

  it('shows resolved status correctly', async () => {
    render(<Alerts />)
    await waitFor(() => {
      // One alert is resolved = should show "Resolved"
      expect(screen.getByText('Resolved')).toBeInTheDocument()
    })
  })

  it('shows open status for unresolved alert', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('Open')).toBeInTheDocument()
    })
  })

  it('renders alert message text', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('Database connection timeout')).toBeInTheDocument()
    })
  })
})
