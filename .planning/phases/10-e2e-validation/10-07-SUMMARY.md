---
phase: 10-e2e-validation
plan: 07
subsystem: testing
tags: [playwright, e2e, recharts-tooltip, gap-closure, partial, superseded]

requires:
  - phase: 10-e2e-validation
    provides: 7 spec files + harness foundation + Gap Group A closure (Plans 10-00..10-06)
  - phase: 10-e2e-validation
    provides: 10-VERIFICATION.md (initial pass) listing Gap Group B (tooltip subtree intercepts tab-pnl click)

provides:
  - "test/05-portfolio-viz.spec.ts: dismissChartTooltip helper (Escape + page.mouse.move(0,0)) called immediately before tab-pnl click — preserved as belt-and-suspenders even after the actual root cause was identified by 10-08"

affects:
  - 10-08 (took ownership of the canonical harness 21/21 green gate that this plan abandoned per failure protocol)
  - 10-09 (will close the corrected Mode A diagnosis once 10-08's verifier pass refreshes VERIFICATION.md)

tech-stack:
  added: []
  patterns:
    - "page.keyboard.press('Escape') + page.mouse.move(0, 0) helper to attempt dismissal of a Recharts hover tooltip before a sibling click (note: 10-08's harness evidence showed this pattern is NOT what closes the failure on this codebase — the actual failure was a layout/volume issue, not a tooltip lifecycle issue. The helper is harmless and stays in place.)"

key-files:
  created: []
  modified:
    - test/05-portfolio-viz.spec.ts

key-decisions:
  - "Task 1 was completed in commit 9924ccc (test(10-07): replace mouse-move-only tooltip dismissal with Escape helper) before Task 2 (the canonical harness gate) ran. Task 1 added a `dismissChartTooltip` helper that performs Escape + mouse displacement, called immediately before the tab-pnl click in test/05-portfolio-viz.spec.ts."
  - "Task 2 (canonical harness 21/21 green gate) FAILED on the first attempted run — 5 hard failures + 2 flaky retries instead of 21 passed. Per Plan 10-07's failure protocol ('do NOT mark the task done. Inspect /tmp/phase10-gap-closure-harness.log for the failed (spec, project) pair(s)') the task was abandoned and a verifier re-pass was triggered."
  - "The verifier re-pass produced commit 4f690e6 (docs(phase-10): refresh VERIFICATION after 10-06 + 10-07 partial — Mode A/B/C identified). 10-VERIFICATION.md was refreshed with three new diagnoses (Modes A, B, C). 10-VERIFICATION.md line 59 explicitly recorded: '10-07 Task 2 (canonical harness gate) FAILED and was abandoned per failure protocol; 10-07-SUMMARY.md was never written.'"
  - "Plan 10-08 was created with `depends_on: [10-06, 10-07]` and explicit objective text: 'own the canonical harness 21/21 green gate that Plan 10-07 abandoned.' 10-08 reverses the original wave order de facto by being the gate-running plan."
  - "Orchestrator decision (the run that wrote this SUMMARY): execute 10-08 first (out of stated wave order) because 10-07 Task 2 cannot pass until 10-08 lands its source edits. After 10-08's partial completion, this 10-07 SUMMARY is hand-written to formalise the supersession and unblock phase verification — which would otherwise see 10-07 as 'incomplete' indefinitely."
  - "The dismissChartTooltip helper from Task 1 stays in place despite 10-08's harness evidence showing the actual interceptor is the Terminal.tsx right-column wrapper (not the Recharts tooltip). Removing the helper is out of scope for this SUMMARY; if and when 10-09 lands, the cleanup decision is owned by that plan."

patterns-established:
  - "When an in-plan verification gate fails and a verifier re-pass refreshes the failure shape, the originally-blocked plan does NOT silently retry. A fresh gap-closure plan (with explicit `depends_on:` and objective text re-stating the gate ownership) supersedes the abandoned task. The original plan's SUMMARY is then hand-written by the orchestrator to record what landed (Task 1) and what was superseded (Task 2)."

requirements-completed: []
requirements-progressed: [TEST-03, TEST-04]

duration: ~6min (Task 1 only; Task 2 abandoned)
completed: 2026-04-27
status: superseded
---

# Phase 10 Plan 07: Gap Group B Closure (Partial — Superseded by 10-08) Summary

**Task 1 (Escape + mouse-move tooltip-dismissal helper in test/05-portfolio-viz.spec.ts) landed in commit 9924ccc; Task 2 (canonical harness 21/21 green gate) failed on its first attempted run and was abandoned per the plan's own failure protocol. The verifier re-pass (commit 4f690e6) refreshed 10-VERIFICATION.md with three new failure mode diagnoses (A/B/C); a successor plan 10-08 was created with explicit objective text taking ownership of the gate. This SUMMARY formalises the supersession so the phase can advance through verifier and onward.**

## Performance

- **Duration:** ~6 min (Task 1 only — single file edit + commit)
- **Started:** 2026-04-27T19:08:00Z (approx — between 10-06 commits and verifier re-pass)
- **Completed:** 2026-04-27T19:14:00Z (approx — Task 1 commit 9924ccc lands)
- **Tasks attempted:** 2
- **Tasks completed:** 1 of 2 (Task 1 committed; Task 2 abandoned per failure protocol)
- **Files modified:** 1

## Accomplishments

- **Task 1: dismissChartTooltip helper in test/05-portfolio-viz.spec.ts (commit 9924ccc — test(10-07): replace mouse-move-only tooltip dismissal with Escape helper).** Added a `dismissChartTooltip` helper inside the test function (immediately after `page.goto('/')`) that performs Escape key dispatch + `page.mouse.move(0, 0)` displacement. Replaced the previous mouse-move-only mitigation that 10-04's verifier had identified as insufficient. Helper called on the line immediately before `getByTestId('tab-pnl').click()` so the dismissal happens at the latest possible moment before the click. META ticker preserved per CONTEXT D-08; heatmap and P&L visibility assertions preserved; no `page.waitForTimeout` anti-pattern introduced.

## Task Commits

1. **Task 1: Escape + mouse-move tooltip dismissal helper** — `9924ccc` (test) — committed.
2. **Task 2: canonical harness 21/21 green gate** — NOT COMMITTED. The harness ran (capturing `/tmp/phase10-gap-closure-harness.log`) but exited 1 with 5 hard failures + 2 flaky retries. Per Plan 10-07's own failure protocol, Task 2 was abandoned and the verifier re-ran.

## Files Modified

- `test/05-portfolio-viz.spec.ts` — `dismissChartTooltip` helper added at lines 26-29 (Escape + mouse-move-to-(0,0)); call site added on the line immediately before the tab-pnl click (line 49). Earlier mouse-move-only mitigation removed. META ticker, positions-table scoped Select META wait, heatmap visibility assertion, P&L visibility assertions all preserved unchanged.

## Decisions Made

See `key-decisions` in frontmatter for the full chain. The decisive one is: **Task 2 was abandoned, not retried.** The verifier re-pass (commit 4f690e6) replaced this plan's gate ownership with 10-08; this SUMMARY records the partial completion honestly so phase verification can proceed without stalling on a never-completed plan.

## Deviations from Plan

### Acceptance-criteria gap that surfaced during Task 2

- Plan 10-07's Task 2 acceptance criteria asserted `21 passed`. Actual harness reported `14 passed / 5 failed / 2 flaky` (per `/tmp/phase10-gap-closure-harness.log`).
- 10-VERIFICATION.md commit 4f690e6 captured the corrected diagnosis: 3 failures from Mode A (Recharts heatmap tooltip — what 10-VERIFICATION.md believed at the time, later corrected by 10-08), 2 failures from Mode B (cross-project SQLite leak makes `$10,000.00` cash assertion fragile), 2 flaky from Mode C (postBuyQty snapshot races React Query refetch).
- The `dismissChartTooltip` helper that Task 1 landed remained insufficient against Modes A/B/C — confirming the original 10-VERIFICATION.md analysis that simple mitigation was not enough. (10-08 would later prove that even the production-side Recharts Tooltip pointer-events fix is not the actual root cause; the real interceptor is a layout overlap from Terminal.tsx. The helper from this plan is harmless and stays in place.)

### Auto-fixed Issues

None — Task 1 landed exactly as written in the plan's `<action>` block.

## Issues Encountered

### Task 2 abandoned per failure protocol

The plan's own `<action>` block for Task 2 stated: "If non-zero, do NOT mark the task done... If a failure is in a file that 10-06 or 10-07 was supposed to fix, that means the prior task's edits did not actually land — re-read the offending file via the read_first protocol and verify the expected changes are present at the expected lines... If a failure surfaces in a file NEITHER plan touched, that is a NEW gap and should be surfaced via VERIFICATION.md update, not silently retried."

The harness reported failures in:
- `test/05-portfolio-viz.spec.ts` (this plan's file — Task 1 changes were verified present at lines 26-29 and 49; the helper executed but the tooltip-pin failure persisted, indicating the diagnosis was wrong; surfaced as a new gap)
- `test/01-fresh-start.spec.ts` (10-VERIFICATION.md called this Mode B — surfaced as a new gap)
- `test/04-sell.spec.ts` (10-VERIFICATION.md called this Mode C — surfaced as a new gap)

The verifier re-ran on the refreshed harness log and produced commit 4f690e6 (`docs(phase-10): refresh VERIFICATION after 10-06 + 10-07 partial — Mode A/B/C identified`). 10-08-PLAN.md was then written to address Modes A/B/C with its own explicit gate-ownership clause.

### Why this SUMMARY is hand-written rather than executor-produced

Plan 10-07 has only two tasks; Task 1 is done and Task 2 is permanently superseded. An executor agent re-spawned on this plan would attempt Task 2 again, which cannot succeed without 10-08's source edits in place. After 10-08 landed Tasks 1-3 (commits a149480, 0a58eb9, c53810f), the orchestrator hand-wrote this SUMMARY to honestly record that:
- Task 1 landed in 9924ccc and is preserved as belt-and-suspenders.
- Task 2 was abandoned per failure protocol and ownership of the canonical harness gate transferred to 10-08.
- This plan is `status: superseded`, not `status: complete` — the harness gate is owned by 10-08 (and now, after 10-08's partial completion, by 10-09 once it is created).

## User Setup Required

None.

## Next Phase Readiness

- **Phase 10 SC#3 NOT MET by this plan.** The harness gate was abandoned. See `10-08-SUMMARY.md` for the next iteration's outcome (Modes B and C closed cleanly, Mode A misdiagnosed and pending corrective 10-09 plan).
- **dismissChartTooltip helper preserved.** Future plans may keep, refine, or remove it once the corrected Mode A root cause is addressed.

## Self-Check: PARTIAL — SUPERSEDED

- [x] `test/05-portfolio-viz.spec.ts` contains `dismissChartTooltip` helper at lines 26-29 (verified by `grep -c 'dismissChartTooltip' test/05-portfolio-viz.spec.ts` → 2: definition + call site).
- [x] `test/05-portfolio-viz.spec.ts` contains `page.keyboard.press('Escape')` (verified by `grep -c "page.keyboard.press('Escape')" test/05-portfolio-viz.spec.ts` → 1).
- [x] `test/05-portfolio-viz.spec.ts` contains `page.mouse.move(0, 0)` as part of the helper body (verified by `grep -c 'page.mouse.move(0, 0)' test/05-portfolio-viz.spec.ts` → 1).
- [x] Task 1 commit `9924ccc` exists on `finally-gsd` (verified by `git log --oneline | grep '9924ccc'`).
- [ ] Task 2 canonical harness 21/21 green — NOT COMPLETED. Abandoned per failure protocol. Ownership of the gate transferred to 10-08 via that plan's explicit objective text.
- [x] 10-VERIFICATION.md commit 4f690e6 records this plan's partial state: line 59 says "10-07 Task 2 (canonical harness gate) FAILED and was abandoned per failure protocol; 10-07-SUMMARY.md was never written" — this SUMMARY corrects the second clause; the first clause stands.

---
*Phase: 10-e2e-validation*
*Plan: 10-07*
*Status: superseded — Task 1 landed in 9924ccc; Task 2 abandoned and gate ownership transferred to 10-08 per 10-VERIFICATION.md commit 4f690e6 + 10-08-PLAN.md objective*
*Completed: 2026-04-27*
