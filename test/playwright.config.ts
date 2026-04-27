// test/playwright.config.ts
// CONTEXT.md: D-02 (full browser matrix), D-07 (workers / parallelism),
// D-09 (testDir, baseURL, retries, reporter).

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // D-09: specs colocated with this config under test/
  testDir: '.',
  testMatch: /\d{2}-.+\.spec\.ts$/,

  // D-09: retries 0 locally / 1 in CI. The compose file sets CI=1 always,
  // so the suite gets one transparent retry to absorb SSE-reconnect-test
  // flakiness without masking real bugs (D-09 wording).
  retries: process.env.CI ? 1 : 0,

  // D-07: "workers: 1 within a Playwright project; cross-browser projects parallel".
  // Playwright DOES NOT support per-project worker caps. The intent is achieved
  // with workers = (number of projects) + fullyParallel: false:
  //   - workers: 3  -> three concurrent worker processes
  //   - fullyParallel: false (default) -> tests in a single file run serially
  //     within one worker; each worker picks up one whole spec file at a time
  //   - 7 specs x 3 projects = 21 (file, project) tasks distributed greedily
  //     across the 3 workers; D-08's per-spec unique tickers prevent any
  //     cross-spec collision regardless of which browser picks them up first.
  workers: 3,
  fullyParallel: false,

  // Forbid `test.only` from sneaking into a green-bar commit.
  forbidOnly: !!process.env.CI,

  // D-09: list reporter to compose stdout + html report under test/playwright-report/
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
  ],

  use: {
    // D-09: compose-internal DNS - the playwright container reaches the app
    // service by service name. Env override available for ad-hoc local runs.
    baseURL: process.env.BASE_URL ?? 'http://app:8000',

    // Trace on first retry only (cheap on green, full evidence on red).
    trace: 'on-first-retry',

    // Capture screenshot only on failure.
    screenshot: 'only-on-failure',

    // Capture video only on failure.
    video: 'retain-on-failure',

    // Suite-wide action timeout. Default Playwright is no per-action timeout
    // (it relies on per-test timeout). Setting 10s catches misclicks early.
    actionTimeout: 10_000,
  },

  // Per-test budget. SSE-related specs may need to wait for retry: 1000 + a
  // tick; 30s is generous.
  timeout: 30_000,

  // Where to write JUnit-style results, traces, etc.
  outputDir: 'test-results',

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit',   use: { ...devices['Desktop Safari'] } },
  ],
});
