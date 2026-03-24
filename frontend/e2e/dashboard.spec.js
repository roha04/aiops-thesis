/**
 * E2E tests – Dashboard page
 *
 * Verifies that KPI cards and charts load correctly when the backend is reachable.
 */
import { test, expect } from '@playwright/test'

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Ensure we're on the dashboard (it's the default)
    await page.waitForSelector('h1:has-text("AIOps Platform")', { timeout: 10_000 })
  })

  test('shows the Dashboard heading', async ({ page }) => {
    // The page-level heading
    await expect(
      page.locator('.space-y-6 h1, main h1').filter({ hasText: '📊 Dashboard' })
    ).toBeVisible({ timeout: 15_000 })
  })

  test('renders Total Alerts KPI card label', async ({ page }) => {
    await expect(page.getByText('Total Alerts (7d)')).toBeVisible({ timeout: 15_000 })
  })

  test('renders Model Accuracy KPI card label', async ({ page }) => {
    await expect(page.getByText('Model Accuracy')).toBeVisible({ timeout: 15_000 })
  })

  test('renders F1 Score KPI card label', async ({ page }) => {
    await expect(page.getByText('F1 Score')).toBeVisible({ timeout: 15_000 })
  })

  test('renders Critical Issues KPI card label', async ({ page }) => {
    await expect(page.getByText('Critical Issues')).toBeVisible({ timeout: 15_000 })
  })

  test('model accuracy shows a percentage value', async ({ page }) => {
    await page.waitForSelector('text=Model Accuracy', { timeout: 15_000 })
    // Find the accuracy value – should contain a % sign
    const accuracyEl = page.locator('text=Model Accuracy').locator('..').locator('p').last()
    await expect(accuracyEl).toContainText('%')
  })

  test('page auto-refreshes without full reload (data stays present)', async ({ page }) => {
    await page.waitForSelector('text=Total Alerts (7d)', { timeout: 15_000 })
    // Wait 11 s (auto-refresh fires at 10 s) and verify headings still present
    await page.waitForTimeout(11_000)
    await expect(page.getByText('Total Alerts (7d)')).toBeVisible()
  })
})
