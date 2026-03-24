/**
 * Unit tests for the Predictor page.
 *
 * Axios calls are intercepted by MSW (configured in src/test/setup.js).
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Predictor from '../pages/Predictor'

describe('Predictor – form rendering', () => {
  it('renders the page heading', () => {
    render(<Predictor />)
    expect(screen.getByText('🔮 Predictor')).toBeInTheDocument()
  })

  it('renders the Pipeline ID input pre-filled', () => {
    render(<Predictor />)
    const input = screen.getByPlaceholderText('e.g., jenkins-build-123')
    expect(input).toBeInTheDocument()
    expect(input.value).toBe('jenkins-build-123')
  })

  it('renders the logs textarea with default value', () => {
    render(<Predictor />)
    const textarea = screen.getByPlaceholderText('Paste log output here...')
    expect(textarea).toBeInTheDocument()
    expect(textarea.value).toBe('ERROR: Database connection timeout')
  })

  it('renders the Predict button', () => {
    render(<Predictor />)
    expect(screen.getByRole('button', { name: /predict/i })).toBeInTheDocument()
  })

  it('Predict button is enabled when pipeline id and logs are provided', () => {
    render(<Predictor />)
    const btn = screen.getByRole('button', { name: /predict/i })
    expect(btn).not.toBeDisabled()
  })

  it('Predict button is disabled when pipeline id is empty', async () => {
    render(<Predictor />)
    const input = screen.getByPlaceholderText('e.g., jenkins-build-123')
    await userEvent.clear(input)
    const btn = screen.getByRole('button', { name: /predict/i })
    expect(btn).toBeDisabled()
  })

  it('Predict button is disabled when logs are empty', async () => {
    render(<Predictor />)
    const textarea = screen.getByPlaceholderText('Paste log output here...')
    await userEvent.clear(textarea)
    const btn = screen.getByRole('button', { name: /predict/i })
    expect(btn).toBeDisabled()
  })
})

describe('Predictor – user interaction', () => {
  it('updates pipeline ID input value on change', async () => {
    render(<Predictor />)
    const input = screen.getByPlaceholderText('e.g., jenkins-build-123')
    await userEvent.clear(input)
    await userEvent.type(input, 'my-new-pipeline')
    expect(input.value).toBe('my-new-pipeline')
  })

  it('updates logs textarea value on change', async () => {
    render(<Predictor />)
    const textarea = screen.getByPlaceholderText('Paste log output here...')
    await userEvent.clear(textarea)
    await userEvent.type(textarea, 'Build started successfully')
    expect(textarea.value).toBe('Build started successfully')
  })
})

describe('Predictor – API call and result rendering', () => {
  it('shows loading state while request is in flight', async () => {
    render(<Predictor />)
    const btn = screen.getByRole('button', { name: /predict/i })
    fireEvent.click(btn)
    // Immediately after click the button text changes to ⏳ Analyzing...
    expect(btn).toHaveTextContent('⏳ Analyzing...')
  })

  it('displays prediction risk level after successful response', async () => {
    render(<Predictor />)
    fireEvent.click(screen.getByRole('button', { name: /predict/i }))

    // MSW returns PREDICTION_RESULT with risk_level "HIGH"
    await waitFor(() => {
      expect(screen.getByText(/HIGH/i)).toBeInTheDocument()
    })
  })

  it('displays the recommendation message after response', async () => {
    render(<Predictor />)
    fireEvent.click(screen.getByRole('button', { name: /predict/i }))

    await waitFor(() => {
      expect(screen.getByText(/CRITICAL/i)).toBeInTheDocument()
    })
  })
})
