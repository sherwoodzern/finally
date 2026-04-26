---
plan: 08-05
phase: 08
status: complete
self_check: PASSED
completed_at: 2026-04-26
duration: ~12m
commits:
  - ec2bfb6
  - 98f6329
  - 4efef2e
  - bb4f318
requirements: [FE-11, FE-05, FE-06]
---

# 08-05 — SkeletonBlock + TabBar + Terminal Restructure

## What was built

Three Wave-2 deliverables landed in a single plan:

1. `frontend/src/components/skeleton/SkeletonBlock.tsx` — the shared
   `bg-border-muted/50 rounded animate-pulse` primitive (FE-11 D-13).
   `aria-hidden="true"`, consumer supplies sizing via `className`.
   Will be reused by Heatmap, PnLChart, and ChatThread skeletons in
   later plans.
2. `frontend/src/components/terminal/TabBar.tsx` — three-tab switcher
   (Chart / Heatmap / P&L) for the new tabbed center column.
   Active tab: 2px `border-b-2 border-accent-blue` underline +
   `text-foreground`. Inactive: `border-transparent text-foreground-muted
   hover:text-foreground`. Subscribes to `selectSelectedTab`; clicks
   dispatch `setSelectedTab` via `usePriceStore.getState()`.
   `aria-pressed` reflects active state for assistive tech.
3. `frontend/src/components/terminal/TabBar.test.tsx` — 4 Vitest
   cases covering: render order, default `selectedTab === 'chart'`,
   click dispatch, and active/inactive className contract.
4. `frontend/src/components/terminal/Terminal.tsx` — restructured to
   wrap the existing Phase 7 3-col grid in `flex flex-row` with a
   right-edge placeholder `<aside data-testid="chat-drawer-slot">`
   that Plan 06/07 will replace with `<ChatDrawer />`. Center column
   conditionally renders `MainChart` / `Heatmap` / `PnLChart` based
   on `selectedTab`.

## Files

| File | Status | Total | Non-blank | Budget |
|------|--------|-------|-----------|--------|
| `frontend/src/components/skeleton/SkeletonBlock.tsx` | NEW | 21 | 18 | ≤30 |
| `frontend/src/components/terminal/TabBar.tsx` | NEW | 42 | 37 | n/a |
| `frontend/src/components/terminal/TabBar.test.tsx` | NEW | 43 | n/a | n/a |
| `frontend/src/components/terminal/Terminal.tsx` | MODIFIED | 51 | 48 | ≤60 |

Terminal.tsx final LOC: **51 (48 non-blank)**, well under the
plan's 60-line cap. Net delta: +34 / -16.

## Drawer slot placeholder — reachable for Plan 06/07

The placeholder is a single `<aside>` element with three locator
hooks that Plan 06/07's ChatDrawer can be swapped in against:

```tsx
<aside
  data-testid="chat-drawer-slot"
  className="w-12 bg-surface-alt border-l border-border-muted flex flex-col"
  aria-label="Chat drawer placeholder"
/>
```

Plan 06/07 will replace this entire `<aside>` with
`<ChatDrawer />` (whose own root is `<aside ...>` per
PATTERNS.md "ChatDrawer.tsx"). The outer `flex flex-row` wrapper
is already in place so Plan 06/07 only edits the right-side child;
the workspace flex-1 sibling stays untouched.

The placeholder's `w-12` matches the UI-SPEC §5.1 "drawer
collapsed" width contract, so the visual layout is already
budgeted for the drawer's eventual presence even before Plan 06/07
lands.

## Tests

| File | Tests | Status |
|------|-------|--------|
| `frontend/src/components/terminal/TabBar.test.tsx` | 4 | PASS |
| **Full Vitest suite** | **93** (89 prior + 4 new) | **PASS** |

Test execution: 1.05s for 13 files (no Recharts in TabBar — no
`vi.mock('recharts', ...)` shim needed for this plan; the recharts
mock pattern from 08-04 was correctly skipped).

## TDD gate compliance

- RED commit: `98f6329` — `test(08-05): add failing TabBar tests`.
  Tests failed at `Failed to resolve import "./TabBar"` (TabBar.tsx
  did not exist), confirming the test was actually testing a
  not-yet-built surface (no false-pass risk).
- GREEN commit: `4efef2e` — `feat(08-05): implement TabBar component`.
  All 4 TabBar tests pass; full suite 93/93 green.
- REFACTOR: not needed; the GREEN implementation matched the plan's
  reference snippet 1:1 with no cleanup pass required.

The two non-TDD tasks (Task 1 SkeletonBlock, Task 3 Terminal restructure)
do not have inline test files; they are exercised transitively when
Plan 06/07 (ChatDrawer) and any future skeleton-using component land
their tests. SkeletonBlock is a 6-line render primitive — testing it
in isolation would be over-engineering per CLAUDE.md.

## Decisions (carry-forward)

- **D-Plan-08-05-1:** `setSelectedTab` is dispatched via
  `usePriceStore.getState().setSelectedTab(t.id)` rather than
  pulling the action through the selector subscription. This
  matches the established pattern in `PositionRow.tsx` (Phase 7)
  for `setSelectedTicker`. It also avoids unnecessary re-renders
  from action-identity churn under React 19 / Zustand 5.
- **D-Plan-08-05-2:** TabBar uses `aria-pressed` (toggle-button
  semantic) rather than `aria-current="page"` (route semantic) per
  UI-SPEC §5.2's reference snippet. Tabs are toggle buttons in
  state, not page navigation.
- **D-Plan-08-05-3:** Terminal.tsx leaves a `data-testid`-tagged
  `<aside>` placeholder rather than mounting `<ChatDrawer />`
  preemptively. This isolates the present plan's surface area
  (FE-05/06 tab switching) from the chat surface (FE-09) and lets
  Plan 06/07 do its own RED/GREEN cycle without worrying about
  upstream drawer-mounting glue.

## Threat model — disposition status

| Threat ID | Status |
|-----------|--------|
| T-08-11 (Tampering — TabBar dispatches) | Accepted as planned. TabBar's `TABS` array is a hardcoded module-level constant; no user input or store data ever flows into `setSelectedTab(...)`. The only call site is `onClick={() => usePriceStore.getState().setSelectedTab(t.id)}` where `t.id` is a TypeScript-narrowed `TabId` literal. |

## Deviations from Plan

None for the active task surface. Plan executed exactly as written.

### Out-of-scope items logged to deferred-items.md

- Pre-existing strict-`tsc` failures in `MainChart.test.tsx` (line
  58) and `Sparkline.test.tsx` (lines 33, 43) related to tuple-
  destructuring `noUncheckedIndexedAccess` strict-mode interaction.
  These exist on the main branch BEFORE plan 08-05 — verified by
  `git stash && tsc --noEmit`. Vitest still runs them green (TS
  errors only block `tsc --noEmit`, not Vite-driven test runs).
  Logged for Phase 9 polish or earlier if a tsc-clean gate is added
  to CI.

## Self-Check: PASSED

**Files created:**
- `frontend/src/components/skeleton/SkeletonBlock.tsx` — FOUND
- `frontend/src/components/terminal/TabBar.tsx` — FOUND
- `frontend/src/components/terminal/TabBar.test.tsx` — FOUND
- `frontend/src/components/terminal/Terminal.tsx` — MODIFIED (verified)

**Commits in `git log --all`:**
- `ec2bfb6` (SkeletonBlock) — FOUND
- `98f6329` (TabBar test RED) — FOUND
- `4efef2e` (TabBar GREEN) — FOUND
- `bb4f318` (Terminal restructure) — FOUND

**Verification:**
- `cd frontend && npm run test:ci` → 13 files / 93 tests / PASS
- `<TabBar />` count in Terminal.tsx → 1
- `<Heatmap />` count in Terminal.tsx → 1
- `<PnLChart />` count in Terminal.tsx → 1
- `<MainChart />` count in Terminal.tsx → 1
- `<Watchlist />` / `<Header />` / `<PositionsTable />` /
  `<TradeBar />` count in Terminal.tsx → each 1 (Phase 7 surfaces
  preserved as required)
- `flex flex-row` count → 1 (outer wrapper)
- `data-testid="chat-drawer-slot"` count → 1 (placeholder in place)
- Terminal.tsx total lines → 51 (≤60 cap)
