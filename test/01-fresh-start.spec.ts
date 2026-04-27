// test/01-fresh-start.spec.ts
// PLAN.md §12 row 1 — fresh start: default watchlist + $10k cash + streaming prices.
// Selectors: aria-label per WatchlistRow.tsx, header-cash testid per Header.tsx (Plan 10-00).
// Streaming proof: each row renders '—' (em-dash) until first SSE tick lands.

import { test, expect } from '@playwright/test';

const SEED_TICKERS = [
  'AAPL',
  'GOOGL',
  'MSFT',
  'AMZN',
  'TSLA',
  'NVDA',
  'META',
  'JPM',
  'V',
  'NFLX',
] as const;

test('fresh start: default watchlist + $10k cash + streaming prices', async ({ page }) => {
  await page.goto('/');

  // 1. All 10 default-seed tickers render as watchlist rows.
  for (const ticker of SEED_TICKERS) {
    await expect(
      page.getByRole('button', { name: `Select ${ticker}` }),
    ).toBeVisible({ timeout: 10_000 });
  }

  // 2. Header cash reads $10,000.00 (Plan 10-00 testid).
  await expect(page.getByTestId('header-cash')).toHaveText('$10,000.00');

  // 3. At least one watchlist row leaves the '—' placeholder within 10s,
  //    proving the SSE stream is live.
  const aaplRow = page.getByRole('button', { name: 'Select AAPL' });
  await expect(aaplRow).not.toContainText('—', { timeout: 10_000 });
});
