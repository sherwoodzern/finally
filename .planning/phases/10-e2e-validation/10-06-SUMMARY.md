---
phase: 10-e2e-validation
plan: 06
subsystem: testing
tags: [playwright, e2e, parallelism, gap-closure, strict-mode-locators, relative-assertions]

requires:
  - phase: 10-e2e-validation
    provides: 7 spec files + harness foundation (Plans 10-00..10-05); VERIFICATION Gap Group A failure list (8 of 9)
  - phase: 10-e2e-validation
    provides: data-testid="watchlist-panel" + data-testid="positions-table" (Plan 10-00) - selector scopes used by Tasks 2-4

provides:
  - "test/playwright.config.ts: workers: 1 single-worker serialisation realising CONTEXT D-07 intent"
  - "test/01-fresh-start.spec.ts: every Select-<ticker> locator scoped to page.getByTestId('watchlist-panel')"
  - "test/03-buy.spec.ts: pre-trade absolute $10,000.00 cash assertion removed - post-trade relative `< 10_000` is the only cash check"
  - "test/04-sell.spec.ts: post-sell qty assertion as expect.poll relative delta `postBuyQty - 1` instead of absolute regex"

affects:
  - 10-07-tooltip-dismissal+harness-gate (Plan 10-07 owns the canonical-command 21/21 green gate run; runs AFTER 10-06)

tech-stack:
  added: []
  patterns:
    - "expect.poll for relative-delta numeric assertions (decouples from text-formatting variants)"
    - "Single-worker serialisation as the simplest fix for cross-spec contention on shared SQLite state"
    - "Selector scoping via parent getByTestId whenever the same accessible name appears in multiple regions (watchlist vs positions table)"

key-files:
  created: []
  modified:
    - test/playwright.config.ts
    - test/01-fresh-start.spec.ts
    - test/03-buy.spec.ts
    - test/04-sell.spec.ts

key-decisions:
  - "Chose option (a) workers: 1 over (b) per-project worker cap (Playwright doesn't support it), (c) per-spec compose run orchestration, (d) sharded spec files. Option (a) is the simplest path; runtime cost (a few extra seconds end-to-end) is irrelevant for a single-user demo project. Reproducible green is the priority."
  - "Dropped 03-buy pre-trade $10k assertion entirely instead of moving it under a worker-isolated branch. The post-trade `cashAmount < 10_000` relative check is sufficient and survives any prior-state cash debits, so the absolute pre-trade sanity is fragile noise even under workers: 1."
  - "04-sell switched to expect.poll relative-delta `postBuyQty - 1` to decouple the assertion from text-formatting variants (1 vs 1.0 vs 1.00). expect.poll reduces to a numeric .toBe(), parsing the qty cell text on every poll iteration until the value matches or times out."
  - "Harness gate result (21/21 green or remaining failures) is OWNED BY Plan 10-07's SUMMARY, not this one. 10-06 only landed the Gap Group A spec/config edits."

patterns-established:
  - "Relative-delta assertions over absolute-value assertions when shared mutable state could leak across specs (cash_balance, position quantity)"
  - "Scope page.getByRole locators with parent page.getByTestId whenever the same accessible name (e.g. `Select META`) appears in multiple regions of the same page (watchlist row vs positions row)"
  - "expect.poll for relative numeric comparisons - parses on every iteration, decoupled from rendering-variant text formatting"

requirements-completed: [TEST-03, TEST-04]

duration: ~12min
completed: 2026-04-27
---

# Phase 10 Plan 06: Gap Group A Closure - Parallelism + Spec Assertions Summary

**Four atomic edits land Gap Group A's full closure: workers: 1 in playwright.config.ts (realising CONTEXT D-07 intent), watchlist-panel-scoped Select-button locators in 01-fresh-start, hardcoded $10,000.00 pre-trade assertion dropped from 03-buy, and post-sell qty assertion converted to a relative `postBuyQty - 1` delta in 04-sell. Together these address all 8 of 9 VERIFICATION.md Gap Group A failures; Plan 10-07 lands Gap Group B (tooltip dismissal in 05-portfolio-viz) and owns the final 21/21 canonical-command harness gate.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-27T18:55:00Z (approx)
- **Completed:** 2026-04-27T19:07:00Z (approx)
- **Tasks:** 4
- **Files modified:** 4 (all under test/)

## Accomplishments

- **Task 1: workers: 1 in playwright.config.ts.** Replaced `workers: 3` with `workers: 1`. Rewrote the parallelism comment block from the original (broken) attempt to realise D-07 wording with workers: 3 + fullyParallel: false to a fresh comment that accurately describes the realised single-worker serialisation across all 21 (spec, project) pairs. Preserved fullyParallel: false (defensive no-op when workers=1) and all three browser projects.
- **Task 2: watchlist-panel-scoped Select-ticker locators in 01-fresh-start.** Wrapped both Select-button locators (the SEED_TICKERS for-loop and the AAPL streaming-proof row) in `page.getByTestId('watchlist-panel')` so they resolve only against the watchlist DOM region, not the positions table. Eliminates the latent collision risk if any spec ahead of 01-fresh-start in the serial schedule creates a position whose ticker is in the seed (NVDA from 03-buy, JPM from 04-sell, META from 05-portfolio-viz, AMZN from 06-chat all collide with the seed watchlist). Header cash $10,000.00 assertion preserved (valid because 01-fresh-start runs first under workers: 1) and em-dash streaming-proof assertion preserved.
- **Task 3: Hardcoded $10,000.00 pre-trade assertion dropped from 03-buy.** Removed the absolute `expect(getByTestId('header-cash')).toHaveText('$10,000.00')` pre-trade sanity (and its 3-line comment block). Replaced with a single one-line comment explaining the deliberate omission. The post-trade `cashAmount < 10_000` relative assertion is sufficient and survives any prior-state cash debits.
- **Task 4: Relative-delta qty assertion in 04-sell.** Replaced the absolute regex assertion `toHaveText(/^\s*1(?:\.0+)?\s*$/)` on the JPM qty cell with an `expect.poll`-based relative-delta assertion: capture the post-buy JPM qty (after the buy of 2 lands) as `postBuyQty`, then assert `expect.poll(...).toBe(postBuyQty - 1)`. Moved the jpmRow / jpmQty locator declarations up so they are available for both the post-buy snapshot and the final assertion.

## Task Commits

Each task was committed atomically (sequential mode on `finally-gsd`, normal git commits with hooks):

1. **Task 1: workers=1 in playwright.config.ts** - `491e6ff` (test)
2. **Task 2: scope Select-button locators to watchlist-panel** - `761d3a6` (test)
3. **Task 3: drop hardcoded $10k pre-trade assertion in 03-buy** - `3bb6105` (test)
4. **Task 4: relative-delta qty assertion in 04-sell** - `ee45f65` (test)

## Files Modified

- `test/playwright.config.ts` — workers: 1 (was 3); rewritten parallelism comment block describing realised single-worker serialisation; fullyParallel: false preserved; three browser projects preserved.
- `test/01-fresh-start.spec.ts` — both Select-button locators (SEED_TICKERS loop + aaplRow) scoped to `page.getByTestId('watchlist-panel')`; header-cash $10,000.00 assertion preserved; em-dash streaming-proof assertion preserved.
- `test/03-buy.spec.ts` — pre-trade `$10,000.00` cash assertion + 3-line comment removed; replaced with one-line explanatory comment; NVDA buy interaction, positions-table scoping, post-trade relative cash assertion preserved.
- `test/04-sell.spec.ts` — final assertion replaced with `expect.poll(...).toBe(postBuyQty - 1)`; jpmRow / jpmQty / postBuyQtyText / postBuyQty locator + snapshot block moved between the post-buy visibility wait and the sell action; absolute regex pattern removed; buy-2 / sell-1 interactions and column-order rationale preserved.

Diff stat across the four files: 4 files changed, 41 insertions(+), 24 deletions(-).

## Decisions Made

- **Option (a) workers: 1 over (b/c/d).** The verifier's "missing" list enumerated four possible fixes: (a) workers: 1 to serialise everything, (b) workers: 3 + project-level fullyParallel: false (Playwright doesn't support per-project worker caps so this is not actually achievable as CONTEXT D-07 worded), (c) per-spec containers via `compose run` orchestration (heaviest), (d) move all UI-mutation specs into a single sharded file. Picked (a) - the simplest path. Runtime cost is irrelevant for a single-user demo project; reproducible green is the priority. Plan 10-07 will run the canonical-command harness with this config to confirm the green-gate.
- **Drop pre-trade $10k assertion entirely instead of conditionally branching.** Even under workers: 1 (where the assertion would technically hold for 03-buy because 03-buy runs after 01/02 only and 02 is REST-only), the absolute pre-trade sanity is fragile noise: the post-trade relative `< 10_000` check is sufficient and would catch any regression where the trade fails to debit cash. Keeping a hardcoded $10k pre-trade assertion would couple the test to schedule details that can shift without breaking semantics.
- **expect.poll over toHaveText regex for 04-sell qty.** `toHaveText` with the regex `/^\s*1(?:\.0+)?\s*$/` would still work under workers: 1, but couples the assertion to text-rendering format. expect.poll evaluates a numeric callback (`parseFloat(...)`) on every iteration until it matches `postBuyQty - 1` numerically. This is robust against any prior state on JPM (the buy adds exactly 2, the sell removes exactly 1, so post-sell == post-buy - 1) AND format-agnostic (1, 1.0, 1.00 all parse to the same Number).
- **Harness gate run is owned by Plan 10-07.** This SUMMARY documents the spec/config edits only. Plan 10-07 lands the Gap Group B fix (Recharts tooltip dismissal in 05-portfolio-viz) and owns the canonical `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` 21/21 green-gate run.

## Deviations from Plan

### Acceptance-Criteria Grep Inconsistencies (Documented, Not Auto-Fixed)

Two of the plan's per-task acceptance-criteria grep checks are internally inconsistent with the prescribed `<action>` code blocks. The actions land the prescribed code; the grep gates do not match it cleanly. Documented here for the verifier so the inconsistency is visible without being mistaken for a fix-the-code signal.

**1. Task 1 acceptance-criterion #4: `grep -c 'workers: 3' test/playwright.config.ts` outputs `0`**

The plan's prescribed comment block contains the literal sentence "Original config used workers: 3 + fullyParallel: false in an attempt to realise...". `grep -c 'workers: 3'` therefore matches 1 line (the comment text), not 0 as the criterion expects. The criterion is logically inconsistent with the prescribed comment block; the prescribed comment text was followed verbatim. The intent of the criterion (the active config setting is no longer `workers: 3`) IS satisfied: `grep -c '^\s*workers:\s*3\b'` returns 0.

**2. Task 4 acceptance-criterion #2 / #3: `grep -c 'const postBuyQty' test/04-sell.spec.ts` outputs `1` AND `grep -c 'expect.poll' test/04-sell.spec.ts` outputs `1`**

The prescribed code block declares both `const postBuyQtyText = await jpmQty.innerText();` and `const postBuyQty = parseFloat(postBuyQtyText.trim());` - both lines start with `const postBuyQty`, so `grep -c 'const postBuyQty'` returns 2, not 1. Likewise `expect.poll` is split across two lines per the prescribed action code (`await expect\n  .poll(`), so single-line grep returns 0; multi-line grep (or PCRE `grep -Pzo`) confirms `expect.poll` is present once. Both intents (post-buy qty snapshot landed; poll-based assertion present) are satisfied.

### Auto-fixed Issues

None. The four tasks landed exactly as written in the plan's `<action>` blocks.

## Cross-cutting Verification

- `git diff --stat HEAD~4 HEAD -- test/playwright.config.ts test/01-fresh-start.spec.ts test/03-buy.spec.ts test/04-sell.spec.ts` shows exactly 4 files changed, no other test files touched. Verified via `git diff --name-only HEAD~4 HEAD` returning the 4 expected paths only.
- `cd test && npx playwright test --list 2>&1 | tail -1` returns `Total: 21 tests in 7 files` - all specs still discovered across all 3 browser projects, no parse-time breakage.

## Issues Encountered

None. Sequential mode on the main working tree (no worktree isolation), normal commits with hooks, four atomic per-task commits, all per-task verify gates green. The plan's per-task `<action>` blocks were prescriptive enough that no auto-fix deviations were required.

## User Setup Required

None. The harness gate run is owned by Plan 10-07; this plan only landed source edits.

## Next Phase Readiness

- **Gap Group A spec/config edits landed; harness gate run by 10-07.** Plan 10-07 will land the Gap Group B fix (Recharts tooltip dismissal in 05-portfolio-viz before tab-pnl click) and run the canonical command. Expected outcome of 10-07's gate: 21 of 21 (spec, project) pairs pass green on chromium + firefox + webkit, closing ROADMAP Phase 10 SC#3.
- **No follow-up required from this plan.** The four files are committed; the next plan in the sequential dependency (10-07) can proceed.

## Self-Check: PASSED

- [x] `test/playwright.config.ts` exists; `grep -E '^\s*workers:\s*1\b'` matches at line 31; `grep -E '^\s*workers:\s*3\b'` returns 0; D-07 corrected comment block landed.
- [x] `test/01-fresh-start.spec.ts` exists; `grep -c "getByTestId('watchlist-panel')"` returns 2 (both Select-button locators scoped); header-cash $10,000.00 assertion preserved at line 34; em-dash streaming-proof assertion preserved at line 41.
- [x] `test/03-buy.spec.ts` exists; `grep -c '\$10,000.00'` returns 0; `grep -c 'No pre-trade cash assertion'` returns 1; post-trade relative `cashAmount < 10_000` assertion preserved at line 38.
- [x] `test/04-sell.spec.ts` exists; `grep -c 'postBuyQty - 1'` returns 1; old absolute regex pattern absent; multi-line `await expect\n  .poll(` present; both buy-2 and sell-1 interactions preserved.
- [x] All 4 task commits exist on `finally-gsd`: `491e6ff` (Task 1), `761d3a6` (Task 2), `3bb6105` (Task 3), `ee45f65` (Task 4).
- [x] `git diff --name-only HEAD~4 HEAD` returns exactly the 4 expected paths.
- [x] `cd test && npx playwright test --list 2>&1 | tail -1` reports `Total: 21 tests in 7 files`.

---
*Phase: 10-e2e-validation*
*Plan: 10-06*
*Completed: 2026-04-27*
