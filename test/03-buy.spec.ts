// PLAN.md §12 row 3 — buy shares: cash decreases, position appears.
// Drives the production TradeBar UI through POST /api/portfolio/trade and
// observes the rendered positions table + header cash span.
//
// Plan refs: 10-03 Task 1; CONTEXT.md D-08 (NVDA isolation); RESEARCH.md
// Pitfall 1 (relative cash assertion — simulator price moves).

import { test, expect } from '@playwright/test';

test('buy NVDA 1: cash decreases, position appears', async ({ page }) => {
  await page.goto('/');

  // Pre-trade sanity: page loaded with full starting cash. Guards against a
  // dirty (re-used) volume — D-06 says compose creates a fresh volume per up,
  // but this assertion fails loudly if that ever regresses.
  await expect(page.getByText('$10,000.00')).toBeVisible();

  // TradeBar uses <label>Ticker</label> wrapping <input>; getByLabel resolves
  // through the accessibility tree (PATTERNS.md selector hierarchy rule 2).
  await page.getByLabel('Ticker').fill('NVDA');
  await page.getByLabel('Quantity').fill('1');
  await page.getByRole('button', { name: 'Buy' }).click();

  // PositionRow renders <tr role="button" aria-label="Select NVDA">. The
  // 10s timeout absorbs the trade roundtrip + React Query refetch + render
  // (cold cache 1-3s, WebKit slower).
  await expect(
    page.getByRole('button', { name: 'Select NVDA' }),
  ).toBeVisible({ timeout: 10_000 });

  // Cash strictly less than $10,000 — RELATIVE assertion. Simulator price
  // moves; hard-coding an exact value flakes (RESEARCH.md Pitfall 1).
  // Plan 10-00 shipped data-testid="header-cash" on the cash <span>.
  const cashText = await page.getByTestId('header-cash').innerText();
  const cashAmount = parseFloat(cashText.replace(/[$,]/g, ''));
  expect(cashAmount).toBeLessThan(10_000);
});
