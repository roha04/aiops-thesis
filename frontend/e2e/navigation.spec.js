/**
 * E2E tests – Navigation & Layout
 *
 * Verifies sidebar navigation links and layout elements across the app.
 * Requires both backend (port 8000) and frontend dev-server (port 5173) running.
 */
import { test, expect } from '@playwright/test'

test.describe('Navigation and Layout', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Wait for the layout to be rendered
    await page.waitForSelector('text=AIOps Platform', { timeout: 10_000 })
  })

  test('page title is AIOps Platform', async ({ page }) => {
    await expect(page.locator('h1').first()).toContainText('AIOps Platform')
  })

  test('sidebar renders all six navigation items', async ({ page }) => {
    const navLabels = [
      '📊 Dashboard',
      '🔮 Predictor',
      '📈 Analytics',
      '📚 History',
      '🚨 Alerts',
      '🔧 Jenkins',
    ]
    for (const label of navLabels) {
      await expect(page.getByText(label).first()).toBeVisible()
    }
  })

  test('Dashboard is the default active page', async ({ page }) => {
    // The Dashboard nav item should have active class
    const dashBtn = page.getByText('📊 Dashboard').first()
    await expect(dashBtn).toBeVisible()
    // The page heading appears inside the content area
    await expect(page.locator('h1').filter({ hasText: '📊 Dashboard' })).toBeVisible()
  })

  test('clicking Predictor nav item switches to Predictor page', async ({ page }) => {
    await page.getByText('🔮 Predictor').first().click()
    await expect(page.locator('h1').filter({ hasText: '🔮 Predictor' })).toBeVisible()
  })

  test('clicking Alerts nav item switches to Alerts page', async ({ page }) => {
    await page.getByText('🚨 Alerts').first().click()
    await expect(page.locator('h1').filter({ hasText: '🚨 Recent Alerts' })).toBeVisible()
  })

  test('clicking Analytics nav item switches to Analytics page', async ({ page }) => {
    await page.getByText('📈 Analytics').first().click()
    await expect(page.locator('h1').filter({ hasText: '📈' })).toBeVisible()
  })

  test('can collapse and expand the sidebar', async ({ page }) => {
    // AIOps text visible while open
    await expect(page.getByText('🤖 AIOps')).toBeVisible()

    // Find the toggle button (contains X icon when open) and click it
    const toggleBtn = page.locator('nav').locator('..').locator('button').first()
    await toggleBtn.click()

    // After collapse the AIOps text should be hidden
    await expect(page.getByText('🤖 AIOps')).not.toBeVisible()

    // Click again to expand
    await toggleBtn.click()
    await expect(page.getByText('🤖 AIOps')).toBeVisible()
  })

  test('backend status indicator is visible in the header', async ({ page }) => {
    const statusEl = page.locator('header').locator('text=/Online|Offline/')
    await expect(statusEl).toBeVisible()
  })
})
