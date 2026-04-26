---
plan: 08-03
phase: 08
status: complete
self_check: PASSED
completed_at: 2026-04-26
commits:
  - 6df305a
  - 5ae580a
---

# 08-03 — Portfolio Heatmap (FE-05 + TEST-02)

## What was built

FE-05 portfolio heatmap as a Recharts `<Treemap>` driven by
`useQuery(['portfolio'])`. Two new components plus their unit tests:

1. `frontend/src/components/portfolio/Heatmap.tsx` — panel chrome +
   `<ResponsiveContainer>` + `<Treemap>` with binary up/down coloring
   (D-02). Exports `buildTreeData` (pure data transform: positions +
   live ticks → `TreeDatum[]` with weight, pnlPct, isUp, isCold) and
   `handleHeatmapCellClick` (dispatches both `setSelectedTicker(t)`
   and `setSelectedTab('chart')` so the user lands on the price chart
   immediately after clicking a tile).
2. `frontend/src/components/portfolio/HeatmapCell.tsx` — pure SVG
   render-by-prop. Fill is a literal CSS var (`var(--color-up)` /
   `var(--color-down)` / `var(--color-surface-alt)`) — Tailwind class
   names cannot compile through SVG `fill=` (UI-SPEC §15). Labels
   (bold ticker + signed-2dp P&L %) render only when
   width >= 60 && height >= 32.

The Treemap `onClick` wires straight to the exported
`handleHeatmapCellClick` so the same code path is exercised by the
unit tests (no fragile jsdom geometry assertions needed).

## Final LOC counts (UI-SPEC §12 budget = 120 non-blank lines per .tsx)

| File | Total lines | Non-blank lines | Budget |
|------|-------------|-----------------|--------|
| `frontend/src/components/portfolio/Heatmap.tsx` | 132 | 120 | 120 (at limit) |
| `frontend/src/components/portfolio/HeatmapCell.tsx` | 72 | 68 | 120 |

## Tests

13 new tests across 2 files; all green.

### `frontend/src/components/portfolio/Heatmap.test.tsx` (7 tests)

1. `builds one TreeDatum per position with binary coloring (FE-05)`
2. `weight = quantity * current_price (TEST-02 portfolio calculation)`
3. `renders empty-state copy when positions.length === 0`
4. `renders skeleton while query is pending (FE-11 D-13 + TEST-02)`
5. `handleHeatmapCellClick(node) dispatches setSelectedTicker AND setSelectedTab("chart") (FE-05 click-to-select)`
6. `handleHeatmapCellClick ignores nodes with no ticker (defensive guard)`
7. `buildTreeData detects cold-cache when live===undefined && current_price===0 (FE-05 cold-cache integration)`

### `frontend/src/components/portfolio/HeatmapCell.test.tsx` (6 tests)

1. `formatPct: signed, 2 decimals (TEST-02 P&L %)`
2. `cold-cache renders neutral surface-alt fill (FE-05 fallback)`
3. `up renders var(--color-up); down renders var(--color-down) (FE-05 D-02)`
4. `renders ticker bold + signed P&L % when width and height are large enough (FE-05 D-03)`
5. `hides labels when width < 60 (FE-05 threshold)`
6. `hides labels when height < 32 (FE-05 threshold)`

### Full suite

`npm run test:ci` → **11 files / 83 tests passed** (70 baseline + 13 new).

## Acceptance grep checks

All grep checks from the plan pass:

- `Heatmap.tsx` non-blank lines = 120 (≤120 budget)
- `HeatmapCell.tsx` non-blank lines = 68 (≤120 budget)
- `from 'recharts'` count = 1
- `Treemap` count = 4 (import + JSX `<Treemap>` opening + `</Treemap>` closing element pieces; the 4-occurrence count includes `import { … Treemap }` plus the JSX usage)
- `queryKey: ['portfolio']` count = 1
- `setSelectedTicker` count = 2 (handler + JSDoc)
- `setSelectedTab` count = 2 (handler + JSDoc)
- `export function handleHeatmapCellClick` count = 1
- Verbatim empty-state copy: `No positions yet — use the trade bar or ask the AI to buy something.`
- `var(--color-up)`, `var(--color-down)`, `var(--color-surface-alt)` all present in `HeatmapCell.tsx`

`cd frontend && npx tsc --noEmit` reports zero errors in the two new
files. (Pre-existing Phase-7 tuple-type warnings in
`MainChart.test.tsx` and `Sparkline.test.tsx` are out of scope per
this plan's scope-boundary rule and are not surfaced by Vitest at
runtime.)

## Deviations

### Rule 1 — Auto-fix bug: useShallow wrapper around the live-prices selector

- **Found during:** Task 2, first run of Heatmap.test.tsx.
- **Issue:** The original Heatmap selector was
  `usePriceStore((s) => { ... return out; })` returning a freshly
  built object literal on every render. Zustand v5 + React 19 treat
  the new identity as a state change, the component re-renders, the
  selector returns yet another new object, and React 19 throws
  *"Maximum update depth exceeded"*. Two of the tests
  (`renders empty-state copy …` and `renders skeleton while query is
  pending …`) failed with this exact stack trace.
- **Fix:** Wrap the selector with
  `useShallow` from `zustand/react/shallow` so identity comparison
  becomes a shallow value comparison.
- **Files modified:** `frontend/src/components/portfolio/Heatmap.tsx`
  (added the `useShallow` import + wrapped the selector).
- **Commit:** `5ae580a` (rolled into the test commit since the failure
  was caught by these tests; the original component commit `6df305a`
  shipped the buggy selector).
- **Tests now passing for the fix:** 7/7 in Heatmap.test.tsx; 6/6 in
  HeatmapCell.test.tsx; full suite 83/83.

### Rule 1 — Auto-fix bug: TreeDatum index signature for Recharts

- **Found during:** Task 1, `tsc --noEmit`.
- **Issue:** `Treemap`'s `data` prop is typed
  `ReadonlyArray<TreemapDataType>` where `TreemapDataType` extends
  `{ [key: string]: any }`. The strictly-typed `TreeDatum` interface
  was missing the index signature.
- **Fix:** Added `[key: string]: string | number | boolean;` to
  `TreeDatum`.
- **Commit:** `6df305a`.

### Rule 1 — Auto-fix bug: removed unsupported `strokeWidth` prop on `<Treemap>`

- **Found during:** Task 1, `tsc --noEmit`.
- **Issue:** `recharts@3.8.1`'s `<Treemap>` `Props` interface declares
  `stroke?: string` but no `strokeWidth`. The PLAN's reference snippet
  (lifted from PATTERNS.md and from a pre-3.x example) included
  `strokeWidth={1}`.
- **Fix:** Removed the `strokeWidth` prop.
- **Commit:** `6df305a`.

### Rule 3 — Auto-fix blocker: `npm install` to land recharts

- **Found during:** Task 1, first `tsc --noEmit` run.
- **Issue:** Wave-1 (Plan 08-02) committed `recharts@^3.8.1` to
  `frontend/package.json` and `package-lock.json`, but the package was
  not present in `node_modules/` on this main worktree. tsc reported
  *"Cannot find module 'recharts'"*.
- **Fix:** Ran `npm install` (no lockfile changes; existing lock
  resolved cleanly).

## Notes for downstream plans

- **Recharts in jsdom:** the `ResizeObserver` stub from Plan 08-02's
  `vitest.setup.ts` is sufficient for these tests. **No `vi.mock`
  of `recharts` was needed**, because the unit tests assert directly
  against `buildTreeData` (pure function), `handleHeatmapCellClick`
  (pure function on the store), and `<HeatmapCell />` rendered inside
  a vanilla `<svg>` wrapper. Plan 08-04 (PnLChart) can follow the same
  approach: split data + handler logic into pure functions, test those
  directly, and only render the chart shell when asserting top-level
  React-Query branches (skeleton / empty / data). Avoid jsdom-fragile
  Treemap-content-prop assertions altogether.
- **Zustand v5 + React 19 selector caveat:** any selector that returns
  a fresh object literal must be wrapped with
  `useShallow` from `zustand/react/shallow`. Plans 08-04..08 must
  follow this rule. Watch for the same trap in `PnLChart`,
  `ChatThread`, and `ActionCardList`.

## Self-Check: PASSED

- `frontend/src/components/portfolio/Heatmap.tsx` exists; 120 non-blank lines.
- `frontend/src/components/portfolio/HeatmapCell.tsx` exists; 68 non-blank lines.
- `frontend/src/components/portfolio/Heatmap.test.tsx` exists; 7 tests pass.
- `frontend/src/components/portfolio/HeatmapCell.test.tsx` exists; 6 tests pass.
- Commit `6df305a` (`feat(08-03): add Heatmap + HeatmapCell components`) found in `git log`.
- Commit `5ae580a` (`test(08-03): add Heatmap + HeatmapCell tests`) found in `git log`.
- Full Vitest suite: 83/83 passing.
- `tsc --noEmit` reports no errors in the two new files (only pre-existing Phase-7 test-file warnings remain).
