/**
 * Unit tests for the Alerts page.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Alerts from '../pages/Alerts'

describe('Alerts – page rendering', () => {
  it('shows loading spinner initially', () => {
    render(<Alerts />)
    expect(screen.getByText(/завантаження сповіщень/i)).toBeInTheDocument()
  })

  it('renders the page heading after data loads', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('🚨 Останні сповіщення')).toBeInTheDocument()
    })
  })

  it('renders the alerts table headers', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('Час')).toBeInTheDocument()
      expect(screen.getByText('Пайплайн')).toBeInTheDocument()
      expect(screen.getByText('Важливість')).toBeInTheDocument()
      expect(screen.getByText('Повідомлення')).toBeInTheDocument()
      expect(screen.getByText('Статус')).toBeInTheDocument()
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

  it('renders CRITICAL severity badge in Ukrainian', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('КРИТИЧНО')).toBeInTheDocument()
    })
  })

  it('renders WARNING severity badge in Ukrainian', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('УВАГА')).toBeInTheDocument()
    })
  })

  it('shows resolved status correctly', async () => {
    render(<Alerts />)
    await waitFor(() => {
      // One alert is resolved → should show "Вирішено"
      expect(screen.getByText('Вирішено')).toBeInTheDocument()
    })
  })

  it('shows open status for unresolved alert', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('Відкрите')).toBeInTheDocument()
    })
  })

  it('renders alert message text', async () => {
    render(<Alerts />)
    await waitFor(() => {
      expect(screen.getByText('Тайм-аут підключення до бази даних')).toBeInTheDocument()
    })
  })
})
