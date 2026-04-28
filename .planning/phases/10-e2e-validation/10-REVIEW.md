---
phase: 10-e2e-validation
reviewed: 2026-04-27T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - test/playwright.config.ts
  - test/docker-compose.test.yml
  - frontend/src/components/portfolio/Heatmap.tsx
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 10: Code Review Report

**Reviewed:** 2026-04-27
**Depth:** standard
**Files Reviewed:** 3
**Status:** clean

## Summary

Re-review of the three files touched by plan `10-09` (viewport bump on Playwright projects, tmpfs at `/app/db`
on the test-side compose, and a `formatter` on the Heatmap Recharts `<Tooltip>`). All three changes are small,
well-scoped, and do exactly what the plan claims.

- **`test/playwright.config.ts`** — explicit `viewport: { width: 1440, height: 900 }` is correctly applied AFTER
  the `devices['Desktop Chrome' | 'Desktop Firefox' | 'Desktop Safari']` spread on each of the three projects, so
  the override wins (later keys overwrite earlier ones in object spread). 1440x900 also aligns with the §10
  "desktop-first ... wide screens" production design contract from `planning/PLAN.md`. Closes Mode A
  test-environment misalignment.

- **`test/docker-compose.test.yml`** — `tmpfs: - /app/db` correctly mounts an in-memory fs over the production
  Dockerfile's `VOLUME /app/db` declaration (verified at `Dockerfile:57`). Each `compose up` gets a fresh empty
  directory; the FastAPI lifespan re-seeds the 10-ticker watchlist + $10k cash on the next start. The earlier
  anonymous-volume approach leaked across `up` invocations because `--abort-on-container-exit` does not remove
  anonymous volumes. Production compose/Dockerfile are untouched. Closes Mode A.2 cross-run SQLite carry-over.

- **`frontend/src/components/portfolio/Heatmap.tsx`** — `<Tooltip formatter={...}>` now pretty-prints the raw
  `weight` (which is `quantity * price` in dollars) using `Intl.NumberFormat` with `style: 'currency'`. The
  formatter signature is compatible with Recharts 3.8.1's `formatter?: (value, name, item, index, payload) =>
  ReactNode | [ReactNode, ReactNode]` (verified at
  `frontend/node_modules/recharts/types/component/Tooltip.d.ts:88`) — taking only `(value)` is fine; the unused
  trailing params are simply ignored. The non-finite branch returns `String(value ?? '')` which gracefully
  handles `undefined` / `null` / array values without throwing. The previous `wrapperStyle={{ pointerEvents:
  'none' }}` from plan 10-08 is preserved unchanged. **Closes WR-01 from the prior 10-REVIEW.md** (the warning
  is fully resolved).

No critical bugs. No security issues. No warnings. Two minor Info items below — both are observations on the
formatter, not defects, and explicitly do not require action for v1.

## Info

### IN-01: Formatter pretty-prints weight only; signed P&L% on the same row is still absent from the tooltip body

**File:** `frontend/src/components/portfolio/Heatmap.tsx:138-150`
**Issue:** The new `formatter` correctly converts the raw `weight` numeric (e.g., `1899.5274`) into `$1,899.53`,
which is the gap WR-01 flagged. However, the `TreeDatum` shape (lines 16-24) also carries `pnlPct`, `isUp`, and
`isCold` — all of which the heatmap tile labels already display visually. The default Recharts tooltip body
still renders only `name : <formatted value>` (e.g., `AAPL : $1,899.53`), so a hover does not surface the signed
P&L% the user sees on the tile itself.

This is below the bar of a defect — the figure shown is correct, formatted, and labeled by ticker — and the
plan 10-09 scope explicitly targeted only the unformatted-number complaint. Flagging as a forward note.

**Fix:** No action required. If a future phase wants a richer tooltip, supply a custom `content` prop or extend
the `formatter` to return a `[ReactNode, ReactNode]` tuple where the second entry incorporates `item.payload.pnlPct`,
e.g.:

```tsx
formatter={(value, _name, item) => {
  const datum = item?.payload as TreeDatum | undefined;
  const pnl = datum
    ? ` (${datum.pnlPct >= 0 ? '+' : ''}${datum.pnlPct.toFixed(2)}%)`
    : '';
  const n = typeof value === 'number' ? value : Number(value);
  const formatted = Number.isFinite(n)
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
    : String(value ?? '');
  return [`${formatted}${pnl}`, 'Value'];
}}
```

### IN-02: `Intl.NumberFormat` constructed inside the formatter on every hover render

**File:** `frontend/src/components/portfolio/Heatmap.tsx:143-148`
**Issue:** The `Intl.NumberFormat('en-US', {...})` constructor is invoked inside the inline arrow on every
tooltip render. For a hover-only path on a portfolio with single-digit positions this is irrelevant — the cost
is sub-millisecond and runs at human-event cadence, not animation cadence — but it is a textbook spot for a
module-scope constant. Performance is also out of v1 scope per the review charter. Pure observation.

**Fix:** No action required. If revisited, hoist a singleton:

```tsx
const USD = new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD',
  minimumFractionDigits: 2, maximumFractionDigits: 2,
});
// inside formatter: return USD.format(n);
```

---

_Reviewed: 2026-04-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
