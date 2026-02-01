/* global process */
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
  ],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
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
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Mobile/tablet projects — used only by responsive suite
    {
      name: 'mobile',
      use: { ...devices['Pixel 5'] },
      testMatch: /12-responsive/,
    },
    {
      name: 'iphone',
      use: { ...devices['iPhone 12'] },
      testMatch: /12-responsive/,
    },
    {
      name: 'ipad',
      use: { ...devices['iPad Pro 11'] },
      testMatch: /12-responsive/,
    },
  ],
  webServer: {
    command: 'cd ../.. && ./scripts/dev.sh',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
})
