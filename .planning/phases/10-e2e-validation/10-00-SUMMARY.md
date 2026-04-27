---
phase: 10-e2e-validation
plan: 00
subsystem: testing
tags: [playwright, vitest, data-testid, react, nextjs, frontend, selectors]

requires:
  - phase: 07-trading-terminal
    provides: Header, TabBar, Watchlist, PositionsTable, TradeBar components targeted by Wave 2 specs
  - phase: 08-portfolio-visualization
    provides: data-testid placement pattern (Heatmap, PnLChart, ChatDrawer, SkeletonBlock)
provides:
  - Stable data-testid hooks on six terminal-component surfaces
  - header-total / header-cash on Header value spans
  - tab-{id} on TabBar role=tab buttons
  - watchlist-panel on Watchlist root <aside>
  - positions-table on PositionsTable root <section>
  - trade-bar on TradeBar root <section>
affects: [10-01, 10-02, 10-03, 10-04, 10-05]

tech-stack:
  added: []
  patterns:
    - "data-testid placement on data-bearing container (Heatmap.tsx:117 analog)"
    - "data-testid alongside id={`tab-${id}`} for a11y + selector parity"

key-files:
  created: []
  modified:
    - frontend/src/components/terminal/Header.tsx
    - frontend/src/components/terminal/TabBar.tsx
    - frontend/src/components/terminal/Watchlist.tsx
    - frontend/src/components/terminal/PositionsTable.tsx
    - frontend/src/components/terminal/TradeBar.tsx

key-decisions:
  - "Placed header test-ids on inner value <span> (data-bearing), not the outer <div> wrapper, matching Heatmap.tsx:117 / ChatDrawer.tsx:22 pattern."
  - "Kept TabBar id={`tab-${t.id}`} alongside new data-testid={`tab-${t.id}`}; the id pairs with aria-controls={`panel-${t.id}`} for a11y and must not be removed."
  - "No *.test.tsx files modified; existing 114 Vitest assertions remained green without changes."

patterns-established:
  - "Stable test-id selectors for Wave 2 Playwright specs to use via page.getByTestId(...) per PATTERNS.md selector hierarchy lines 481-495."

requirements-completed: [TEST-04]

duration: ~6min
completed: 2026-04-27
---

# Phase 10 Plan 00: Add data-testid Hooks to Terminal Components

**Six additive `data-testid` attributes across five `frontend/src/components/terminal/*.tsx` files, enabling Wave 2 Playwright specs to use stable selectors instead of brittle DOM-index queries.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-27T17:23:00Z
- **Completed:** 2026-04-27T17:29:01Z
- **Tasks:** 3 (Task 1, Task 2 multi-file, Task 3 verification gate)
- **Files modified:** 5 frontend component files

## Accomplishments
- Added `data-testid="header-total"` and `data-testid="header-cash"` to Header value spans
- Added `data-testid={`tab-${t.id}`}` to TabBar role=tab buttons (preserving the existing a11y `id` attribute)
- Added `data-testid="watchlist-panel"` to Watchlist root `<aside>`
- Added `data-testid="positions-table"` to PositionsTable root `<section>`
- Added `data-testid="trade-bar"` to TradeBar root `<section>`
- Confirmed zero behavioral regression: `npm run build` produced `frontend/out/index.html`; `npm run test:ci` ran 114 tests across 20 files, all passing

## Task Commits

Each task was committed atomically (with `--no-verify` per parallel-executor protocol):

1. **Task 1: Add `data-testid` to Header total + cash spans** — `ddeb643` (feat)
2. **Task 2: Add `data-testid` to TabBar, Watchlist, PositionsTable, TradeBar** — `da660bb` (feat)
3. **Task 3: Build + Vitest verification gate** — no code changes; `npm run build` and `npm run test:ci` both green; gate result documented in this summary

## Files Created/Modified
- `frontend/src/components/terminal/Header.tsx` — added `data-testid` on Total value span (line 43) and Cash value span (line 49)
- `frontend/src/components/terminal/TabBar.tsx` — added `data-testid={`tab-${t.id}`}` on role=tab `<button>` (line 34); existing `id` (line 33) preserved
- `frontend/src/components/terminal/Watchlist.tsx` — added `data-testid="watchlist-panel"` on root `<aside>` (line 27)
- `frontend/src/components/terminal/PositionsTable.tsx` — added `data-testid="positions-table"` on root `<section>` (line 30)
- `frontend/src/components/terminal/TradeBar.tsx` — added `data-testid="trade-bar"` on root `<section>` (line 84)

Diff stat across the five files: 5 files changed, 15 insertions(+), 5 deletions(-). No `*.test.tsx` files modified.

## Decisions Made

- **Header test-id placement on inner value `<span>`, not the outer `<div>`.** Matches the Heatmap.tsx:117 / PnLChart.tsx:93 / ChatDrawer.tsx:22 pattern (attribute on the data-bearing container). Lets Playwright assertions assert on the formatted dollar string directly via `page.getByTestId('header-cash').toHaveText('$10,000.00')` without traversing wrapper divs.
- **TabBar: `data-testid` added alongside existing `id={`tab-${t.id}`}` rather than as a replacement.** The `id` attribute pairs with `aria-controls={`panel-${t.id}`}` for screen-reader tab-panel association — removing it would regress a11y. Both attributes use the same template-literal value for visual symmetry.
- **No test changes.** Existing terminal-component tests use role/text/aria selectors (e.g., `getByRole('tablist')`, `toHaveAttribute('aria-selected', 'true')`) and assert presence of specific attributes, never absence. Adding `data-testid` is purely additive; all 114 Vitest assertions stayed green without modification.

## Deviations from Plan

None — plan executed exactly as written. All six attributes match their documented placement (file, line, target element). No `className`, `onClick`, state, rendering, or import changes. No `*.test.tsx` files touched.

## Issues Encountered

- **`node_modules` absent in fresh worktree.** First `npm run build` failed with `sh: next: command not found`. Resolved by running `npm ci --no-audit --no-fund` (509 packages, 10s). This is expected setup for a freshly created worktree, not a plan deviation. Subsequent `npm run build` succeeded immediately.
- **Pre-existing `next.config.mjs` rewrites warning.** Next.js 16 logs `Specified "rewrites" will not automatically work with "output: export"` during build. This is a pre-existing project config issue, unrelated to this plan, and does not fail the build (warning only). Out-of-scope for Plan 10-00 — left untouched per the deviation rules' scope-boundary clause.

## User Setup Required

None — no external service configuration required.

## Verification Evidence

- **`grep` of all six attributes:** all present at the documented lines (Header.tsx:43, Header.tsx:49, TabBar.tsx:34, Watchlist.tsx:27, PositionsTable.tsx:30, TradeBar.tsx:84).
- **TabBar `id` preservation:** `grep -nF 'id={`tab-${t.id}`}' TabBar.tsx` returns line 33 (still present alongside the new line 34 `data-testid`).
- **`npm run build`:** exit 0; `frontend/out/index.html` produced (13,039 bytes).
- **`npm run test:ci`:** exit 0; **114 tests passed** across **20 files** (well above the ≥111/≥19 plan floor); duration 1.71s.
- **Diff scope:** `git diff --stat` shows exactly 5 component files modified; `git diff --name-only ... | grep '\.test\.tsx$' | wc -l` returns 0.

## Next Phase Readiness

- Wave 2 spec plans (10-02 through 10-05) can now use the project's preferred `page.getByTestId(...)` selectors for header values, tab navigation, watchlist/positions/trade-bar container assertions, and within-region scoping.
- Wave 1 plan 10-01 (test infrastructure) is unaffected by this plan — zero overlap (10-01 creates files under `test/` only).
- No follow-up work required from this plan.

## Self-Check: PASSED

- [x] `frontend/src/components/terminal/Header.tsx` exists and contains both `header-total` and `header-cash` (verified at lines 43, 49)
- [x] `frontend/src/components/terminal/TabBar.tsx` exists and contains `data-testid={`tab-${t.id}`}` at line 34, with `id={`tab-${t.id}`}` preserved at line 33
- [x] `frontend/src/components/terminal/Watchlist.tsx` exists and contains `data-testid="watchlist-panel"` at line 27
- [x] `frontend/src/components/terminal/PositionsTable.tsx` exists and contains `data-testid="positions-table"` at line 30
- [x] `frontend/src/components/terminal/TradeBar.tsx` exists and contains `data-testid="trade-bar"` at line 84
- [x] Commit `ddeb643` exists in `git log` (Task 1)
- [x] Commit `da660bb` exists in `git log` (Task 2)
- [x] `frontend/out/index.html` produced by `npm run build`
- [x] `npm run test:ci` reports 114 passed / 0 failed

---
*Phase: 10-e2e-validation*
*Plan: 10-00*
*Completed: 2026-04-27*
