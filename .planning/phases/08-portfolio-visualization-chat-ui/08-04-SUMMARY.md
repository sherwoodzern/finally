---
plan: 08-04
phase: 08
status: complete
self_check: PASSED
completed_at: 2026-04-26
duration: 14m 36s
commits:
  - bb43210
  - ccda211
requirements: [FE-06, TEST-02]
---

# 08-04 — P&L Line Chart (FE-06 + TEST-02)

## What was built

FE-06 P&L line chart as a Recharts `<LineChart>` driven by
`useQuery(['portfolio', 'history'])`. Two new components plus their
unit tests:

1. `frontend/src/components/portfolio/PnLChart.tsx` — panel chrome +
   header summary + `<ResponsiveContainer><LineChart>` with
   `<CartesianGrid>` + `<XAxis>` + `<YAxis>` + dotted `<ReferenceLine
   y={10000}>` (D-05) + `<Tooltip content={<PnLTooltip />}>` + a
   single `<Line dataKey="total_value" />`. Stroke flips at
   break-even (D-06): `lastTotal >= 10000 ? 'var(--color-up)' :
   'var(--color-down)'` — both literal CSS-var strings, no Tailwind
   class compiled to SVG. Renders the verbatim 1-snapshot empty
   state from UI-SPEC §8.3 and the matching error fallback. Header
   summary `data-testid="pnl-summary"` shows formatted current
   total + signed delta vs $10k.
2. `frontend/src/components/portfolio/PnLTooltip.tsx` — pure render
   helper for the Recharts `Tooltip.content` prop. Renders a
   3-line card: timestamp, formatted current total, signed delta vs
   $10k. Typed with a small local `PnLTooltipProps` interface
   (`active`, `payload`) rather than Recharts'
   `TooltipContentProps` — RESEARCH.md §Version Verification flags
   the rename from `TooltipProps` (2.x) to `TooltipContentProps`
   (3.x); we deliberately stay with a local typing to keep the
   tooltip portable across patch versions.

## Final LOC counts (UI-SPEC §12 budget = 120 non-blank per .tsx)

| File | Total lines | Non-blank lines | Budget |
|------|-------------|-----------------|--------|
| `frontend/src/components/portfolio/PnLChart.tsx` | 120 | 107 | 130 (plan flag-if-exceeded) |
| `frontend/src/components/portfolio/PnLTooltip.tsx` | 49 | 43 | 60 |
| `frontend/src/components/portfolio/PnLChart.test.tsx` | 110 | 100 | n/a |

PnLChart.tsx fits inside the plan's 130-line cap (initial draft was
140 lines; trimmed branch boilerplate by extracting a shared
`skeleton` element and collapsing single-statement returns into
arrow form).

## Stroke values verified

```
$ grep -F "var(--color-up)" frontend/src/components/portfolio/PnLChart.tsx
  const stroke = lastTotal >= 10000 ? 'var(--color-up)' : 'var(--color-down)';
$ grep -F "var(--color-down)" frontend/src/components/portfolio/PnLChart.tsx
  const stroke = lastTotal >= 10000 ? 'var(--color-up)' : 'var(--color-down)';
```

Both are literal strings flowing into the `<Line stroke={stroke}>`
prop — no concatenation, no template literal, no user-controlled
input (T-08-10 mitigated).

## Tests

6 new tests in `PnLChart.test.tsx`; all green.

| # | Name | Maps to |
|---|------|---------|
| 1 | `renders skeleton while pending (FE-11 D-13)` | FE-11 D-13 |
| 2 | `1-snapshot empty state copy renders (FE-06 Discretion)` | FE-06 Claude's Discretion |
| 3 | `line stroke is var(--color-up) when latest total_value >= 10000 (FE-06 D-06)` | D-06 |
| 4 | `line stroke is var(--color-down) when latest total_value < 10000 (FE-06 D-06)` | D-06 |
| 5 | `includes a <ReferenceLine y=10000> rendered as a dashed SVG line (FE-06 D-05)` | D-05 |
| 6 | `header summary shows latest total + signed delta vs $10k (FE-06)` | FE-06 |

### Full suite

`npm run test:ci` → **12 files / 89 tests passed** (83 baseline +
6 new). `npx tsc --noEmit` reports zero new errors (only
pre-existing Phase-7 tuple-type warnings in
`MainChart.test.tsx` and `Sparkline.test.tsx` remain — out of
scope per the executor scope-boundary rule, already documented in
08-03 SUMMARY).

## Acceptance grep checks

All grep checks from the plan pass:

- `grep -c "from 'recharts'" PnLChart.tsx` → `1`
- `grep -c "ReferenceLine" PnLChart.tsx` → `2` (import + JSX)
- `grep -c "y={10000}" PnLChart.tsx` → `1`
- `grep -c "queryKey: \['portfolio', 'history'\]" PnLChart.tsx` → `1`
- `grep -F "var(--color-up)" PnLChart.tsx` → matches
- `grep -F "var(--color-down)" PnLChart.tsx` → matches
- `grep -F "Building P&amp;L history…" PnLChart.tsx` → matches
- `grep -F "Couldn&apos;t load P&amp;L history. Retrying in 15s." PnLChart.tsx` → matches
- `grep -F 'vs $10k' PnLTooltip.tsx` → 2 matches (docstring + JSX)

## Deviations

### Rule 3 — Auto-fix blocker: vi.mock recharts.ResponsiveContainer in PnLChart.test.tsx

- **Found during:** Task 2, first run of the test suite.
- **Issue:** Three of the six tests (`stroke up`, `stroke down`,
  `<ReferenceLine y=10000>`) failed with `expected false to be
  true` / `expected 0 to be greater than 0`. Vitest stderr showed
  Recharts logging *"The width(-1) and height(-1) of chart should
  be greater than 0"*. Root cause: jsdom has no layout engine, the
  global `ResizeObserver` stub from `vitest.setup.ts` only
  prevents the constructor from throwing — it never invokes the
  observer callback. So `<ResponsiveContainer>` measures the parent
  div as -1×-1 and Recharts skips rendering all SVG paths and
  reference lines. The skeleton/empty-state/header-summary tests
  passed because they don't hit the chart-render branch.
- **Fix:** Added a file-local `vi.mock('recharts', ...)` that
  overrides only `ResponsiveContainer` to a 800×600 cloneElement
  shim. All other Recharts components (`LineChart`,
  `ReferenceLine`, `Line`, `Tooltip`, `CartesianGrid`, `XAxis`,
  `YAxis`) come from the real module via `vi.importActual`, so the
  test exercises real Recharts SVG rendering. This is the standard
  escape hatch documented in 08-RESEARCH.md §Common Pitfall 5
  ("Concrete: mock Recharts ResponsiveContainer for tests"). The
  Heatmap test suite from Plan 08-03 didn't need this because it
  asserts only against pure functions (`buildTreeData`,
  `handleHeatmapCellClick`) and never against rendered SVG;
  PnLChart's plan asks for stroke-color and reference-line
  assertions on the actual rendered chart, which is why the mock
  is required here.
- **Files modified:** `frontend/src/components/portfolio/PnLChart.test.tsx`
  (file-local `vi.mock` block).
- **Commit:** `ccda211`.

### Rule 1 — Auto-fix bug: PnLChart.tsx initial draft exceeded 130-line cap

- **Found during:** Task 1, post-Write LOC count.
- **Issue:** Verbatim plan template was 140 lines / 125 non-blank,
  above the 130-line flag-if-exceeded cap.
- **Fix:** Collapsed `formatMoney` formatting object to one line,
  inlined the `tickTime` `new Date(value).toLocaleTimeString` call,
  extracted a shared `skeleton` element used for both `isPending`
  and `snapshots.length === 0` branches, and collapsed two
  single-statement returns to arrow form. No behavioral change.
- **Files modified:** `frontend/src/components/portfolio/PnLChart.tsx`.
- **Commit:** `bb43210` (rolled into the component commit before the
  test commit).

## Notes for downstream plans

- **The local `vi.mock('recharts', ...)` ResponsiveContainer shim
  established in 08-04 is the recommended pattern for any future
  Phase 8 plan that needs to assert against real Recharts SVG
  output in jsdom.** Add it at the top of the test file (before
  the import of the component under test) and import only
  `vi.importActual` to keep all the rest of Recharts real. Plans
  08-05+ that test Treemap or LineChart geometry should follow
  this same pattern.
- **PnLTooltip's local-typed-props approach** is also the
  recommended way to type custom Recharts tooltips going forward —
  Recharts 3.x renamed `TooltipProps` to `TooltipContentProps`,
  but the runtime shape (`active`, `payload[].payload`) is stable
  across all 3.x patch versions, and a 4-property interface keeps
  the import surface minimal and forward-compatible.
- **Header-summary `data-testid="pnl-summary"`** — kept as a
  test-only marker because the actual summary text contains an
  ASCII parenthesis pair around the delta-vs-$10k clause and a
  matched-text regex would otherwise need to anchor on the
  formatted total. The `data-testid` is a tiny extra surface for
  test stability.
- **No Threat Flags surface introduced.** Both T-08-09 (Date.parse
  silent fail in PnLTooltip) and T-08-10 (line stroke string
  interp) are mitigated as planned: `recorded_at` is rendered via
  `new Date(...).toLocaleString(...)` (no HTML), and `stroke` is
  one of two literal strings.

## Self-Check: PASSED

- `frontend/src/components/portfolio/PnLChart.tsx` exists; 107 non-blank lines.
- `frontend/src/components/portfolio/PnLTooltip.tsx` exists; 43 non-blank lines.
- `frontend/src/components/portfolio/PnLChart.test.tsx` exists; 6 tests pass.
- Commit `bb43210` (`feat(08-04): add PnLChart + PnLTooltip components (FE-06)`) found in `git log`.
- Commit `ccda211` (`test(08-04): add PnLChart vitest suite (FE-06 + TEST-02)`) found in `git log`.
- Full Vitest suite: 89/89 passing (12 test files).
- `tsc --noEmit` reports no errors in the new files.
