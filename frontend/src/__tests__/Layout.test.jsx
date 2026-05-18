/**
 * Unit tests for the Layout component.
 *
 * Run: npm test  (from frontend/)
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Layout from '../components/Layout'

function renderLayout(overrides = {}) {
  const props = {
    page: 'dashboard',
    setPage: vi.fn(),
    backendOnline: true,
    children: <div data-testid="page-content">Page Content</div>,
    ...overrides,
  }
  return { ...render(<Layout {...props} />), setPage: props.setPage }
}

describe('Layout – sidebar navigation', () => {
  it('renders children inside the main area', () => {
    renderLayout()
    expect(screen.getByTestId('page-content')).toBeInTheDocument()
  })

  it('renders all six navigation menu items', () => {
    renderLayout()
    expect(screen.getByText('📊 Панель')).toBeInTheDocument()
    expect(screen.getByText('🔮 Прогноз')).toBeInTheDocument()
    expect(screen.getByText('📈 Аналітика')).toBeInTheDocument()
    expect(screen.getByText('📚 Історія')).toBeInTheDocument()
    expect(screen.getByText('🚨 Сповіщення')).toBeInTheDocument()
    expect(screen.getByText('🔧 Jenkins')).toBeInTheDocument()
  })

  it('calls setPage with the correct id when a menu item is clicked', () => {
    const { setPage } = renderLayout()
    fireEvent.click(screen.getByText('🔮 Прогноз'))
    expect(setPage).toHaveBeenCalledWith('predictor')
  })

  it('highlights the currently active menu item', () => {
    renderLayout({ page: 'alerts' })
    const alertsBtn = screen.getByText('🚨 Сповіщення').closest('button')
    expect(alertsBtn).toHaveClass('bg-blue-600')
  })

  it('shows "Онлайн" when backend is online', () => {
    renderLayout({ backendOnline: true })
    expect(screen.getByText('Онлайн')).toBeInTheDocument()
  })

  it('shows "Офлайн" when backend is offline', () => {
    renderLayout({ backendOnline: false })
    expect(screen.getByText('Офлайн')).toBeInTheDocument()
  })

  it('toggles sidebar open/closed on menu button click', () => {
    renderLayout()
    // Initially open – AIOps heading visible
    expect(screen.getByText('🤖 AIOps')).toBeInTheDocument()

    // Click the collapse button
    const toggleBtn = screen.getByRole('button', { name: '' })  // X icon button
    fireEvent.click(toggleBtn)

    // Heading should disappear when sidebar is collapsed
    expect(screen.queryByText('🤖 AIOps')).not.toBeInTheDocument()
  })
})
