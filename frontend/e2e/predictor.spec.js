/**
 * E2E tests – Predictor page
 *
 * Tests the full pipeline prediction form: fill inputs → submit → see result.
 */
import { test, expect } from '@playwright/test'

test.describe('Predictor Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('text=AIOps Platform', { timeout: 10_000 })
    await page.getByText('🔮 Predictor').first().click()
    await page.waitForSelector('h1:has-text("🔮 Predictor")', { timeout: 5_000 })
  })

  test('renders the Predictor heading', async ({ page }) => {
    await expect(page.locator('h1').filter({ hasText: '🔮 Predictor' })).toBeVisible()
  })

  test('pipeline ID input is pre-filled', async ({ page }) => {
    await expect(page.getByPlaceholder('e.g., jenkins-build-123')).toHaveValue('jenkins-build-123')
  })

  test('logs textarea is pre-filled', async ({ page }) => {
    await expect(page.getByPlaceholder('Paste log output here...')).toHaveValue(
      'ERROR: Database connection timeout'
    )
  })

  test('Predict button is visible and enabled', async ({ page }) => {
    const btn = page.getByRole('button', { name: /predict/i })
    await expect(btn).toBeVisible()
    await expect(btn).toBeEnabled()
  })

  test('typing in pipeline ID updates its value', async ({ page }) => {
    const input = page.getByPlaceholder('e.g., jenkins-build-123')
    await input.fill('my-custom-pipeline')
    await expect(input).toHaveValue('my-custom-pipeline')
  })

  test('typing in logs textarea updates its value', async ({ page }) => {
    const textarea = page.getByPlaceholder('Paste log output here...')
    await textarea.fill('INFO: all systems nominal')
    await expect(textarea).toHaveValue('INFO: all systems nominal')
  })

  test('Predict button is disabled when pipeline ID is cleared', async ({ page }) => {
    await page.getByPlaceholder('e.g., jenkins-build-123').fill('')
    const btn = page.getByRole('button', { name: /predict/i })
    await expect(btn).toBeDisabled()
  })

  test('clicking Predict shows loading state', async ({ page }) => {
    await page.getByRole('button', { name: /predict/i }).click()
    // Immediately after click the text changes to analyzing
    await expect(page.getByRole('button', { name: /analyzing/i })).toBeVisible()
  })

  test('after prediction result shows a risk level badge', async ({ page }) => {
    await page.getByRole('button', { name: /predict/i }).click()
    // Wait for result – risk level should be LOW / MEDIUM / HIGH
    await expect(
      page.locator('text=/LOW|MEDIUM|HIGH/').first()
    ).toBeVisible({ timeout: 15_000 })
  })

  test('after prediction a recommendation message appears', async ({ page }) => {
    await page.getByRole('button', { name: /predict/i }).click()
    // The response message contains OK / WARNING / CRITICAL
    await expect(
      page.locator('text=/system appears healthy|Monitor closely|Check logs/i').first()
    ).toBeVisible({ timeout: 15_000 })
  })
})
