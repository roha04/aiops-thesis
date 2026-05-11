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
    expect(screen.getByText('🔮 Прогноз')).toBeInTheDocument()
  })

  it('renders the Pipeline ID input pre-filled', () => {
    render(<Predictor />)
    const input = screen.getByPlaceholderText('напр., jenkins-build-123')
    expect(input).toBeInTheDocument()
    expect(input.value).toBe('jenkins-build-123')
  })

  it('renders the logs textarea with default value', () => {
    render(<Predictor />)
    const textarea = screen.getByPlaceholderText('Вставте логи сюди...')
    expect(textarea).toBeInTheDocument()
    expect(textarea.value).toBe('ERROR: Database connection timeout')
  })

  it('renders the Predict button', () => {
    render(<Predictor />)
    expect(screen.getByRole('button', { name: /прогнозувати|аналіз/i })).toBeInTheDocument()
  })

  it('Predict button is enabled when pipeline id and logs are provided', () => {
    render(<Predictor />)
    const btn = screen.getByRole('button', { name: /прогнозувати|аналіз/i })
    expect(btn).not.toBeDisabled()
  })

  it('Predict button is disabled when pipeline id is empty', async () => {
    render(<Predictor />)
    const input = screen.getByPlaceholderText('напр., jenkins-build-123')
    await userEvent.clear(input)
    const btn = screen.getByRole('button', { name: /прогнозувати|аналіз/i })
    expect(btn).toBeDisabled()
  })

  it('Predict button is disabled when logs are empty', async () => {
    render(<Predictor />)
    const textarea = screen.getByPlaceholderText('Вставте логи сюди...')
    await userEvent.clear(textarea)
    const btn = screen.getByRole('button', { name: /прогнозувати|аналіз/i })
    expect(btn).toBeDisabled()
  })
})

describe('Predictor – user interaction', () => {
  it('updates pipeline ID input value on change', async () => {
    render(<Predictor />)
    const input = screen.getByPlaceholderText('напр., jenkins-build-123')
    await userEvent.clear(input)
    await userEvent.type(input, 'my-new-pipeline')
    expect(input.value).toBe('my-new-pipeline')
  })

  it('updates logs textarea value on change', async () => {
    render(<Predictor />)
    const textarea = screen.getByPlaceholderText('Вставте логи сюди...')
    await userEvent.clear(textarea)
    await userEvent.type(textarea, 'Build started successfully')
    expect(textarea.value).toBe('Build started successfully')
  })
})

describe('Predictor – API call and result rendering', () => {
  it('shows loading state while request is in flight', async () => {
    render(<Predictor />)
    const btn = screen.getByRole('button', { name: /прогнозувати|аналіз/i })
    fireEvent.click(btn)
    // Immediately after click the button text changes to "⏳ Аналіз..."
    expect(btn).toHaveTextContent('⏳ Аналіз...')
  })

  it('displays the Ukrainian risk-level label after a successful response', async () => {
    render(<Predictor />)
    fireEvent.click(screen.getByRole('button', { name: /прогнозувати|аналіз/i }))

    // MSW returns PREDICTION_RESULT with risk_level "HIGH" → "ВИСОКИЙ РИЗИК"
    await waitFor(() => {
      expect(screen.getByText(/ВИСОКИЙ РИЗИК/)).toBeInTheDocument()
    })
  })

  it('displays the recommendation message after response', async () => {
    render(<Predictor />)
    fireEvent.click(screen.getByRole('button', { name: /прогнозувати|аналіз/i }))

    await waitFor(() => {
      expect(screen.getByText(/КРИТИЧНО/)).toBeInTheDocument()
    })
  })
})

describe('Predictor – Drain parsed-log card', () => {
  it('renders the parsed-log card after a prediction', async () => {
    render(<Predictor />)
    fireEvent.click(screen.getByRole('button', { name: /прогнозувати|аналіз/i }))

    await waitFor(() => {
      expect(screen.getByTestId('parsed-log-card')).toBeInTheDocument()
    })
  })

  it('shows the Drain event template and id from the response', async () => {
    render(<Predictor />)
    fireEvent.click(screen.getByRole('button', { name: /прогнозувати|аналіз/i }))

    await waitFor(() => {
      const tmpl = screen.getByTestId('parsed-template')
      expect(tmpl).toHaveTextContent('Database connection timeout')
      expect(tmpl).toHaveTextContent('<*>')
      expect(screen.getByTestId('parsed-event-id')).toHaveTextContent('E00007')
    })
  })

  it('shows the extracted log level and service', async () => {
    render(<Predictor />)
    fireEvent.click(screen.getByRole('button', { name: /прогнозувати|аналіз/i }))

    await waitFor(() => {
      expect(screen.getByTestId('parsed-level')).toHaveTextContent('ERROR')
      expect(screen.getByTestId('parsed-service')).toHaveTextContent('db-worker')
    })
  })

  it('renders extracted parameters as chips', async () => {
    render(<Predictor />)
    fireEvent.click(screen.getByRole('button', { name: /прогнозувати|аналіз/i }))

    await waitFor(() => {
      const params = screen.getByTestId('parsed-parameters')
      expect(params).toBeInTheDocument()
      expect(params).toHaveTextContent('30s')
    })
  })
})
