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

  // PositionRow column order (PositionRow.tsx:57-76): ticker, quantity,
  // avg_cost, current_price, pnl, pct. Scope to the second <td> (qty cell).
  //
  // Capture post-buy JPM qty so the post-sell assertion can be a relative
  // delta rather than an absolute `1`. Robust to any prior state on JPM.
  const jpmRow = positionsTable.getByRole('button', { name: 'Select JPM' });
  const jpmQty = jpmRow.locator('td').nth(1);
  const postBuyQtyText = await jpmQty.innerText();
  const postBuyQty = parseFloat(postBuyQtyText.trim());

  // Sell 1. TradeBar clears its inputs onSuccess (verified TradeBar.tsx:48-49)
  // so we explicitly re-fill rather than relying on residual state.
  await page.getByLabel('Ticker').fill('JPM');
  await page.getByLabel('Quantity').fill('1');
  await page.getByRole('button', { name: 'Sell' }).click();

  // Post-sell qty == post-buy qty - 1 (we sold 1 of the 2 we bought).
  // Use a generous timeout for the React Query refetch + render after sell.
  await expect
    .poll(
      async () => parseFloat((await jpmQty.innerText()).trim()),
      { timeout: 10_000 },
    )
    .toBe(postBuyQty - 1);
});
