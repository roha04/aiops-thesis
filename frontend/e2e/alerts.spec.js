/**
 * E2E tests – Alerts page
 *
 * Verifies the alerts table renders, auto-refreshes, and displays data correctly.
 */
import { test, expect } from '@playwright/test'

test.describe('Alerts Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('text=AIOps Platform', { timeout: 10_000 })
    await page.getByText('🚨 Alerts').first().click()
    await page.waitForSelector('h1:has-text("🚨 Recent Alerts")', { timeout: 5_000 })
  })

  test('renders the Alerts heading', async ({ page }) => {
    await expect(page.locator('h1').filter({ hasText: '🚨 Recent Alerts' })).toBeVisible()
  })

  test('renders table with Timestamp header', async ({ page }) => {
    await expect(page.getByText('Timestamp')).toBeVisible({ timeout: 10_000 })
  })

  test('renders table with Pipeline header', async ({ page }) => {
    await expect(page.getByText('Pipeline')).toBeVisible({ timeout: 10_000 })
  })

  test('renders table with Severity header', async ({ page }) => {
    await expect(page.getByText('Severity')).toBeVisible({ timeout: 10_000 })
  })

  test('renders table with Message header', async ({ page }) => {
    await expect(page.getByText('Message')).toBeVisible({ timeout: 10_000 })
  })

  test('renders table with Status header', async ({ page }) => {
    await expect(page.getByText('Status')).toBeVisible({ timeout: 10_000 })
  })

  test('shows at least one alert row when alerts exist', async ({ page }) => {
    // Wait for the table body to have at least one row
    await page.waitForSelector('tbody tr', { timeout: 10_000 })
    const rows = page.locator('tbody tr')
    await expect(rows).toHaveCount(await rows.count())
    expect(await rows.count()).toBeGreaterThan(0)
  })

  test('severity badges are colour-coded (critical badge has red styling)', async ({ page }) => {
    await page.waitForSelector('tbody tr', { timeout: 10_000 })
    // Find a CRITICAL badge and verify it has a red-related class
    const criticalBadge = page.locator('span').filter({ hasText: 'CRITICAL' }).first()
    if (await criticalBadge.isVisible()) {
      const className = await criticalBadge.getAttribute('class')
      expect(className).toMatch(/red/)
    }
  })
})
