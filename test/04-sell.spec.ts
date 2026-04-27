// PLAN.md §12 row 4 — sell shares: position quantity drops after partial sell.
// Buys JPM × 2, sells JPM × 1, asserts the JPM row's full text contains "1"
// (the round-trip leaves a half-position).
//
// Plan refs: 10-03 Task 2; CONTEXT.md D-08 (JPM isolation); RESEARCH.md
// §04-sell (qty regex tolerates "1", "1.0", "1.00" formatting variants).

import { test, expect } from '@playwright/test';

test('sell JPM 1 after buying 2: position quantity drops to 1', async ({ page }) => {
  await page.goto('/');

  // Buy 2 — proves the buy fully processed (position row appears) before
  // the sell fires; avoids racing the second mutation against the first
  // React Query invalidation.
  await page.getByLabel('Ticker').fill('JPM');
  await page.getByLabel('Quantity').fill('2');
  await page.getByRole('button', { name: 'Buy' }).click();
  await expect(
    page.getByRole('button', { name: 'Select JPM' }),
  ).toBeVisible({ timeout: 10_000 });

  // Sell 1. TradeBar clears its inputs onSuccess (verified TradeBar.tsx:48-49)
  // so we explicitly re-fill rather than relying on residual state.
  await page.getByLabel('Ticker').fill('JPM');
  await page.getByLabel('Quantity').fill('1');
  await page.getByRole('button', { name: 'Sell' }).click();

  // The JPM row's full <tr> text contains the qty cell. Regex tolerates
  // PositionRow rendering qty as "1", "1.0", or "1.00" — Phase 7
  // implementation uses {position.quantity} (raw number) but defensive
  // formatting variants are matched too.
  const jpmRow = page.getByRole('button', { name: 'Select JPM' });
  await expect(jpmRow).toContainText(/\bJPM\b.*\b1(?:\.0+)?\b/, {
    timeout: 10_000,
  });
});
