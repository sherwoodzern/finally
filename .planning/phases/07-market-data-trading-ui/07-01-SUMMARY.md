---
phase: 07-market-data-trading-ui
plan: 01
subsystem: ui
tags: [zustand, sse, lightweight-charts, sparkline, flash, vitest]

requires:
  - phase: 06-frontend-scaffold-sse
    provides: usePriceStore SSE store with prices, status, lastEventAt; __setEventSource DI hook; selectTick + selectConnectionStatus selectors
provides:
  - flashDirection slice on usePriceStore set per ticker on price change with 500ms auto-clear via module-level timer Map
  - sparklineBuffers slice on usePriceStore appending raw.price each tick and trimming to the last 120 entries
  - selectedTicker slice plus setSelectedTicker action so the MainChart can read the user-clicked ticker
  - selectSparkline(ticker), selectFlash(ticker), and selectSelectedTicker selector closures for narrow Zustand subscriptions
affects: [07-02-PLAN, 07-03-PLAN, 07-04-PLAN, 07-05-PLAN, 07-06-PLAN, 07-07-PLAN]

tech-stack:
  added: []
  patterns:
    - "Pattern 1 (RESEARCH §2): Surgical store slice extension - same create() call, same EventSource lifecycle, additional slices keyed by ticker"
    - "Module-level Map<string, Timeout> for per-ticker transient state (flash) cleared on disconnect/reset"
    - "Per-ticker selector closures returning either undefined or a stable per-ticker reference so unrelated tickers do not re-render"

key-files:
  created:
    - frontend/src/lib/price-store.test.ts
  modified:
    - frontend/src/lib/price-store.ts

key-decisions:
  - "FLASH_MS = 500 chosen to match the CSS transition window described in CONTEXT D-01"
  - "SPARKLINE_WINDOW = 120 chosen as ~60s at the 500ms tick cadence (CONTEXT D-03)"
  - "Single set() per tick collects prices/sparklineBuffers/flashDirection/lastEventAt together so subscribers wake once; flash-clear timers scheduled AFTER the set() so the render sees the flash first"
  - "Flash timers cleared in BOTH disconnect() and reset() to prevent leaks across hot-reload and Phase 7 component-test resets"

patterns-established:
  - "Per-ticker transient state pattern: Map of timers keyed by ticker, scheduled in ingest, cleaned in disconnect/reset"
  - "Selector closure pattern: (ticker) => (s) => s.slice[ticker] keeps per-row Zustand subscriptions independent (Pattern C from PATTERNS.md)"

requirements-completed: [FE-03]

duration: 1min
completed: 2026-04-25
---

# Phase 07 Plan 01: Watchlist Store Extensions Summary

**Extended Phase 06 usePriceStore in place with flashDirection (D-01), sparklineBuffers (D-03), and selectedTicker slices, exposing per-ticker selector closures for Wave-3 components.**

## Performance

- **Duration:** ~1 min (single executor pass)
- **Started:** 2026-04-25T04:41:00Z
- **Completed:** 2026-04-25T04:42:07Z
- **Tasks:** 3 (Task 3 is verification-only, no source change)
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments

- Added three new state fields to `PriceStoreState`: `sparklineBuffers: Record<string, number[]>`, `flashDirection: Record<string, 'up' | 'down'>`, `selectedTicker: string | null`
- Added one new action: `setSelectedTicker(t: string | null)`
- Added three new exported selector closures: `selectSparkline(ticker)`, `selectFlash(ticker)`, `selectSelectedTicker`
- Added module-level constants `FLASH_MS = 500`, `SPARKLINE_WINDOW = 120`, and a `flashTimers: Map<string, Timeout>`
- Extended `disconnect()` and `reset()` to clear `flashTimers` and zero the new slices, preventing timer leaks
- Verified the full Vitest suite (8 existing Phase 06 + 7 new) all pass and `npm run build` exits 0

## Final Shape of `PriceStoreState`

```ts
interface PriceStoreState {
  prices: Record<string, Tick>;
  status: ConnectionStatus;
  lastEventAt: number | null;
  sparklineBuffers: Record<string, number[]>;       // NEW (D-03)
  flashDirection: Record<string, 'up' | 'down'>;     // NEW (D-01)
  selectedTicker: string | null;                      // NEW
  connect: () => void;
  disconnect: () => void;
  ingest: (payload: Record<string, RawPayload>) => void;
  reset: () => void;
  setSelectedTicker: (t: string | null) => void;     // NEW
}
```

Constants adopted at the module level: `FLASH_MS = 500`, `SPARKLINE_WINDOW = 120`, plus `flashTimers = new Map<string, ReturnType<typeof setTimeout>>()`.

## Test Counts

- **Before:** 8 tests (Phase 06: `price-stream.test.ts`)
- **After:** 15 tests total (8 unchanged + 7 new in `price-store.test.ts`)
- No Phase 06 test was modified; the extension is purely additive.

The 7 new tests cover:
1. `flashDirection` is `'up'` on a price rise
2. `flashDirection` is `'down'` on a price fall
3. `flashDirection` is cleared 500ms after the tick (`vi.useFakeTimers` + `vi.advanceTimersByTime(500)`)
4. `sparklineBuffers` appends the price on each tick
5. `sparklineBuffers` trims to the last 120 entries (verified with 125 emits — oldest retained is the 6th tick)
6. `setSelectedTicker` updates the store and `selectSelectedTicker` reads it (round-trip including `null`)
7. `reset()` clears flash timers AND zeroes all new slices (verified by advancing timers past the clear window after reset)

## Task Commits

Each task committed atomically:

1. **Task 1: Extend price-store.ts with flashDirection + sparklineBuffers + selectedTicker** - `f213102` (feat)
2. **Task 2: Add unit tests for flash + sparkline + selectedTicker** - `a1bef3b` (test)
3. **Task 3: Verify the full Vitest suite + build remain green** - no commit (verification-only; full suite green, build green; recorded here)

## Files Created/Modified

- `frontend/src/lib/price-store.ts` (modified) - Added flashTimers Map, FLASH_MS, SPARKLINE_WINDOW; extended PriceStoreState interface; rewrote ingest() to compute direction, buffer, and schedule clears in a single set() per tick; extended disconnect()/reset() to clear timers and slices; added setSelectedTicker action and three new exported selectors. Final size ~180 lines, within the surgical-extension budget noted in the plan.
- `frontend/src/lib/price-store.test.ts` (created) - 7-case Vitest suite using the Phase 06 MockEventSource + payload() harness verbatim, with `vi.useFakeTimers` wrapping each test for the 500ms flash-clear assertion.

## Decisions Made

- Followed RESEARCH §2 Pattern 1 verbatim — no deviation. Single `set()` per tick collects `prices` + `sparklineBuffers` + `flashDirection` + `lastEventAt` together; flash-clear timers scheduled AFTER the `set()` so subscribers see the flash before the deferred cleanup.
- Did not introduce any new `try/catch`. The only wire-boundary catch (`es.onmessage` D-19) remained untouched.

## Deviations from Plan

None — plan executed exactly as written. RESEARCH §2 Pattern 1 was followed step-for-step (constants, slices, ingest body, disconnect/reset cleanup, selectors). No auto-fixes required, no architectural decisions, no auth gates.

## Threat Flags

None — this plan stays inside the existing trust boundary. T-07-03 (sparkline XSS) is mitigated as planned: `sparklineBuffers` only stores `number` values from the same `raw.price` field already validated by `isValidPayload`, and no `dangerouslySetInnerHTML` is introduced.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Wave-3 components (Watchlist row, Positions row, MainChart panel) can now subscribe via `useStoreWithSelector(selectFlash('AAPL'))`, `selectSparkline('AAPL')`, and `selectSelectedTicker` with Zustand's per-key reference equality keeping render scope narrow.
- FE-03's store-side requirements (D-01 flash, D-03 sparkline buffer) are fully proved by unit tests; the row component still needs to translate `flashDirection[ticker]` into the `bg-up/10` / `bg-down/10` Tailwind classes (Plan 07-04 territory).
- No blockers for downstream plans.

## Self-Check: PASSED

- `frontend/src/lib/price-store.ts` modified — verified present (commit `f213102`).
- `frontend/src/lib/price-store.test.ts` created — verified present (commit `a1bef3b`).
- All 15 Vitest cases pass; `npm run build` exits 0.
- `git log` confirms both task commits exist on the worktree branch.

---
*Phase: 07-market-data-trading-ui*
*Completed: 2026-04-25*
