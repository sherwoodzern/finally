// PLAN.md §12 row 4 — sell shares: position quantity drops after partial sell.
// Buys JPM × 2, sells JPM × 1, asserts the JPM row's full text contains "1"
// (the round-trip leaves a half-position).
//
// Plan refs: 10-03 Task 2; CONTEXT.md D-08 (JPM isolation); RESEARCH.md
// §04-sell (qty regex tolerates "1", "1.0", "1.00" formatting variants).

import { test, expect } from '@playwright/test';

test('sell JPM 1 after buying 2: position quantity drops to 1', async ({ page }) => {
  await page.goto('/');

  // JPM is also in the default watchlist seed (same aria-label="Select JPM"
  // on the watchlist row), so scope all position-row lookups to
  // data-testid="positions-table" (Plan 10-00). Avoids strict-mode violation
  // and isolates assertions to the positions table.
  const positionsTable = page.getByTestId('positions-table');

  // Buy 2 — proves the buy fully processed (position row appears) before
  // the sell fires; avoids racing the second mutation against the first
  // React Query invalidation.
  await page.getByLabel('Ticker').fill('JPM');
  await page.getByLabel('Quantity').fill('2');
  await page.getByRole('button', { name: 'Buy' }).click();
  await expect(
    positionsTable.getByRole('button', { name: 'Select JPM' }),
  ).toBeVisible({ timeout: 10_000 });

  // Sell 1. TradeBar clears its inputs onSuccess (verified TradeBar.tsx:48-49)
  // so we explicitly re-fill rather than relying on residual state.
  await page.getByLabel('Ticker').fill('JPM');
  await page.getByLabel('Quantity').fill('1');
  await page.getByRole('button', { name: 'Sell' }).click();

  // PositionRow column order (PositionRow.tsx:57-76): ticker, quantity,
  // avg_cost, current_price, pnl, pct. Scope the assertion to the second
  // <td> (qty cell) so the \b1\b regex works — against the full row text
  // "JPM1$195.02..." the leading \b boundary fails (M and 1 are both
  // word chars). Regex tolerates "1", "1.0", "1.00" rendering variants.
  const jpmRow = positionsTable.getByRole('button', { name: 'Select JPM' });
  const jpmQty = jpmRow.locator('td').nth(1);
  await expect(jpmQty).toHaveText(/^\s*1(?:\.0+)?\s*$/, { timeout: 10_000 });
});
