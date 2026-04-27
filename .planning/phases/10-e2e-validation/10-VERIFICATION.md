---
phase: 10-e2e-validation
verified: 2026-04-27T19:35:00Z
status: gaps_found
score: 2/3 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 2/3
  gaps_closed:
    - "Cross-spec parallelism contention from `workers: 3` (Gap Group A — workers config). 10-06 commit 491e6ff sets `workers: 1`."
    - "Unscoped `getByRole('button', { name: 'Select <ticker>' })` in 01-fresh-start (Gap Group A — selector scoping). 10-06 commit 761d3a6 scopes to `getByTestId('watchlist-panel')`."
    - "Hardcoded `$10,000.00` pre-trade assertion in 03-buy (Gap Group A — absolute cash). 10-06 commit 3bb6105 drops the assertion entirely."
    - "Absolute qty=1 regex assertion in 04-sell (Gap Group A — absolute qty). 10-06 commit ee45f65 converts to `expect.poll(...).toBe(postBuyQty - 1)`."
    - "10-07 Task 1 `dismissChartTooltip` helper landed in 05-portfolio-viz (commit 9924ccc) — Escape + mouse displacement called immediately before tab-pnl click."
  gaps_remaining:
    - "ROADMAP SC#3 — single canonical command finishes green reproducibly. Today's run: 14 passed / 5 failed / 2 flaky / exit 1."
  regressions:
    - "Failure shape changed since previous VERIFICATION.md. The 9-failure pattern (parallelism + tooltip + spec-design) is gone, replaced by a 5-failure + 2-flaky pattern with three NEW root causes (Modes A, B, C below). Net failure count dropped from 9 → 5, but reproducibility is still NOT met (flaky retries cannot count toward `reproducibly green`)."
gaps:
  - truth: "After the heatmap renders, the Recharts hover tooltip is reliably dismissed before the tab-pnl click — across all 3 browsers."
    status: failed
    reason: "Mode A — Tooltip survives the `dismissChartTooltip` helper on all 3 browsers. The helper (Escape + mouse-move) does not actually retract the Recharts Treemap default tooltip overlay once it has pinned to a cell. Recharts dismisses on chart `mouseleave`, not on document-level keyboard events; the tooltip subtree continues to intercept pointer events at the tab-pnl click target. Evidence: harness lines 626 (chromium NVDA), 675 (firefox META), 860 (webkit META) — `<td class=\"px-4 font-semibold\">{ticker}</td> from <div class=\"flex flex-col gap-4\">…</div> subtree intercepts pointer events`. All 3 browsers report TimeoutError after retrying click action ~22 times. 3 of 5 hard failures."
    artifacts:
      - path: "test/05-portfolio-viz.spec.ts"
        issue: "Line 49 calls `dismissChartTooltip()` immediately before line 50 `getByTestId('tab-pnl').click()`, but the helper body (lines 26-29) does Escape + `page.mouse.move(0, 0)` only. Neither dispatches a `mouseleave` event on the chart container, which is what the Recharts Tooltip lifecycle actually listens for. The verifier confirmed — by reading the harness traces — the same `<td>{ticker}</td> subtree intercepts pointer events` failure as before; the helper is structurally insufficient."
      - path: "frontend/src/components/portfolio/Heatmap.tsx"
        issue: "No `<Tooltip>` is explicitly imported or rendered inside `<Treemap>`. Recharts uses its DEFAULT internal tooltip which renders a wrapper `<div class=\"flex flex-col gap-4\">` containing the `<td>{ticker}</td>` cell. The default wrapper has `pointer-events: auto`, so the tooltip overlay covers and intercepts clicks on neighbouring elements (sibling tabs in the TabBar)."
    missing:
      - "Production-side fix: import `Tooltip` from `recharts` in `frontend/src/components/portfolio/Heatmap.tsx` and render it as a child of `<Treemap>` with `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />`. Closes Mode A on all 3 browsers in one line — the tooltip remains visible (correct production UX) but its wrapper no longer intercepts clicks. This is the simplest fix and is appropriate for production: hover tooltips that block sibling clicks are a UX defect regardless of test coverage."
      - "Alternative (test-side only): replace `dismissChartTooltip` with `await page.locator('[data-testid=heatmap-treemap]').dispatchEvent('mouseleave')` to fire the actual event Recharts is listening for. This is more invasive and brittle (depends on internal Recharts event names). The production fix is preferred."
  - truth: "01-fresh-start asserts the seed $10,000.00 cash on a clean SQLite state across all 3 browsers."
    status: failed
    reason: "Mode B — Cross-project SQLite leak. The anonymous compose volume persists for the entire `up` invocation, NOT per browser project. With `workers: 1`, chromium runs ALL 7 specs first (debiting cash via 03-buy/04-sell/05-portfolio-viz/06-chat), THEN firefox runs against the same SQLite (cash now $7,820.46, NOT $10,000.00), THEN webkit (cash now $5,447.88). The `workers: 1` decision in 10-06 fixed cross-spec contention WITHIN one project, but never addressed cross-project ordering — that's a per-project SQLite reset problem, not a worker count problem. Evidence: harness lines 729 (firefox: Received `$7,820.46`), 916 (webkit: Received `$5,447.88`). 2 of 5 hard failures."
    artifacts:
      - path: "test/01-fresh-start.spec.ts"
        issue: "Line 34 still asserts the absolute literal `$10,000.00`. Comment at line 33 says `Header cash reads $10,000.00 (Plan 10-00 testid)`. This holds for chromium (the FIRST project alphabetically under workers:1) but fails for firefox and webkit because cash has been debited by chromium's 03/04/05/06 specs against the shared SQLite volume. 10-06 deliberately preserved this assertion (Plan 10-06 Task 2 wording: `01-fresh-start runs FIRST in alphabetical spec order and `workers: 1` (Task 1) guarantees no prior spec has mutated cash`) — but `runs first` is true only WITHIN a project, not ACROSS projects."
    missing:
      - "Test-side fix: drop the absolute `$10,000.00` assertion at `test/01-fresh-start.spec.ts:34`, mirroring 10-06's decision for 03-buy. The 10-ticker watchlist visibility (lines 25-31) and the streaming-proof `not.toContainText('—')` (line 41) already prove the page is on a working app. Cash level is incidental to the `fresh start` truth and depends on cross-project ordering that the harness does not control."
      - "Alternative (heavier): per-project SQLite reset, e.g. `globalSetup` that hits a hypothetical `/api/test/reset` endpoint (explicitly rejected by CONTEXT D-06 — no test-only production endpoints) OR per-project compose `up` (rejected by CONTEXT D-03 — single canonical command). Test-side drop is the only path consistent with existing decisions."
  - truth: "04-sell deterministically passes on every (spec, project) pair without retries."
    status: failed
    reason: "Mode C — Snapshot-vs-refetch race. The `postBuyQty` capture at `test/04-sell.spec.ts:36-37` happens immediately after the `Select JPM` button becomes visible (line 25-27) but BEFORE React Query has refetched `/api/portfolio` and re-rendered the JPM qty cell with the post-buy value. On firefox the snapshot caught `1` (intermediate), the sell debited 1, target was `1-1=0`, but the actual qty cell value is `2` (post-buy buy of 2 fully refetched after the snapshot). On webkit the snapshot caught `3` (a stale value from prior cross-project state + buy in flight), target was `3-1=2`, actual is `4`. The `expect.poll` recovers on retry #1, so Playwright reports `flaky` (eventually passed). But the plan's acceptance criterion in 10-07 Task 2 (`grep -c 'flaky' = 0`) is violated, AND `reproducibly green` is broken — the same `up` produces different per-pair outcomes run-to-run. 2 of 5 outcomes (both as `flaky`)."
    artifacts:
      - path: "test/04-sell.spec.ts"
        issue: "Lines 34-37 capture `postBuyQty` before the React Query refetch settles. The visibility wait at lines 25-27 only proves the JPM `<button>` is rendered; it does NOT guarantee the second `<td>` (qty cell) has refetched its post-buy value. On firefox the snapshot caught the stale qty `1` and on webkit caught `3` — both wrong by 1 from the true post-buy quantity. Evidence: harness line 1090 (firefox: Expected 0, Received 2), line 1119 (webkit: Expected 2, Received 4). Both cases match `actual_qty - postBuyQty = 1` (the buy of 2 finalised AFTER the snapshot)."
    missing:
      - "Test-side fix: stabilise `postBuyQty` BEFORE snapshotting it. Replace lines 34-37 with an `expect.poll` that waits for `parseFloat(qtyCellText) >= 2` (the buy added 2, so the post-buy qty must be at least 2 regardless of any prior state). Capture `postBuyQty` only AFTER the poll succeeds. Then the existing relative-delta assertion at lines 47-52 will be deterministic. Same pattern as 10-06 used in lines 47-52 — apply it to the snapshot read as well."
deferred: []
overrides: []
---

# Phase 10: E2E Validation Verification Report

**Phase Goal:** An out-of-band `docker-compose.test.yml` brings up the production image alongside a Playwright container with `LLM_MOCK=true`, and every §12 end-to-end scenario passes green against it.

**Verified:** 2026-04-27T19:35:00Z
**Status:** gaps_found
**Re-verification:** Yes — after Plan 10-06 (Gap Group A closure) + Plan 10-07 Task 1 (Escape helper). 10-07 Task 2 (canonical harness gate) FAILED and was abandoned per failure protocol; 10-07-SUMMARY.md was never written. Failure shape has CHANGED since the previous VERIFICATION.md was written.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth (ROADMAP SC)                                                                                                                                                                                          | Status     | Evidence                                                                                                                                                                                                                                                          |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | SC#1: All §12 spec files exist (7 specs total).                                                                                                                                                             | ✓ VERIFIED | 7 spec files under `test/`: 01-fresh-start, 02-watchlist-crud, 03-buy, 04-sell, 05-portfolio-viz, 06-chat, 07-sse-reconnect (verified by `ls test/0[0-9]-*.spec.ts`).                                                                                              |
| 2   | SC#2: Harness foundation works (compose up, /api/health, browsers reach app).                                                                                                                               | ✓ VERIFIED | Harness log line 120: `Container test-appsvc-1 Healthy`. All 21 (spec, project) pairs were dispatched and ran. 14 passed, including all 6 pairs of 02-watchlist-crud and 06-chat (proving REST + browser navigation paths both reach the app on every browser).   |
| 3   | SC#3: Single canonical command finishes green reproducibly — `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` exits 0 with all 21 pairs passing. | ✗ FAILED   | Today's run: harness log lines 1148-1158 — `5 failed`, `2 flaky`, `14 passed`, `playwright-1 exited with code 1`. Exit code 1 fails SC#3's `exits 0`. The 2 flaky retries also fail SC#3's `reproducibly`. TEST-03 and TEST-04 cannot be marked complete.        |

**Score:** 2/3 truths verified

### Per-(spec, project) Pair Result Table

Source: `/tmp/phase10-gap-closure-harness.log` (1169 lines). Today's canonical-command run.

| Spec                     | Chromium | Firefox      | WebKit       |
| ------------------------ | -------- | ------------ | ------------ |
| 01-fresh-start           | ✓ pass   | ✗ fail (B)   | ✗ fail (B)   |
| 02-watchlist-crud (REST) | ✓ pass   | ✓ pass       | ✓ pass       |
| 03-buy                   | ✓ pass   | ✓ pass       | ✓ pass       |
| 04-sell                  | ✓ pass   | ⚠️ flaky (C) | ⚠️ flaky (C) |
| 05-portfolio-viz         | ✗ fail (A) | ✗ fail (A) | ✗ fail (A) |
| 06-chat                  | ✓ pass   | ✓ pass       | ✓ pass       |
| 07-sse-reconnect         | ✓ pass   | ✓ pass       | ✓ pass       |

**Aggregate:** 14 passed / 5 failed / 2 flaky / 0 not-run, of 21 pairs. Harness exit 1.

Mode legend:
- **(A)** Recharts heatmap tooltip intercepts `tab-pnl` click (3 hard failures)
- **(B)** Cross-project SQLite leak — `$10,000.00` no longer holds when 01-fresh-start runs after chromium's full pass debited cash (2 hard failures)
- **(C)** `postBuyQty` snapshot races React Query refetch in 04-sell (2 flaky retries — pass on retry #1 but block reproducibility)

### Failure Mode Detail

**Mode A — 05-portfolio-viz: tooltip subtree intercepts tab-pnl click on all 3 browsers** (3 of 5 hard failures)

Evidence:
- Harness line 626: `[chromium] <td class="px-4 font-semibold">NVDA</td> from <div class="flex flex-col gap-4">…</div> subtree intercepts pointer events`
- Harness line 675: `[firefox] <td class="px-4 font-semibold">META</td> ...` (same shape)
- Harness line 860: `[webkit] <td class="px-4 font-semibold">META</td> ...` (same shape)
- Harness lines 619-647: Playwright retried `tab-pnl` click ~22 times across `2 × waiting`, `19 × waiting`, eventually TimeoutError at line 647.
- The chromium tooltip caption is `NVDA` because chromium runs 03-buy first (creating an NVDA position) and at the moment of the heatmap hover, NVDA's tile is the largest (chromium has accumulated NVDA + JPM + META positions by the time 05 runs).
- 10-07 commit 9924ccc landed the `dismissChartTooltip` helper (Escape + mouse-move) at line 49 immediately before the tab-pnl click — but the harness traces show the tooltip pin SURVIVES both the Escape keypress and the mouse-move. Confirmed by direct read of `/tmp/phase10-gap-closure-harness.log:619-647` — the helper executed (no error), and the click still failed with the same `subtree intercepts pointer events` shape.

Why the helper is insufficient: Recharts' default Tooltip lifecycle dismisses on `mouseleave` of the chart container, not on a document-level keypress and not on a mouse-move-to-(0,0) that does not pass through a synthetic mouse event chain on the chart node itself. Once the tooltip has anchored to a cell, it stays anchored.

**Mode B — 01-fresh-start: cross-project SQLite leak** (2 of 5 hard failures)

Evidence:
- Harness line 729: `[firefox] Expected: "$10,000.00" / Received: "$7,820.46"`
- Harness line 916: `[webkit] Expected: "$10,000.00" / Received: "$5,447.88"`
- Harness lines 730 (firefox) and 917 (webkit): `9 × locator resolved to <span data-testid="header-cash" ...>$7,820.46</span>` (the value is stable, NOT a transient mid-render snapshot).

Root cause: The compose anonymous volume persists across all 3 browser projects within a single `up`. Under `workers: 1`, projects run alphabetically — chromium first, firefox second, webkit third. By the time firefox 01-fresh-start runs, chromium has already executed:
- 03-buy (NVDA × 1) → debits cash
- 04-sell (JPM × 2 buy → JPM × 1 sell) → debits cash net
- 05-portfolio-viz (META × 1 buy) → debits cash (note: 05 still failed but the META buy lands BEFORE the failing tab-pnl click, so cash is debited)
- 06-chat (mock buy AMZN × 1) → debits cash

So firefox sees ~$7.8k. By the time webkit runs, firefox + chromium have done two passes of debits, so webkit sees ~$5.4k.

10-06's commit history (Plan 10-06 Task 2) deliberately PRESERVED the absolute `$10,000.00` assertion at line 34 with the rationale "01-fresh-start runs FIRST in alphabetical spec order and `workers: 1` (Task 1) guarantees no prior spec has mutated cash." That rationale is correct WITHIN a project — but `workers: 1` is a per-project worker cap, NOT a cross-project ordering guarantee. The plan missed this distinction.

**Mode C — 04-sell: postBuyQty snapshot races React Query refetch** (2 flaky retries)

Evidence:
- Harness line 1090: `[firefox] Expected: 0 / Received: 2` — postBuyQty captured = 1 (an in-flight value), expected `1-1=0`, actual qty after sell = `2` (the buy of 2 fully refetched after the snapshot). Position quantity was `0` from prior cross-project state, +2 buy = `2`, snapshot caught `1` mid-refetch, sell -1 → assertion expected `0`, actual is `2`.
- Harness line 1119: `[webkit] Expected: 2 / Received: 4` — postBuyQty captured = 3, expected `3-1=2`, actual = `4`. Webkit JPM had `2` from prior state (firefox's net +1 after buy 2 / sell 1), + buy 2 = `4`, snapshot caught `3` mid-refetch, sell -1 → assertion expected `2`, actual is `4`.
- Both cases: `actual_qty = postBuyQty + 1` (the buy completed after the snapshot, adding 1 more share than the snapshot recorded).
- Harness lines 356 (firefox retry #1: ✓ 857ms), 532 (webkit retry #1: ✓ 902ms) — both pass on retry, so Playwright marks `flaky`.

Root cause: The visibility wait at `test/04-sell.spec.ts:25-27` (`positionsTable.getByRole('button', { name: 'Select JPM' }).toBeVisible()`) only proves the JPM `<button>` element exists. It does NOT wait for React Query's `/api/portfolio` refetch to populate the qty cell with the post-buy value. The snapshot read at lines 36-37 happens too early.

The flakiness blocks SC#3's `reproducibly` even though Playwright reports `passed` after retry. Plan 10-07 Task 2's acceptance criterion `grep -c 'flaky' /tmp/phase10-gap-closure-harness.log = 0` is violated.

### Required Artifacts

| Artifact                                           | Expected                                                                  | Status              | Details                                                                                                                                                                            |
| -------------------------------------------------- | ------------------------------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test/docker-compose.test.yml`                     | Two-service compose with appsvc (LLM_MOCK=true) + playwright              | ✓ VERIFIED          | Container test-appsvc-1 Healthy (harness log line 120). All 21 pairs dispatched.                                                                                                   |
| `test/playwright.config.ts`                        | `workers: 1`, 3 browser projects, baseURL `http://appsvc:8000`            | ✓ VERIFIED          | Line 31: `workers: 1`. Line 32: `fullyParallel: false`. Lines 71-75: 3 projects. Line 48: baseURL `http://appsvc:8000`. 10-06 commit 491e6ff confirmed.                            |
| `test/01-fresh-start.spec.ts`                      | Watchlist-panel-scoped Select-button locators                             | ⚠️ PARTIAL (Mode B) | Lines 26-31 + 38-40: Select-buttons scoped to `getByTestId('watchlist-panel')` ✓. BUT line 34 still asserts absolute `$10,000.00` cash — fails on firefox/webkit due to Mode B.    |
| `test/02-watchlist-crud.spec.ts`                   | REST add+remove PYPL                                                      | ✓ VERIFIED          | Passed all 3 browsers (REST `request` fixture, no shared-state contention).                                                                                                        |
| `test/03-buy.spec.ts`                              | NVDA × 1 buy, no pre-trade $10k assertion, post-trade `< 10_000`          | ✓ VERIFIED          | 10-06 commit 3bb6105: pre-trade $10k assertion removed (line 13-14 now bears explanatory comment). Post-trade `< 10_000` at line 38. Passed all 3 browsers.                       |
| `test/04-sell.spec.ts`                             | postBuyQty snapshot + relative delta `(postBuyQty - 1)` via expect.poll   | ⚠️ PARTIAL (Mode C) | 10-06 commit ee45f65: relative-delta assertion at lines 47-52 ✓. BUT the snapshot at lines 36-37 races the buy refetch → flaky on firefox + webkit.                                |
| `test/05-portfolio-viz.spec.ts`                    | `dismissChartTooltip` helper (Escape + mouse-move) before tab-pnl click   | ⚠️ PARTIAL (Mode A) | 10-07 commit 9924ccc: helper defined at lines 26-29, called at line 49 before tab-pnl click at line 50 ✓. BUT helper does not actually retract the Recharts default tooltip → fails all 3 browsers. |
| `test/06-chat.spec.ts`                             | Mock buy AMZN 1 → action-card-executed                                    | ✓ VERIFIED          | Passed all 3 browsers.                                                                                                                                                             |
| `test/07-sse-reconnect.spec.ts`                    | abort('connectionreset') + reload → reconnect                             | ✓ VERIFIED          | Passed all 3 browsers.                                                                                                                                                             |
| `frontend/src/components/portfolio/Heatmap.tsx`    | (Implicit) hover tooltip should not block sibling clicks                  | ⚠️ DEFECT           | No explicit `<Tooltip>` rendered. Recharts default Tooltip wrapper has `pointer-events: auto`, intercepting clicks on neighbouring tabs. Production UX defect surfaced by Mode A. |

### Key Link Verification

| From                                              | To                                              | Via                                                                                                  | Status      | Details                                                                                                                                       |
| ------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `test/docker-compose.test.yml` (build context)    | repo-root `Dockerfile`                          | `docker compose ... up --build`                                                                      | ✓ WIRED     | Build executed in harness lines 1-99. Container test-appsvc-1 Healthy (line 120).                                                              |
| `test/docker-compose.test.yml` (LLM_MOCK)         | `backend/app/chat/mock.py`                      | Phase 5 mock-mode env switch                                                                         | ✓ WIRED     | 06-chat passed all 3 browsers via the mock client.                                                                                            |
| `test/playwright.config.ts` (baseURL appsvc)      | compose service `appsvc`                        | Compose internal DNS                                                                                 | ✓ WIRED     | All 3 browsers reached the app (02/06/07 prove it; 01/04/05 also reached the app — they failed at assertion time, not navigation time).      |
| 05-portfolio-viz `dismissChartTooltip` helper     | Recharts Treemap default Tooltip                | Browser-level Escape key + cursor displacement to (0,0)                                              | ✗ NOT_WIRED | The helper executes (no error) but the tooltip does not dismiss. Recharts listens for `mouseleave` on the chart container, not Escape.        |
| 04-sell `postBuyQty` snapshot                     | Post-refetch JPM qty cell text                  | `await jpmQty.innerText()` after `Select JPM` button is visible                                      | ✗ NOT_WIRED | Visibility of the row does not imply qty cell has refetched to post-buy value. The snapshot races React Query.                                 |
| 01-fresh-start `$10,000.00` assertion             | Pristine SQLite cash_balance                    | Compose anonymous volume (per-`up`, NOT per-project)                                                 | ✗ NOT_WIRED | Cross-project ordering under `workers: 1` puts firefox and webkit AFTER chromium's debits; the assertion only holds for chromium.            |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable        | Source                                                              | Produces Real Data            | Status                                                                  |
| --------------------------------- | -------------------- | ------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------------------------------- |
| `test/05-portfolio-viz.spec.ts`   | tab-pnl click target | TabBar button (verified-existent in DOM, see harness lines 620, 669) | Yes (locator resolves)        | ⚠️ INTERCEPTED — pointer events absorbed by sibling Recharts tooltip overlay |
| `test/04-sell.spec.ts`            | `postBuyQty`         | `jpmQty.innerText()` after Select JPM visibility                    | Yes — but pre-refetch          | ⚠️ STALE — snapshot is a pre-refetch in-flight value, not the post-buy resting value |
| `test/01-fresh-start.spec.ts`     | header-cash          | Live SQLite via `/api/portfolio`                                    | Yes — but cross-project leaked | ⚠️ DRIFT — value flows correctly; the absolute assertion does not match drift state |

### Behavioral Spot-Checks

| Behavior                                                      | Command                                                                                                            | Result                                                       | Status |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------ | ------ |
| Canonical harness command runs end-to-end                     | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` | exit 1; 14 passed / 5 failed / 2 flaky (2.4m runtime)        | ✗ FAIL |
| Compose YAML is well-formed                                   | `docker compose -f test/docker-compose.test.yml config`                                                            | exit 0 (per 10-01 SUMMARY)                                   | ✓ PASS |
| Playwright config parses                                      | `cd test && npx playwright test --list`                                                                            | exit 0 (21 tests listed)                                     | ✓ PASS |
| All 7 spec files exist                                        | `ls test/0[1-7]-*.spec.ts \| wc -l`                                                                                | 7                                                            | ✓ PASS |
| `workers: 1` active in playwright.config.ts                   | `grep -E '^\s*workers:\s*1\b' test/playwright.config.ts`                                                            | match at line 31                                             | ✓ PASS |
| `dismissChartTooltip` helper present in 05-portfolio-viz      | `grep -c 'dismissChartTooltip' test/05-portfolio-viz.spec.ts`                                                       | 2 (1 definition + 1 call)                                    | ✓ PASS |
| Helper actually retracts the tooltip in practice              | (manual inspection of harness traces 619-647, 668-696)                                                              | tooltip survives Escape + mouse-move on all 3 browsers       | ✗ FAIL |
| $10k assertion removed from 03-buy                            | `grep -c '\$10,000.00' test/03-buy.spec.ts`                                                                         | 0                                                            | ✓ PASS |
| Relative delta assertion in 04-sell                           | `grep -c 'postBuyQty - 1' test/04-sell.spec.ts`                                                                     | 1                                                            | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan      | Description                                                                                                                                                | Status                              | Evidence                                                                                                                                                                                                  |
| ----------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TEST-03     | 10-01-PLAN       | Playwright E2E harness under `test/` with its own `docker-compose.test.yml` running the app container (`LLM_MOCK=true`) alongside a Playwright container. | ✓ SATISFIED                         | Foundation works end-to-end. appsvc Healthy, 14 passing, all 3 browsers reach the app. The harness mechanism is correct; remaining failures are at the spec / production-component layer.               |
| TEST-04     | 10-00, 10-02..07 | All §12 E2E scenarios pass green — fresh start, watchlist add/remove, buy/sell, heatmap + P&L chart rendering, mocked chat with trade execution, SSE reconnect. | ⚠️ BLOCKED                          | 5 of 7 §12 scenarios green on every browser (02/03/06/07 + 04 chromium-only). 01 chromium-only. 05 fails all 3 browsers. SC#3 (single-command-green-reproducibly) is not met → TEST-04 cannot complete. |

Per ROADMAP Phase 10's bottom traceability, both TEST-03 and TEST-04 remain `[ ]` unchecked in REQUIREMENTS.md. This verification does NOT mark them complete.

### Plan-by-Plan must_haves Status

| Plan       | must_have truth                                                                                                       | Status                                                                              |
| ---------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 10-00      | data-testids land on Header/TabBar/Watchlist/PositionsTable/TradeBar                                                  | ✓ MET — confirmed by harness traces (`getByTestId('header-cash')`, `getByTestId('watchlist-panel')`, etc. all resolve in DOM) |
| 10-01      | docker-compose.test.yml + playwright.config.ts + healthcheck                                                          | ✓ MET — appsvc Healthy, all 21 pairs dispatched                                     |
| 10-02      | 01-fresh-start (10-ticker seed) + 02-watchlist-crud (PYPL REST)                                                       | ✓ MET (specs land) / ⚠️ 01 fails on firefox + webkit due to Mode B                  |
| 10-03      | 03-buy + 04-sell                                                                                                      | ✓ MET (specs land) / ⚠️ 04 flaky on firefox + webkit due to Mode C                  |
| 10-04      | 05-portfolio-viz + 06-chat                                                                                            | ✓ MET (specs land) / ✗ 05 fails all 3 browsers due to Mode A                        |
| 10-05      | 07-sse-reconnect + harness gate                                                                                       | ⚠️ PARTIAL — 07 passes all 3 browsers, but harness gate exit 1 (NOT 0)              |
| 10-06      | "Single Playwright worker serializes all 7 spec files across all 3 browser projects"                                  | ✓ MET — workers: 1 active                                                           |
| 10-06      | "01-fresh-start asserts only on watchlist rows"                                                                       | ✓ MET — Select-button locators scoped to watchlist-panel                            |
| 10-06      | "03-buy makes no absolute pre-trade cash assertion"                                                                   | ✓ MET — pre-trade $10k assertion removed                                            |
| 10-06      | "04-sell asserts the post-sell quantity using a relative delta (post-buy qty minus 1)"                                | ✓ MET — `expect.poll(...).toBe(postBuyQty - 1)` at line 47-52                       |
| 10-06      | "Canonical harness exits 0 with all 21 pairs passing — Gap Group A from VERIFICATION.md is fully closed"              | ✗ NOT MET — exit 1, 14 passed, NEW failure modes B and C surfaced after 10-06 fixes |
| 10-07      | "After the heatmap tile interaction, the Recharts hover tooltip is reliably dismissed before any subsequent click"   | ✗ NOT MET — `dismissChartTooltip` helper present but does not actually dismiss      |
| 10-07      | "Canonical harness exits 0 with all 21 (spec, project) pairs passing"                                                 | ✗ NOT MET — exit 1                                                                  |
| 10-07      | "ROADMAP Phase 10 SC#3 is met"                                                                                        | ✗ NOT MET                                                                           |

### Anti-Patterns Found

| File                                              | Line  | Pattern                                                                                                                                                                                       | Severity   | Impact                                                                                       |
| ------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------- |
| `test/05-portfolio-viz.spec.ts`                   | 26-29 | `dismissChartTooltip` helper assumes Escape + mouse-move dismisses Recharts tooltip. Harness traces prove it does not. The helper is a placeholder mitigation that doesn't fire the right event. | 🛑 Blocker | Mode A — all 3 browsers fail.                                                                |
| `test/01-fresh-start.spec.ts`                     | 34    | Absolute `$10,000.00` assertion. Comment at line 33 reflects an incorrect assumption that 01-fresh-start runs against a clean SQLite on every browser project.                                | 🛑 Blocker | Mode B — firefox + webkit fail.                                                              |
| `test/04-sell.spec.ts`                            | 36-37 | `postBuyQty` snapshot is read immediately after row visibility, before React Query refetches the qty cell. Visibility ≠ refetched data.                                                       | ⚠️ Warning  | Mode C — firefox + webkit flaky. Recovers on retry, but blocks `reproducibly green`.       |
| `frontend/src/components/portfolio/Heatmap.tsx`   | 119-127 | Default Recharts Treemap tooltip wrapper has `pointer-events: auto` and intercepts clicks on sibling tabs. Production UX defect, not just a test concern.                                       | ⚠️ Warning  | Root cause of Mode A. Production fix `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` closes Mode A on all 3 browsers in one line. |

### Human Verification Required

None. All gaps are reproducibly demonstrable from `/tmp/phase10-gap-closure-harness.log` and verifiable via static inspection of the named files at the named lines. Once Modes A/B/C are fixed, re-running the canonical command will deterministically prove green or surface a new failure shape. There are no UX/visual/timing-feel items needing human judgment at this stage.

### Recommended Fix Plan

Three small, independent edits close all three modes. Each can be its own gap-closure plan, OR they can be bundled into a single Plan 10-08 (recommended — they are tightly related and the harness gate must run once after all three land).

**Fix 1 (Production fix — closes Mode A)** — `frontend/src/components/portfolio/Heatmap.tsx`
- Import `Tooltip` from `recharts`
- Render `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` as a child of `<Treemap>`
- Effect: tooltip remains visible (correct UX), but its wrapper no longer intercepts clicks on sibling tabs
- Closes 3 hard failures (chromium / firefox / webkit on 05-portfolio-viz) in one line
- Justification for production-side fix: a hover tooltip that blocks neighbouring clicks is a UX defect regardless of test coverage. The user could hit this manually by hovering a heatmap tile and then trying to click the P&L tab. Production hardening, not test-only band-aid.
- After this fix lands, the existing `dismissChartTooltip` helper in `05-portfolio-viz.spec.ts` becomes redundant. Either delete it (cleanest) or leave it in place as belt-and-suspenders (acceptable; no behavioural change).

**Fix 2 (Test fix — closes Mode B)** — `test/01-fresh-start.spec.ts`
- Delete line 34 (`await expect(page.getByTestId('header-cash')).toHaveText('$10,000.00');`) and the comment at line 33
- Replace with a one-line comment explaining the cross-project SQLite leak rationale (mirrors 10-06's pattern in 03-buy)
- The 10-ticker watchlist visibility (lines 25-31) and the streaming-proof (lines 38-41) are sufficient to prove `fresh start` — cash level is incidental
- Closes 2 hard failures (firefox / webkit on 01-fresh-start)
- Justification: same reasoning as 10-06's drop in 03-buy. Absolute cash assertions are fragile across cross-project state; relative or non-cash assertions are robust.

**Fix 3 (Test fix — closes Mode C)** — `test/04-sell.spec.ts`
- Replace lines 36-37 (`const postBuyQtyText = await jpmQty.innerText(); const postBuyQty = parseFloat(postBuyQtyText.trim());`) with an `expect.poll` that waits for `parseFloat(qtyCellText) >= 2` before snapshotting:

  ```typescript
  // Wait for React Query to refetch the post-buy qty before snapshotting.
  // The Select-JPM visibility wait (lines 25-27) only proves the row exists;
  // the qty cell may still be a pre-refetch stale value.
  let postBuyQty = 0;
  await expect.poll(
    async () => {
      postBuyQty = parseFloat((await jpmQty.innerText()).trim());
      return postBuyQty;
    },
    { timeout: 10_000 },
  ).toBeGreaterThanOrEqual(2);
  ```

- Effect: snapshot is taken only after the post-buy qty has settled to at least 2 (since the buy added exactly 2 shares)
- Closes 2 flaky retries (firefox / webkit on 04-sell). Removes flakiness, restores reproducibility.
- Justification: same `expect.poll` pattern that 10-06 already established in lines 47-52 for the post-sell assertion — apply the same robustness to the snapshot read.

After all three fixes land, the canonical command should produce 21 passed / 0 failed / 0 flaky / exit 0, satisfying ROADMAP SC#3 and unblocking TEST-03 and TEST-04.

### Gaps Summary

ROADMAP Phase 10 has three success criteria. SC#1 (specs exist) ✓ and SC#2 (harness foundation works) ✓ are met. **SC#3 (single command finishes green reproducibly) ✗ is not met** — today's run produced 14 passed / 5 failed / 2 flaky / exit 1.

Three new failure modes have surfaced after Plans 10-06 and 10-07 Task 1:
- **Mode A** — Recharts default Treemap tooltip wrapper intercepts pointer events at the sibling tab-pnl click. The 10-07 `dismissChartTooltip` helper (Escape + mouse-move) does not retract the tooltip on any of the 3 browsers. Production-side fix recommended: `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />`. (3 hard failures.)
- **Mode B** — Cross-project SQLite leak. The compose anonymous volume persists across all 3 browser projects within one `up`, so by the time firefox/webkit run 01-fresh-start, chromium has already debited cash via 03/04/05/06. The absolute `$10,000.00` assertion at line 34 was preserved by 10-06 on the assumption that `workers: 1` makes 01-fresh-start "first" — but `first` is true only WITHIN a project, not ACROSS projects. Test-side fix recommended: drop the absolute assertion. (2 hard failures.)
- **Mode C** — `postBuyQty` snapshot in 04-sell races React Query refetch. The visibility wait at lines 25-27 only proves the row exists; the qty cell may still be a pre-refetch stale value. The `expect.poll` at lines 47-52 recovers on retry, so Playwright reports `flaky` — but flakiness is incompatible with SC#3's `reproducibly`. Test-side fix recommended: stabilise `postBuyQty` via `expect.poll(... >= 2)` before snapshotting. (2 flaky retries.)

Net failure count dropped from the previous run (9 → 5 hard failures + 2 flaky), but reproducibility is still NOT met. A focused gap-closure pass with three small edits — one production line + two test-side edits — closes all three modes.

No items are deferred to a later phase. Phase 10 is the final phase in the roadmap; SC#3 must be met here.

---

*Verified: 2026-04-27T19:35:00Z*
*Verifier: Claude (gsd-verifier)*
*Evidence: /tmp/phase10-gap-closure-harness.log (1169 lines)*
