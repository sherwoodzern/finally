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

  // Dismiss any lingering Recharts hover tooltip before clicking a sibling
  // tab. Pointer-event interception by the tooltip <td>{ticker}</td>
  // subtree is the documented failure mode (10-VERIFICATION.md Gap Group B,
  // all 3 browsers). The previous `page.mouse.move(0, 0)`-only mitigation
  // was insufficient because once the tooltip pins to a cell, moving the
  // cursor away does not retract the overlay; Escape is what tells the
  // Recharts tooltip lifecycle to dismiss. Both steps together (Escape +
  // mouse displacement) are robust across chromium, firefox, and webkit.
  const dismissChartTooltip = async () => {
    await page.keyboard.press('Escape');
    await page.mouse.move(0, 0);
  };

  // Buy a position so the heatmap leaves the skeleton state.
  // META — D-08 isolation from NVDA/JPM (10-03), PYPL (10-02), AMZN (10-06).
  await page.getByLabel('Ticker').fill('META');
  await page.getByLabel('Quantity').fill('1');
  await page.getByRole('button', { name: 'Buy' }).click();
  // Scope to positions-table — the watchlist also renders a "Select META" row,
  // so the unscoped locator hits a strict-mode collision.
  await expect(
    page
      .getByTestId('positions-table')
      .getByRole('button', { name: 'Select META' }),
  ).toBeVisible({ timeout: 10_000 });

  // Heatmap tab: click, assert the Recharts Treemap container is visible AND
  // that an SVG with at least one <rect> for a position has actually rendered
  // inside it. The wrapper div alone passing toBeVisible() is insufficient —
  // a Recharts ResponsiveContainer with height="100%" inside a flex-1 parent
  // can mount the wrapper div with positive size but emit a 0×0 inner div
  // (the bug fixed by giving the chart wrapper an explicit pixel height).
  // This assertion closes that verification gap.
  await page.getByTestId('tab-heatmap').click();
  await expect(page.getByTestId('heatmap-treemap')).toBeVisible({ timeout: 10_000 });
  await expect(page.locator('[data-testid="heatmap-treemap"] svg rect')).not.toHaveCount(0, {
    timeout: 10_000,
  });

  // P&L tab: click and assert both the chart container, the summary text,
  // AND that an SVG with at least one <path> (the line series) has rendered.
  // Same verification-gap closure as the heatmap above.
  await dismissChartTooltip();
  await page.getByTestId('tab-pnl').click();
  await expect(page.getByTestId('pnl-chart')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId('pnl-summary')).toBeVisible();
  await expect(page.locator('[data-testid="pnl-chart"] svg path')).not.toHaveCount(0, {
    timeout: 10_000,
  });
});
