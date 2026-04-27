---
phase: 10-e2e-validation
verified: 2026-04-27T18:30:00Z
status: gaps_found
score: 2/3 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Running the full E2E pack is a single command and finishes green locally against the freshly built image, with reproducible results on repeat runs (ROADMAP SC#3)."
    status: failed
    reason: "Canonical harness exits 1 with 9 of 21 (spec, project) pairs failed (12 passed). Two distinct root causes: (a) cross-spec parallelism in playwright.config.ts contends on shared SQLite global state — cash balance and seed-watchlist tickers — causing 8 of the 9 failures; (b) 05-portfolio-viz click-timeout from Recharts hover tooltip intercepting pointer events, affecting all 3 browsers (1 of the 9 failures, distinct mode). Foundation HSTS rename (commit 22ac1a4) successfully unblocked Chromium/Firefox at navigation; failures now arise from spec design + parallelism configuration, NOT browser navigation."
    artifacts:
      - path: "test/playwright.config.ts"
        issue: "workers: 3 + fullyParallel: false — three concurrent worker processes pick up different spec files against the same backend SQLite. CONTEXT.md D-07 stated intent was 'workers: 1 within a Playwright project; cross-browser projects parallel'. The config comment claims D-08 ticker isolation prevents collisions, but that only protects per-ticker state — it does not protect shared global state (cash balance, default seed-watchlist tickers that ALSO get bought as positions, e.g. NVDA/JPM/META/AMZN are all in the seed watchlist)."
      - path: "test/01-fresh-start.spec.ts:27"
        issue: "`getByRole('button', { name: 'Select <ticker>' })` is unscoped. When 06-chat (or any other spec) runs concurrently and creates an AMZN position, the selector resolves to TWO elements (watchlist row + positions row) and Playwright strict mode rejects it. Firefox/WebKit harness logs show this as the failure mode for 01-fresh-start (3 of 9 failed pairs)."
      - path: "test/03-buy.spec.ts:16"
        issue: "`expect(page.getByTestId('header-cash')).toHaveText('$10,000.00')` is an absolute pre-trade sanity assertion. With concurrent specs trading, the harness shows actual rendered values like `$6,049.89` when 03-buy starts after 04-sell or 05-portfolio-viz has already debited cash. Hardcoded $10k assertion only holds with workers: 1 OR with a per-spec fresh container."
      - path: "test/04-sell.spec.ts:42"
        issue: "Same root cause as 03-buy. The qty regex `/^\\s*1(?:\\.0+)?\\s*$/` saw `'4'` and `'5'` in the harness — the JPM row already had quantity from another concurrent spec's interaction (03-buy uses NVDA but a stray buy or accumulated state from prior tests poisoned the JPM cell). Quantity-1 assertion only holds with worker isolation."
      - path: "test/05-portfolio-viz.spec.ts:41"
        issue: "`page.mouse.move(0, 0)` Rule-1 fix (10-04 SUMMARY) is placed BETWEEN the heatmap assertion and the P&L tab click (line 38), but the harness trace shows the META hover tooltip is still intercepting pointer events at line 41 click. The fix did not fully cover the tab-pnl click path. Affects all 3 browsers (chromium, firefox, webkit) — distinct from the parallelism failure mode. 1 of 9 failed pairs (× 3 browsers = 3 distinct (spec, project) failures, all rooted in the same defect)."
    missing:
      - "Worker-level isolation. Either: (a) set `workers: 1` in playwright.config.ts to serialize ALL specs across all projects (simplest, slowest); (b) set `workers: 3` + project-level `fullyParallel: false` only — but Playwright doesn't support per-project worker caps so this is not actually achievable as 10-CONTEXT D-07 worded; (c) per-spec containers via `compose run` orchestration (heaviest); (d) move all UI-mutation specs into a single sharded file to keep them in one worker."
      - "Strict-mode-safe selectors throughout 01-fresh-start. Scope each `getByRole('button', { name: 'Select <ticker>' })` to `page.getByTestId('watchlist-panel')` since the test is asserting on the watchlist not the positions table."
      - "Relative cash assertion in 03-buy/04-sell pre-trade sanity check. Either drop the pre-trade `$10,000.00` assertion entirely (the post-trade `< 10_000` relative assertion is sufficient) OR scope it to a worker-fresh state with workers: 1."
      - "04-sell quantity assertion robustness. Either guarantee a fresh container (workers: 1) or change the assertion to a *delta* (qty-after-sell == qty-after-buy - 1) rather than an absolute `1`."
      - "05-portfolio-viz tooltip dismissal coverage. The `page.mouse.move(0, 0)` fix should be applied (a) BEFORE the tab-heatmap click as well, OR (b) replaced with a more reliable dismissal (e.g., page.keyboard.press('Escape'), or scroll the chart out of viewport, or pin the click to the tab button's exact bounding-box center). The current fix is insufficient — chromium-and-webkit harness traces show the click attempt retried many times and never succeeded; the META tooltip never dismissed."
deferred: []
---

# Phase 10: E2E Validation Verification Report

**Phase Goal:** An out-of-band `docker-compose.test.yml` brings up the production image alongside a Playwright container with `LLM_MOCK=true`, and every §12 end-to-end scenario passes green against it.

**Verified:** 2026-04-27T18:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth (ROADMAP Success Criteria)                                                                                                                                                                                                                                                                                                                                                                                  | Status     | Evidence                                                                                                                                                                                                                                                                                                                |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | SC#1: `test/docker-compose.test.yml` spins up the app container (`LLM_MOCK=true`) plus a Playwright container, keeping browser dependencies out of the production image.                                                                                                                                                                                                                                          | ✓ VERIFIED | `test/docker-compose.test.yml` exists with two services (`appsvc`, `playwright`); `appsvc.environment.LLM_MOCK: "true"` (line 26); compose-side healthcheck at line 36-42; production `Dockerfile` has no playwright/browser deps (verified by 09-VERIFICATION). Harness log line 119 shows `Container test-appsvc-1 Healthy`. |
| 2   | SC#2: The Playwright suite covers a fresh start (default watchlist visible, $10k balance, streaming prices), watchlist add + remove, buy shares (cash decreases, position appears), sell shares (cash increases, position updates or disappears), heatmap + P&L chart rendering, mocked chat with a visible trade execution, and SSE disconnect + automatic reconnect.                                            | ✓ VERIFIED | All 7 spec files exist under `test/`: 01-fresh-start, 02-watchlist-crud, 03-buy, 04-sell, 05-portfolio-viz, 06-chat, 07-sse-reconnect. Each maps directly to a §12 scenario per D-11. Specs assert the documented behaviors per code review.                                                                            |
| 3   | SC#3: Running the full E2E pack is a single command and finishes green locally against the freshly built image, with reproducible results on repeat runs.                                                                                                                                                                                                                                                         | ✗ FAILED   | Canonical command `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` exits 1. 9 of 21 (spec, project) pairs failed; 12 passed. Per-failure breakdown below. NOT reproducibly green.                                                                       |

**Score:** 2/3 truths verified

### Required Artifacts

| Artifact                                                                                                                            | Expected                                                                       | Status     | Details                                                                                                                                            |
| ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/Users/sherwood/Projects/python/src/github.com/sherwoodzern/finally/test/docker-compose.test.yml`                                  | Two-service compose with appsvc (LLM_MOCK=true) + playwright + healthcheck     | ✓ VERIFIED | All required keys present; appsvc rename per HSTS fix; healthcheck uses python3+urllib (curl absent from python:3.12-slim).                        |
| `test/playwright.config.ts`                                                                                                         | 3 browser projects, baseURL http://appsvc:8000, list+html reporter             | ⚠️ ORPHANED-INTENT | File exists and is wired. But `workers: 3` + `fullyParallel: false` does NOT realize CONTEXT D-07 intent ("workers: 1 within a Playwright project; cross-browser projects parallel"). The comment block in the config admits Playwright does not support per-project worker caps. The chosen config produces cross-spec parallelism that contends on shared SQLite state — root cause of 8/9 failures. |
| `test/01-fresh-start.spec.ts`                                                                                                       | Fresh start scenario — 10-ticker seed + $10k cash + streaming proof            | ✓ STRUCTURE / ✗ PARALLEL-SAFE | Asserts the right things on chromium (passed). Selector `getByRole('button', { name: 'Select AMZN' })` (line 27) is unscoped and collides with positions row when 06-chat runs concurrently. |
| `test/02-watchlist-crud.spec.ts`                                                                                                    | REST add+remove PYPL                                                           | ✓ VERIFIED | Passed all 3 browsers (REST `request` fixture, no browser navigation, no shared-state contention).                                                |
| `test/03-buy.spec.ts`                                                                                                               | NVDA × 1 buy → position appears + cash relative                                | ✓ STRUCTURE / ✗ PARALLEL-SAFE | Passed chromium. Failed firefox/webkit on hardcoded `$10,000.00` pre-trade sanity (line 16). Concurrent specs debited cash before this spec's `goto('/')` resolved on the slower browsers. |
| `test/04-sell.spec.ts`                                                                                                              | JPM ×2 buy → ×1 sell → qty=1                                                   | ✓ STRUCTURE / ✗ PARALLEL-SAFE | Passed chromium. Failed firefox/webkit. Harness shows JPM qty cell read `4` and `5` — concurrent specs polluted JPM holdings. Quantity-1 assumption only holds with worker isolation. |
| `test/05-portfolio-viz.spec.ts`                                                                                                     | META buy → heatmap-treemap + pnl-chart + pnl-summary visible                   | ✗ STUB     | Failed all 3 browsers identically. `page.mouse.move(0, 0)` mitigation (line 38) only protects ONE click path; the META tooltip subtree intercepts pointer events for `tab-pnl` click (line 41). Even with retries, the click never fires. This is a spec defect, not a flake. |
| `test/06-chat.spec.ts`                                                                                                              | Mock buy AMZN 1 → action-card-executed                                         | ✓ VERIFIED | Passed all 3 browsers. The Pitfall 4 guard (no bubble-text assertion) and `.first()` action-card scoping work as designed.                          |
| `test/07-sse-reconnect.spec.ts`                                                                                                     | abort('connectionreset') + reload → reconnect                                  | ✓ VERIFIED | Passed all 3 browsers. The `toBeAttached` Rule-1 fix and `context.route` pattern are correct.                                                       |

### Key Link Verification

| From                                       | To                                                                | Via                                                                                                            | Status     | Details                                                                                                                              |
| ------------------------------------------ | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `test/docker-compose.test.yml` (build context: ..) | repo-root `Dockerfile`                                            | `docker compose ... up --build` builds from local source per D-04                                              | ✓ WIRED    | Harness log lines 1-99 show the multi-stage build executing against the live Dockerfile.                                            |
| `test/docker-compose.test.yml` (LLM_MOCK)  | `backend/app/chat/mock.py`                                        | Phase 5 mock-mode env switch                                                                                    | ✓ WIRED    | 06-chat spec passes on all 3 browsers via the mock client. Harness log line 26 confirms `LLM_MOCK: "true"`.                          |
| `test/playwright.config.ts` (baseURL)      | `test/docker-compose.test.yml` (BASE_URL=http://appsvc:8000)      | Compose internal DNS via service name `appsvc`                                                                  | ✓ WIRED    | HSTS rename committed in 22ac1a4. All 3 browsers reach the app — 02/06/07 specs prove it.                                            |
| 01/03/04 spec selectors                    | Watchlist + positions rows (`Select <ticker>`)                    | Same `aria-label="Select {TICKER}"` pattern on both surfaces                                                    | ⚠️ AMBIGUOUS | 03/04 explicitly scope to `positions-table`. 01-fresh-start does NOT scope — collides under cross-spec concurrency.                   |
| 05-portfolio-viz tab-pnl click             | Recharts heatmap tooltip                                          | Pointer-event z-stack — META tooltip from heatmap subtree intercepts clicks on tab-pnl                          | ✗ NOT_WIRED | The `page.mouse.move(0, 0)` interleave at line 38 does NOT dismiss the tooltip enough to free up the tab-pnl click target on any of 3 browsers. |
| 03/04 pre-trade `$10,000.00` assertion     | Concurrent specs (05/04 share cash balance with 03)               | All specs hit the same SQLite users_profile.cash_balance row                                                    | ✗ NOT_WIRED | Hardcoded value only valid in worker-isolated context. With workers: 3, three specs debit cash concurrently and the assertion races. |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable        | Source                                | Produces Real Data | Status     |
| --------------------------------- | -------------------- | ------------------------------------- | ------------------ | ---------- |
| `test/docker-compose.test.yml`    | LLM_MOCK env         | Phase 5 backend mock client            | Yes                | ✓ FLOWING  |
| `test/01-fresh-start.spec.ts`     | watchlist row prices | SSE stream from running container      | Yes                | ✓ FLOWING (chromium proves it; em-dash leaves the cell) |
| `test/03-buy.spec.ts`             | header-cash          | running app cash balance                | Yes — but contended | ⚠️ STATIC-ASSERTION (the assertion is hardcoded; the data flows but the assertion can't ride concurrent mutations) |

### Behavioral Spot-Checks

| Behavior                              | Command                                                                                                            | Result                                | Status |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------- | ------ |
| Canonical harness command runs end-to-end | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright`  | exit 1; 12 passed / 9 failed (1.2m runtime) | ✗ FAIL |
| Compose YAML is well-formed            | `docker compose -f test/docker-compose.test.yml config`                                                             | exit 0 (per 10-01 SUMMARY)            | ✓ PASS |
| Playwright config parses               | `cd test && npx playwright test --list`                                                                             | exit 0 (per 10-01 SUMMARY); 21 tests listed | ✓ PASS |
| All 7 spec files exist                 | `ls test/0[1-7]-*.spec.ts \| wc -l`                                                                                  | 7                                     | ✓ PASS |

### Per-(spec, project) Pair Result Table

Source: `/tmp/phase10-harness.log` after the canonical orchestrator run with HSTS rename in place.

| Spec                       | Chromium  | Firefox   | WebKit    |
| -------------------------- | --------- | --------- | --------- |
| 01-fresh-start             | ✓ pass    | ✗ fail    | ✗ fail    |
| 02-watchlist-crud (REST)   | ✓ pass    | ✓ pass    | ✓ pass    |
| 03-buy                     | ✓ pass    | ✗ fail    | ✗ fail    |
| 04-sell                    | ✓ pass    | ✗ fail    | ✗ fail    |
| 05-portfolio-viz           | ✗ fail    | ✗ fail    | ✗ fail    |
| 06-chat                    | ✓ pass    | ✓ pass    | ✓ pass    |
| 07-sse-reconnect           | ✓ pass    | ✓ pass    | ✓ pass    |

**Aggregate:** 12 passed / 9 failed of 21 pairs. Harness exit 1.

### Failure Root-Cause Classification

Two distinct gap groups (related failures bundled by root cause to help the planner author focused gap-closure plans):

**Gap Group A — Cross-spec parallelism + spec-design defects (8 of 9 failures)**

Affects: 01-fresh-start (firefox, webkit), 03-buy (firefox, webkit), 04-sell (firefox, webkit) — 6 distinct (spec, project) failures. Plus the chromium-passing-firefox/webkit-failing pattern is consistent with chromium being the "first worker to land" in the parallel schedule, picking up the cleanest state. Root cause:

- `test/playwright.config.ts:26` sets `workers: 3`. Three worker processes pick up different spec files concurrently against the SAME SQLite (anonymous volume per `up`, but shared within the `up`).
- `test/03-buy.spec.ts:16` and `test/04-sell.spec.ts:42` (effectively, via the buy-then-assert flow) expect specific cash and quantity values. Concurrent specs mutate those values.
- `test/01-fresh-start.spec.ts:27` uses unscoped `getByRole('button', { name: 'Select <ticker>' })`. A concurrent buy in another spec (e.g., 06-chat buying AMZN, 03-buy buying NVDA) creates a positions row with the same accessible name, triggering Playwright strict-mode rejection.

**Gap Group B — 05-portfolio-viz tooltip-intercepts-tab-click (1 of 9 failures, replicated across all 3 browsers)**

Affects: 05-portfolio-viz on chromium, firefox, webkit (3 distinct (spec, project) failures, single root cause).

- After the heatmap renders, hovering over a tile triggers a Recharts tooltip rendered as `<td>{ticker}</td>` (in the harness log: `<td class="px-4 font-semibold">META</td> from <div class="flex flex-col gap-4">…</div> subtree intercepts pointer events`).
- The 10-04 SUMMARY claims a `page.mouse.move(0, 0)` fix between the heatmap assertion and the P&L tab click — present at `test/05-portfolio-viz.spec.ts:38`. But the harness traces show the tooltip is still intercepting `tab-pnl` clicks (line 41) on all 3 browsers despite the mouse-move fix.
- The fix is insufficient. Either the tooltip dismissal needs a more reliable mechanism (Escape key, scroll, blur), or the mouse-move needs to land on a non-Recharts element BEFORE the next click rather than just at viewport (0, 0).

### Requirements Coverage

| Requirement | Source Plan      | Description                                                                                                                                                                              | Status                              | Evidence                                                                                                                                                              |
| ----------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TEST-03     | 10-01-PLAN       | Playwright E2E harness under `test/` with its own `docker-compose.test.yml` running the app container (`LLM_MOCK=true`) alongside a Playwright container.                                | ✓ SATISFIED                         | Foundation files all present and wired; canonical command builds + boots successfully. Harness mechanism works; the failures are at the spec layer, not the harness. |
| TEST-04     | 10-00, 10-02..05 | All E2E scenarios from `planning/PLAN.md` §12 — fresh start, watchlist add/remove, buy/sell, heatmap + P&L chart rendering, mocked chat with trade execution, SSE reconnection.       | ⚠️ PARTIAL (5 of 7 scenarios green) | Specs exist for all 7 scenarios. 02, 06, 07 green across all browsers. 01, 03, 04 green chromium-only (parallelism contention). 05 fails all 3 browsers (tooltip defect). |

### Anti-Patterns Found

Scope: files modified across all six plans (per SUMMARY key-files), excluding the seven spec files which are themselves the subject of the verification.

| File                                                  | Line  | Pattern                                | Severity   | Impact                                                                                                                                                                                                            |
| ----------------------------------------------------- | ----- | -------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test/playwright.config.ts`                           | 17-27 | Documentation comment claims D-07 intent ("workers: 1 within a Playwright project"), but config sets `workers: 3` and admits in the same comment that Playwright doesn't support per-project worker caps. Yet the chosen config does NOT serialize within a project either — three concurrent workers process spec files greedily across all projects. | 🛑 Blocker | This is the root cause of Gap Group A (8 of 9 failures). The discrepancy between intent and realization wasn't caught at planning time and propagated to spec authors who then assumed serial within-project execution. |
| `test/05-portfolio-viz.spec.ts`                       | 38    | `page.mouse.move(0, 0)` between heatmap assertion and tab-pnl click. Comment says it "dismisses the tooltip" but harness traces show the tooltip still intercepts subsequent click. | 🛑 Blocker | Root cause of Gap Group B (3 of 9 failures, all 3 browsers).                                                                                                                                                  |
| `test/01-fresh-start.spec.ts`                         | 27    | Unscoped `getByRole('button', { name: \`Select ${ticker}\` })`. The same aria-label appears in BOTH the watchlist (`watchlist-panel`) AND the positions table (`positions-table`) when concurrent specs create positions. | ⚠️ Warning  | Contributes to Gap Group A. Easy fix: scope to `page.getByTestId('watchlist-panel')`.                                                                                                                          |
| `test/03-buy.spec.ts`                                 | 16    | `expect(page.getByTestId('header-cash')).toHaveText('$10,000.00')` is an absolute pre-trade sanity assertion. With concurrent specs mutating cash, this only holds in a worker-isolated execution. | ⚠️ Warning  | Contributes to Gap Group A. Either drop the pre-trade assertion or fix the parallelism config first.                                                                                                            |
| `test/04-sell.spec.ts`                                | 42    | `toHaveText(/^\\s*1(?:\\.0+)?\\s*$/)` absolute qty assertion. Harness saw `'4'` and `'5'`. | ⚠️ Warning  | Contributes to Gap Group A.                                                                                                                                                                                  |

No TODO/FIXME/PLACEHOLDER markers found in the spec files themselves — the failures are real spec/config defects, not stubs.

### Human Verification Required

None. All gaps are reproducibly demonstrable from the harness log and identifiable from static inspection of the config + spec files. Once the orchestrator/planner fixes the parallelism strategy and the tooltip dismissal, re-running the canonical command will deterministically prove green or red. There is no UX/visual/timing-feel item that requires human judgment.

### Gaps Summary

ROADMAP Phase 10 has three success criteria. **SC#1 (compose harness with LLM_MOCK + browser deps isolated) and SC#2 (suite covers all 7 §12 scenarios) are met.** Five of the seven scenarios (02, 03 chromium, 04 chromium, 06, 07) actually pass green; the other two (01, 05) plus 03/04 on firefox/webkit fail.

**SC#3 ("single command finishes green locally with reproducible results on repeat runs") is the gate that fails.** The harness exits 1 with 9 of 21 pairs failed. Two root-cause families:

1. **Cross-spec parallelism contention (8 failures).** `playwright.config.ts` ships `workers: 3` + `fullyParallel: false`, which the config comments themselves admit does not realize CONTEXT.md D-07's stated intent ("workers: 1 within a Playwright project"). Three workers concurrently run different spec files against shared SQLite state. The spec authors wrote assertions assuming worker-1 isolation (hardcoded `$10,000.00`, hardcoded qty `1`, unscoped seed-ticker selectors). Either the config needs to change (workers: 1) or the specs need to drop absolute-state assertions in favor of relative ones (deltas, before/after captures).

2. **05-portfolio-viz Recharts tooltip intercepts tab click (1 failure × 3 browsers).** The 10-04 Rule-1 fix `page.mouse.move(0, 0)` is in the wrong place / insufficient form. All 3 browsers show identical pointer-event interception preventing `tab-pnl` click.

These are NOT browser-environment flakes (e.g., the previously-blocking HSTS issue is RESOLVED — confirmed by the foundation rename in commit 22ac1a4 and the fact that 02, 06, 07 are green across all 3 browsers via real browser navigation in 06/07). They are deterministic defects in the parallelism config and one spec.

A Phase 10.1 gap-closure pass needs to address both gap groups. Suggested grouping for `/gsd-plan-phase 10 --gaps`:
- **Plan A** — Parallelism + spec assertions: edit `playwright.config.ts` and 01/03/04 specs together.
- **Plan B** — Tooltip dismissal in 05-portfolio-viz: replace or augment the `page.mouse.move(0, 0)` mitigation.

No items are deferred to a later phase; Phase 10 is the final phase in the roadmap.

---

*Verified: 2026-04-27T18:30:00Z*
*Verifier: Claude (gsd-verifier)*
