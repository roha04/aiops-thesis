// @ts-check
import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for E2E tests.
 *
 * Tests assume the frontend dev-server is running on http://localhost:5173
 * and the backend is on http://localhost:8000.
 *
 * Start both servers before running:
 *   cd backend && uvicorn main:app --reload
 *   cd frontend && npm run dev
 * Then run:
 *   npx playwright test
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { outputFolder: 'playwright-report' }], ['list']],

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],

  // Optionally auto-start the dev server for CI
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:5173',
  //   reuseExistingServer: !process.env.CI,
  // },
})
