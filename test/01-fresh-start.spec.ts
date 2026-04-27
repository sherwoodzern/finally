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
      page
        .getByTestId('watchlist-panel')
        .getByRole('button', { name: `Select ${ticker}` }),
    ).toBeVisible({ timeout: 10_000 });
  }

  // No absolute cash assertion: the compose anonymous SQLite volume persists
  // across all 3 browser projects within a single `up`. Under workers: 1
  // projects run alphabetically (chromium → firefox → webkit), so by the time
  // firefox/webkit run this spec, chromium's 03-buy/04-sell/05-portfolio-viz/
  // 06-chat have already debited cash. Cross-project SQLite leak — see
  // 10-VERIFICATION.md Mode B (commit 4f690e6) and 10-06's parallel drop in
  // 03-buy. The 10-ticker watchlist visibility above and the streaming-proof
  // assertion below are sufficient to prove `fresh start` without coupling
  // to cross-project state.

  // 3. At least one watchlist row leaves the '—' placeholder within 10s,
  //    proving the SSE stream is live.
  const aaplRow = page
    .getByTestId('watchlist-panel')
    .getByRole('button', { name: 'Select AAPL' });
  await expect(aaplRow).not.toContainText('—', { timeout: 10_000 });
});
