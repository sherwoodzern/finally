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

  // D-07 (corrected): A single worker process serialises ALL 21 (spec,
  // project) pairs across the 3 browser projects, eliminating cross-spec
  // contention on shared SQLite state (cash_balance, default seed-watchlist
  // positions). Cross-browser projects are still defined as separate
  // Playwright projects below; with workers: 1 they run sequentially within
  // the same `up` invocation rather than in parallel. Original config used
  // workers: 3 + fullyParallel: false in an attempt to realise D-07's
  // "workers: 1 within a Playwright project; cross-browser projects parallel"
  // wording, but Playwright does not support per-project worker caps and
  // the result was three concurrent workers picking up different spec files
  // against the same backend (8 of 9 failures in 10-VERIFICATION.md Gap
  // Group A). Single-worker serialisation is the simplest fix and is the
  // right answer for a single-user demo project — the runtime cost (a few
  // extra seconds end-to-end) is irrelevant; reproducible green is.
  workers: 1,
  fullyParallel: false,

  // Forbid `test.only` from sneaking into a green-bar commit.
  forbidOnly: !!process.env.CI,

  // D-09: list reporter to compose stdout + html report under test/playwright-report/
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
  ],

  use: {
    // D-09 (override): compose-internal DNS - the playwright container reaches
    // the appsvc service by service name. Env override available for ad-hoc
    // local runs. Service is `appsvc` not `app` to avoid Chrome/Firefox HSTS
    // preload upgrade on the `.app` TLD (see docker-compose.test.yml header).
    baseURL: process.env.BASE_URL ?? 'http://appsvc:8000',

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
