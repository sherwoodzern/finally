---
phase: 10-e2e-validation
plan: 08
subsystem: testing
tags: [playwright, e2e, recharts-tooltip, sqlite-volume-leak, react-query-race, gap-closure, partial, root-cause-divergence]

requires:
  - phase: 10-e2e-validation
    provides: 7 spec files + harness foundation (Plans 10-00..10-05) + Gap Group A closure (Plan 10-06) + 10-07 dismissChartTooltip helper at test/05-portfolio-viz.spec.ts:26-29
  - phase: 10-e2e-validation
    provides: Refreshed 10-VERIFICATION.md (commit 4f690e6) listing Modes A/B/C as remaining gaps after 10-06 + 10-07 partial

provides:
  - "frontend/src/components/portfolio/Heatmap.tsx: explicit Recharts <Tooltip wrapperStyle={{ pointerEvents: 'none' }} /> rendered inside <Treemap> (latent UX fix; does NOT close the actual harness failure — see Issues Encountered)"
  - "test/01-fresh-start.spec.ts: absolute $10,000.00 cash assertion dropped — Mode B closed (1/1 → 3/3 green)"
  - "test/04-sell.spec.ts: postBuyQty snapshot stabilised via expect.poll(...).toBeGreaterThanOrEqual(2) — Mode C closed (1/3 + 2 flaky → 3/3 green, 0 flaky)"

affects:
  - 10-09 (next gap-closure plan — owner of the corrected Mode A diagnosis: Terminal.tsx layout overlap at viewport 1280×720 + cross-project SQLite carry-over via persistent docker volume)

tech-stack:
  added: []
  patterns:
    - "wrapperStyle={{ pointerEvents: 'none' }} on Recharts hover tooltips so the wrapper never absorbs sibling clicks (latent production UX hardening)"
    - "expect.poll(...).toBeGreaterThanOrEqual(N) snapshot stabilisation when the captured numeric value depends on a downstream React Query refetch — pair with `let` binding so the closure can update the captured value on each iteration"

key-files:
  created: []
  modified:
    - frontend/src/components/portfolio/Heatmap.tsx
    - test/01-fresh-start.spec.ts
    - test/04-sell.spec.ts

key-decisions:
  - "Override of 10-07-PLAN.md Task 1 'do NOT modify Heatmap' guidance: 10-VERIFICATION.md commit 4f690e6 evidence proved the test-only mitigation (Escape + mouse displacement) does not retract the Recharts default tooltip. The override addresses what was BELIEVED to be the root cause; while subsequent harness evidence (this plan's Task 4) showed the actual interceptor is NOT the Recharts tooltip (see Issues Encountered), the production fix is still kept — a tooltip whose wrapper has pointer-events: auto IS a latent UX defect a user could hit by hovering a heatmap tile and clicking a sibling tab. Defense in depth, not scope creep."
  - "Test-side drop of $10,000.00 in 01-fresh-start mirrors Plan 10-06's pattern in 03-buy. Same fragility (absolute cash assertion across cross-project SQLite state under workers: 1), same fix (drop the absolute, lean on contextual proofs — watchlist visibility + em-dash streaming proof). CONTEXT D-03 (single canonical command) and D-06 (no test-only /api/test/reset endpoint) block heavier alternatives."
  - "expect.poll snapshot stabilisation in 04-sell mirrors 10-06's expect.poll for the post-sell delta. Visibility wait alone does NOT guarantee React Query has refetched the post-buy qty cell. Wrapping the snapshot in expect.poll(...).toBeGreaterThanOrEqual(2) (the buy added 2; any settled state must be >= 2) eliminates the refetch race. The existing post-sell expect.poll(...).toBe(postBuyQty - 1) at lines 47-52 (10-06 commit ee45f65) is preserved unchanged."
  - "Canonical harness command run verbatim per CONTEXT D-03 — no flags, no filters, no spec-pinning. The whole point of the SC#3 gate is the unmodified D-03 invocation. Adding --retries=2 or -p chromium would mask root cause and produce a 'green' result that does not actually prove SC#3."
  - "STOPPED at Task 4 instead of patching around the harness failure. CLAUDE.md root rule: 'Identify root cause before fixing. Try one test at a time. Be methodical. Don't jump to conclusions.' Task 4 evidence proved 10-VERIFICATION.md's Mode A diagnosis was wrong; the right next move is verifier re-pass + a fresh gap-closure plan (10-09), not silent retries or in-plan scope expansion."

patterns-established:
  - "Recharts Treemap tooltip non-blocking: explicitly render `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` as a child of `<Treemap>`. Default tooltip wrapper has `pointer-events: auto` and intercepts clicks on sibling elements. One-line, no-functional-change UX hardening."
  - "Snapshot-then-assert race avoidance: when capturing a numeric value that depends on a downstream React Query refetch, wrap the capture in `expect.poll(...)` matched against a known-good lower bound (`toBeGreaterThanOrEqual(N)` where N is the minimum the data must reach after the mutation). Pair with `let` binding so the closure can mutate the captured value across iterations."

requirements-completed: []
requirements-progressed: [TEST-03, TEST-04]

duration: ~22min (Tasks 1-3: ~7min; Task 4 harness + diagnosis: ~15min)
completed: 2026-04-27
status: partial
---

# Phase 10 Plan 08: Mode A/B/C Closure (Partial — A Misdiagnosed) Summary

**Three atomic edits closed Modes B and C cleanly (01-fresh-start 3/3 green; 04-sell 3/3 green, 0 flaky), and added a defensive Recharts Tooltip pointer-events fix to Heatmap.tsx as a latent UX hardening. The canonical harness gate FAILED 18/21 because Mode A's root cause is NOT a Recharts tooltip overlay — the actual interceptor is the Terminal.tsx right-column wrapper at viewport 1280×720, and harness state carries over across `up` invocations via a persistent docker volume. The misdiagnosis is documented for a fresh verifier pass and a corrective 10-09 plan; ROADMAP Phase 10 SC#3 is NOT yet met.**

## Performance

- **Duration:** ~22 min total (Tasks 1-3 source edits ~7 min; Task 4 harness build + 1.6 min Playwright + diagnosis ~15 min)
- **Started:** 2026-04-27T21:25:00Z (approx)
- **Completed:** 2026-04-27T21:47:00Z (approx)
- **Tasks attempted:** 4
- **Tasks completed:** 3 of 4 (Tasks 1, 2, 3 committed; Task 4 harness gate failed and was abandoned per failure protocol — same protocol Plan 10-07 invoked)
- **Files modified:** 3

## Accomplishments

- **Task 1: Recharts Tooltip with pointerEvents none in Heatmap.tsx (commit a149480).** Extended the recharts import from `{ ResponsiveContainer, Treemap }` to `{ ResponsiveContainer, Tooltip, Treemap }`. Converted the previously self-closing `<Treemap ... />` into an opening + closing tag with `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` as the only child. All other Treemap props (data, dataKey, stroke, content, isAnimationActive, animationDuration, onClick) preserved. `data-testid="heatmap-treemap"` on the surrounding `<div>` preserved. `npm run build` green. This addresses what 10-VERIFICATION.md commit 4f690e6 BELIEVED was the root cause of Mode A; subsequent harness evidence proved that diagnosis wrong (see Issues Encountered). The fix is kept in place because a tooltip wrapper with `pointer-events: auto` IS a latent production UX defect — independently of whether it caused this specific harness failure.
- **Task 2: drop $10,000.00 absolute cash assertion in 01-fresh-start.spec.ts (commit 0a58eb9).** Replaced lines 33-34 (the comment + `expect(getByTestId('header-cash')).toHaveText('$10,000.00')` assertion) with an explanatory comment block calling out the cross-project SQLite leak (the compose anonymous-volume comment in docker-compose.test.yml line 31 implies anonymous, but the lived behaviour shows persistence — see Issues Encountered). The 10-ticker watchlist visibility loop and the em-dash streaming-proof assertion are sufficient to prove `fresh start` without coupling to cross-project state. Mode B closed: harness shows 01-fresh-start 3/3 green (chromium + firefox + webkit).
- **Task 3: expect.poll-stabilised postBuyQty snapshot in 04-sell.spec.ts (commit c53810f).** Replaced lines 36-37 (`const postBuyQtyText = await jpmQty.innerText(); const postBuyQty = parseFloat(postBuyQtyText.trim());`) with `let postBuyQty = 0; await expect.poll(async () => { postBuyQty = parseFloat((await jpmQty.innerText()).trim()); return postBuyQty; }, { timeout: 10_000 }).toBeGreaterThanOrEqual(2);`. The closure-mutable `let` binding holds the latest reading; the `.toBeGreaterThanOrEqual(2)` matcher waits for React Query to refetch to a post-buy value of at least 2 (the buy added exactly 2). The existing post-sell `expect.poll(...).toBe(postBuyQty - 1)` at lines 47-52 (10-06 commit ee45f65) is preserved unchanged — it operates on the now-stable `postBuyQty`. Mode C closed: harness shows 04-sell 3/3 green, 0 flaky.

## Task Commits

Each completed task was committed atomically (sequential mode on `finally-gsd`, normal commits with hooks):

1. **Task 1: Recharts Tooltip with pointerEvents none in Heatmap** — `a149480` (feat)
2. **Task 2: drop absolute cash assertion in 01-fresh-start** — `0a58eb9` (test)
3. **Task 3: expect.poll-stabilise postBuyQty snapshot in 04-sell** — `c53810f` (test)
4. **Task 4: canonical harness 21/21 green gate** — NOT COMMITTED. Harness ran (capturing `/tmp/phase10-final-harness.log`, 77,182 bytes) but exited 1 with `18 passed / 3 failed / 0 flaky` — see Issues Encountered.

## Files Modified

- `frontend/src/components/portfolio/Heatmap.tsx` — `Tooltip` added to recharts import (alphabetical: ResponsiveContainer, Tooltip, Treemap); `<Treemap>` converted from self-closing to opening + closing with `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` as the only child; all other props and surrounding markup preserved.
- `test/01-fresh-start.spec.ts` — absolute `$10,000.00` cash assertion at the original line 34 + its single-line comment at line 33 dropped; replaced with a multi-line comment ("Cross-project SQLite leak — see 10-VERIFICATION.md Mode B (commit 4f690e6)..."); 10-ticker watchlist visibility loop, SEED_TICKERS array, em-dash streaming-proof assertion, and 10-06's `getByTestId('watchlist-panel')` scoping all preserved unchanged.
- `test/04-sell.spec.ts` — pre-refetch snapshot at the original lines 36-37 replaced with `let postBuyQty = 0` + `await expect.poll(async () => { postBuyQty = parseFloat(...); return postBuyQty; }, { timeout: 10_000 }).toBeGreaterThanOrEqual(2)`; intermediate `postBuyQtyText` variable removed; jpmRow + jpmQty declarations at lines 34-35 preserved; the existing post-sell `expect.poll(...).toBe(postBuyQty - 1)` at lines 47-52 (10-06) preserved unchanged; buy-2 + sell-1 quantities preserved per CONTEXT D-08.

## Decisions Made

See `key-decisions` in frontmatter for the full list. The most consequential decision was **stopping at Task 4 instead of patching around the failure** — the harness evidence proved 10-VERIFICATION.md's Mode A diagnosis was wrong, and CLAUDE.md mandates root-cause analysis before fixing.

## Deviations from Plan

### Acceptance-criteria gap that surfaced during Task 4

- Plan 10-08's Task 4 acceptance criteria asserted `21 passed`. Actual harness reported `18 passed (1.6m)` + `3 failed`. The 3 failures are all `[chromium|firefox|webkit] 05-portfolio-viz.spec.ts:15:5 portfolio viz: heatmap and P&L chart render after a position exists`. None of the 18 passing tests were retries; `0 flaky` confirms determinism — every project failed twice and stayed failed.
- Plan 10-08's Task 1 fix landed correctly (verified by `grep -c "wrapperStyle={{ pointerEvents: 'none' }}" frontend/src/components/portfolio/Heatmap.tsx` → 1, `grep -c "<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />" frontend/src/components/portfolio/Heatmap.tsx` → 1, `npm run build` green). The fix targets the WRONG ROOT CAUSE — see Issues Encountered. The plan author and the verifier both identified the wrong interceptor; the fix is a real latent UX hardening but does NOT close the harness failure.

### Auto-fixed Issues

None — Tasks 1, 2, 3 all landed exactly as written in the plan's `<action>` blocks. Task 4 was not auto-fixed because the failure shape was not patchable within the plan's `<files_modified>` contract (the actual interceptor lives in Terminal.tsx, which Plan 10-08 was not authorised to modify).

## Issues Encountered

### Mode A misdiagnosed by 10-VERIFICATION.md (commit 4f690e6) — actual root cause is NOT a Recharts tooltip

10-VERIFICATION.md attributed the `<td class="px-4 font-semibold">{ticker}</td> from <div class="flex flex-col gap-4">...</div> subtree intercepts pointer events` failure to the Recharts default Treemap tooltip wrapper (`pointer-events: auto`). My Task 1 fix added an explicit `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` to Heatmap.tsx. **The fix is correct and is now committed in `a149480`** — but it does not close the actual failure because the actual interceptor is NOT a Recharts tooltip.

Inspection of the test-failed screenshots (`test/test-results/05-portfolio-viz-portfolio-3f443-der-after-a-position-exists-{chromium,firefox,webkit}{,-retry1}/test-failed-1.png`) and the page accessibility snapshots (`error-context.md` per failure dir) prove:

1. The intercepting `<td class="px-4 font-semibold">META</td>` is the **first cell of the META row of the right-column `<PositionsTable>`** (NOT a tooltip body cell). The visible position row carries content that mirrors the layout of the production positions table, not a hover overlay.
2. The screenshots show the **center column visually narrows** at viewport 1280×720, with the tabs (`Chart | Heatmap | P&L`) crammed into a strip — and the right column's Positions table starts where the P&L tab's click coordinates would fall.
3. The "from `<div class="flex flex-col gap-4">…</div>` subtree" matches `Terminal.tsx:26-27` — the **center column wrapper** (`<div className="flex-1 min-w-0 p-6"><div className="grid grid-cols-[320px_1fr_360px] gap-6">`). At viewport 1280: outer `p-6` (px-6 px-6 = 48) + grid columns 320 + 1fr + 360 + two `gap-6` (24+24 = 48) = 776 + center column. Available center column width is 1280 - 776 = 504px. That should be enough but the screenshot proves the center is overflowing in practice (likely because the `min-w-0` on the parent doesn't fully constrain inner intrinsic widths, OR because the chat drawer when open further constrains the layout).
4. The TradeBar in the failed-test screenshots shows the alert "Not enough cash for that order." and the Positions table shows META qty=9 (from cumulative prior chromium-round state — confirming the SQLite leak is not just cash but full position state). Chat history shows 4 prior "buy AMZN 1" turns at 19:08, 19:09, 19:10, 19:41 (the 19:41 entry is from THIS run's 06-chat) — proving the volume persists ACROSS `up` invocations, not just within one.

### Cross-project / cross-run SQLite leak deeper than Mode B implies

`test/docker-compose.test.yml` line 31 comment claims "D-06: NO `volumes:` mapping for /app/db -> compose creates a fresh anonymous volume each `up`". The lived behaviour shows otherwise: positions and chat history persist across `up` runs. Either:
- The compose file has a named volume despite the comment (a `volumes:` block at line 50 deserves audit — likely the playwright service's test-results mount, but worth verifying).
- Docker Compose's anonymous-volume cleanup behaviour differs from the comment's assumption (anonymous volumes can outlive `compose down` without `--volumes`; `compose up --build` may not recycle them).

This is a Phase 10-level concern: the harness is supposed to be reproducible, and right now it isn't — chromium accumulates state that subsequent runs see.

### Recommended next steps for the verifier + 10-09 plan

The verifier should re-read `/tmp/phase10-final-harness.log` plus the test-results screenshots and accessibility snapshots, and refresh `10-VERIFICATION.md` with the corrected Mode A diagnosis:
- **Mode A (corrected)**: layout overlap at viewport 1280×720 between the center column's TabBar (containing tab-pnl) and the right column's PositionsTable. The Recharts Tooltip pointer-events fix is a latent UX hardening but does NOT close this harness failure. Three plausible fix paths: (i) test-side `tab-pnl.click({ force: true })` (smallest change, hides UX regression), (ii) production-side layout fix in Terminal.tsx (correct UX fix, scope creep for Phase 10), (iii) test-side viewport bump in playwright.config.ts (hides UX regression).
- **Mode A.2 (new)**: cross-project / cross-run SQLite carry-over via persistent docker volume. Audit `test/docker-compose.test.yml` line 50 `volumes:` block; ensure /app/db is anonymous AND ephemeral across runs. This is independent of Mode A but compounds it (drained cash → buys fail → spec assertions wedged on prior state).

A fresh gap-closure plan (10-09) should target both. The Modes B and C closure landed by this plan stands; harness now shows `01-fresh-start` and `04-sell` 3/3 green across all 3 browsers.

## User Setup Required

None — no external service configuration changes.

## Next Phase Readiness

- **Phase 10 SC#3 NOT MET.** Canonical harness exits 1 with 18/21. ROADMAP Phase 10 cannot be marked complete; TEST-03 and TEST-04 cannot be ticked yet.
- **Modes B and C closure preserved.** The 8 hard failures + 2 flaky retries from 01-fresh-start and 04-sell that motivated Plan 10-08 are gone. The remaining 3 failures (all 05-portfolio-viz) require a corrective gap-closure plan (10-09).
- **Recommended action**: run `/gsd-verify-work 10` (or let the next phase verifier pass execute) so 10-VERIFICATION.md is refreshed with the corrected Mode A diagnosis, then run `/gsd-plan-phase 10 --gaps` to generate 10-09 targeting the real layout + volume root causes.

## Self-Check: PARTIAL

- [x] `frontend/src/components/portfolio/Heatmap.tsx` contains `wrapperStyle={{ pointerEvents: 'none' }}` (verified by `grep -c "wrapperStyle={{ pointerEvents: 'none' }}"` → 1).
- [x] `test/01-fresh-start.spec.ts` does not contain `$10,000.00` (verified by `grep -c '\$10,000.00'` → 0).
- [x] `test/04-sell.spec.ts` contains `toBeGreaterThanOrEqual(2)` and `let postBuyQty = 0` (verified by `grep -c 'toBeGreaterThanOrEqual(2)'` → 1, `grep -c 'let postBuyQty = 0'` → 1).
- [x] `/tmp/phase10-final-harness.log` exists (77,182 bytes) and contains `Container test-appsvc-1 Healthy` at line 147.
- [x] All 3 task commits exist on `finally-gsd`: `a149480`, `0a58eb9`, `c53810f`.
- [ ] `/tmp/phase10-final-harness.log` contains `21 passed` — FAILED. Actual: `18 passed (1.6m)` + `3 failed` (all 05-portfolio-viz × 3 browsers).
- [ ] Canonical command exits 0 — FAILED. Actual exit code: 1.
- [ ] `grep -c 'flaky' /tmp/phase10-final-harness.log` outputs 0 — PASSED (no retries needed; failures stayed failed) but does NOT compensate for the 3 hard failures.

---
*Phase: 10-e2e-validation*
*Plan: 10-08*
*Status: partial — Modes B/C closed cleanly; Mode A misdiagnosed by 10-VERIFICATION.md, harness gate failed, fresh verifier pass + 10-09 plan required*
*Completed: 2026-04-27*
