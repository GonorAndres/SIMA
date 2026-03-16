import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E config for SIMA.
 *
 * Usage:
 *   npx playwright test                          # all tests, all browsers
 *   npx playwright test --project=chromium        # chromium only
 *   npx playwright test e2e/premium-calculator    # single file
 *   npx playwright test --update-snapshots        # create/update visual baselines
 *
 * CI: override baseURL via environment variable:
 *   BASE_URL=http://localhost:8080 npx playwright test
 */
export default defineConfig({
  testDir: './e2e',

  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
      threshold: 0.2,
      animations: 'disabled',
    },
  },

  fullyParallel: true,
  workers: 2,
  retries: 1,

  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results/e2e-results.json' }],
  ],

  outputDir: 'test-results',

  use: {
    baseURL: process.env.BASE_URL || 'https://sima-d3qj5vwxtq-uc.a.run.app',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    navigationTimeout: 30000,
    actionTimeout: 20000,
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile', use: { ...devices['iPhone 14'] } },
  ],
});
