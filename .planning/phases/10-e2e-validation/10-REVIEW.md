---
phase: 10-e2e-validation
reviewed: 2026-04-27T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - frontend/src/components/portfolio/Heatmap.tsx
  - test/01-fresh-start.spec.ts
  - test/04-sell.spec.ts
  - test/05-portfolio-viz.spec.ts
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-04-27
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the four files modified by Phase 10 gap-closure work (commits 9924ccc / a149480 / 0a58eb9 / c53810f). The
changes are small, well-targeted, and consistent with the documented plan in `10-08-PLAN.md`. The single production
edit (`Heatmap.tsx`) uses a correctly-typed Recharts 3.8.1 prop (`wrapperStyle?: CSSProperties` per
`recharts/types/component/Tooltip.d.ts:183`). The three test edits all preserve the project's documented anti-pattern
guards — no `waitForTimeout`, no `toHaveText` regex, scoped selectors, `expect.poll` for async data races.

No critical bugs, no security issues. One Warning concerns the rendered content of the new explicit `<Tooltip />` —
adding it to `<Treemap>` opts the user into Recharts' DEFAULT tooltip body, which displays the raw `weight` numeric
field (`quantity * price`) without formatting or unit. Worth confirming this is acceptable UX or supplying a custom
`content`/`formatter`. Four Info items cover minor robustness and clarity observations.

The harness gate state (18/21 with Mode A misdiagnosed) is outside this file-level review's scope; it is properly
captured in `10-VERIFICATION.md` and a `10-09` plan should drive resolution.

## Warnings

### WR-01: Default Recharts Tooltip body shows raw `weight` (dollars-as-bare-number)

**File:** `frontend/src/components/portfolio/Heatmap.tsx:138`
**Issue:** The new `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` is rendered with NO `content`,
`formatter`, or `labelFormatter` prop. For a `Treemap`, Recharts' default `DefaultTooltipContent` renders
`payload[0].name : payload[0].value`, which in this component is `<ticker> : <weight>` where `weight` is
`Math.max(p.quantity * price, 0.01)` (Heatmap.tsx:49). The user will see an unlabeled, unformatted number such as
`AAPL : 1899.5274` — a dollar position value rendered with no `$`, no thousands separator, no rounding.

The `TreeDatum` shape (lines 16-24) carries richer fields that would make a more useful tooltip — `ticker`, `pnlPct`,
`isUp`, `isCold` — none of which surface in the default body. The 10-08 plan's threat model (T-10-08-01) asserts
"Tooltip exposes the same per-position figures the rest of the UI already shows" — but the heatmap labels show
`ticker` + signed `pnlPct%`, NOT raw position dollar value, so this Tooltip surface is in fact NEW data with NO
formatting.

This is below the bar of a critical bug (the data is the user's own portfolio data, not sensitive), but it is a UX
regression on the heatmap and may surprise users.

**Fix:** Either supply a `formatter` that pretty-prints the weight, OR a custom `content` that surfaces the same
fields the heatmap labels already show. Minimal example using `formatter`:

```tsx
<Tooltip
  wrapperStyle={{ pointerEvents: 'none' }}
  formatter={(value: number, _name, item) => {
    const datum = item?.payload as TreeDatum | undefined;
    const pnl = datum ? `${datum.pnlPct >= 0 ? '+' : ''}${datum.pnlPct.toFixed(2)}%` : '';
    return [`$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} (${pnl})`, 'Value'];
  }}
/>
```

If the team prefers to keep the default body until a follow-up phase explicitly designs the heatmap tooltip, leave a
TODO comment alongside the existing block comment so future reviewers know this is deferred, not overlooked.

## Info

### IN-01: Comment numbering jumps `1.` -> `3.` after assertion removal

**File:** `test/01-fresh-start.spec.ts:24, 44`
**Issue:** The original spec had three numbered comments (`// 1.`, `// 2.`, `// 3.`). Commit 0a58eb9 dropped `// 2.`
along with its absolute cash assertion but left the surrounding numbering intact, so the spec now reads
`// 1. ...` then a 9-line explanatory comment (Cross-project SQLite leak) then `// 3. ...`. This is mildly confusing
to a future reader who may wonder what happened to step 2.
**Fix:** Renumber to `// 1.` / `// 2.` (collapsing the gap), or drop the numbering entirely — the explanatory
comments are now self-describing.

### IN-02: Streaming-proof asserts em-dash absence on entire row text, not just price cell

**File:** `test/01-fresh-start.spec.ts:48`
**Issue:** `await expect(aaplRow).not.toContainText('—', { timeout: 10_000 })` checks the full row's text content.
The row contains the ticker letters, the price, the daily change %, and the sparkline. If a future change adds an
em-dash placeholder to a different column (e.g., volume), the assertion still passes if THAT column's em-dash is
present, as long as the price column has updated. Conversely, if the price column lost its em-dash but a NEW column
introduced one, the test would silently start failing — but for the wrong reason.

Today this works because em-dash is unique to the pre-tick price placeholder. Mostly informational; tightening would
require a `data-testid` on the price cell.
**Fix:** Optional — add a `data-testid="watchlist-row-price"` to the price `<td>` in `WatchlistRow.tsx` and assert
on that scoped locator. Defer until a price-cell-specific selector is needed by another spec.

### IN-03: `dismissChartTooltip` called before any user hover has occurred

**File:** `test/05-portfolio-viz.spec.ts:49`
**Issue:** `dismissChartTooltip()` is called between the heatmap-tab visibility assertion (line 46) and the P&L tab
click (line 50), but the test never hovers a heatmap cell. Playwright's `toBeVisible()` auto-wait does not move the
real mouse onto the element. So the tooltip being dismissed cannot have appeared in this code path. After the 10-08
production fix (`pointerEvents: 'none'` on the Tooltip wrapper), the helper is now triple-defense: it dismisses a
tooltip that (a) was never opened in this test and (b) wouldn't intercept clicks anyway.

This is intentional per the 10-08 plan ("leave AS IS, it becomes belt-and-suspenders"). Flagging only so a future
author cleaning up E2E specs is aware the helper is now strictly redundant.
**Fix:** No action required for v1. When 10-09 closes Mode A definitively and the harness gate is green for several
runs, consider removing the helper to simplify the spec.

### IN-04: `parseFloat` on cell text tolerates whitespace via `.trim()` but silently masks `NaN`

**File:** `test/04-sell.spec.ts:47, 64`
**Issue:** Both poll callbacks do `parseFloat((await jpmQty.innerText()).trim())`. If the cell rendered with
unexpected content (e.g., a transient `—` placeholder during refetch, or empty during DOM update),
`parseFloat('—')` = `NaN`, `parseFloat('')` = `NaN`. `NaN >= 2` and `NaN === postBuyQty - 1` are both false, so
`expect.poll` retries and times out at 10_000ms with a useless error. This is "fail safe" but the failure message
won't pinpoint the cause.

In practice the qty cell renders a number from the React Query payload, so `NaN` should not appear — flagging as
defensive observation only.
**Fix:** No action required. If a future flake surfaces, swap `parseFloat` for `Number()` (which preserves `NaN`
identically but pairs with `Number.isNaN` checks more explicitly), or add an explicit guard:
`if (Number.isNaN(n)) return -1;` so the matcher rejects faster and surfaces "got -1" instead of timing out.

---

_Reviewed: 2026-04-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
