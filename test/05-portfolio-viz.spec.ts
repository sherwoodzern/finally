// test/05-portfolio-viz.spec.ts
// PLAN.md §12 row 5 — heatmap + P&L chart render after a position exists.
// Phase 10 plan 10-04. D-08 ticker isolation: META (not used by 02/03/04/06).
//
// Heatmap renders the SKELETON state when positions are empty (Heatmap.tsx:83);
// only with >=1 position does [data-testid=heatmap-treemap] mount (Heatmap.tsx:117).
// We therefore buy META x 1 via the TradeBar UI as a precondition for both
// tab assertions.
//
// Tab buttons expose data-testid="tab-{id}" (TabBar.tsx:34) — preferred over
// role+name regex for cross-engine stability.

import { test, expect } from '@playwright/test';

test('portfolio viz: heatmap and P&L chart render after a position exists', async ({ page }) => {
  await page.goto('/');

  // Buy a position so the heatmap leaves the skeleton state.
  // META — D-08 isolation from NVDA/JPM (10-03), PYPL (10-02), AMZN (10-06).
  await page.getByLabel('Ticker').fill('META');
  await page.getByLabel('Quantity').fill('1');
  await page.getByRole('button', { name: 'Buy' }).click();
  await expect(
    page.getByRole('button', { name: 'Select META' }),
  ).toBeVisible({ timeout: 10_000 });

  // Heatmap tab: click and assert the Recharts Treemap container is visible.
  await page.getByTestId('tab-heatmap').click();
  await expect(page.getByTestId('heatmap-treemap')).toBeVisible({ timeout: 10_000 });

  // P&L tab: click and assert both the chart container and the summary text.
  await page.getByTestId('tab-pnl').click();
  await expect(page.getByTestId('pnl-chart')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId('pnl-summary')).toBeVisible();
});
