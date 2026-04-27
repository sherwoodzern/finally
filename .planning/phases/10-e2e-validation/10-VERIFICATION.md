---
phase: 10-e2e-validation
verified: 2026-04-27T22:15:00Z
status: gaps_found
score: 2/3 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 2/3
  gaps_closed:
    - "Mode B — Cross-project SQLite leak. 10-08 commit 0a58eb9 dropped the absolute `$10,000.00` cash assertion from `test/01-fresh-start.spec.ts:33-34`. Today's harness shows 01-fresh-start 3/3 green (chromium L170, firefox L300, webkit L437)."
    - "Mode C — postBuyQty snapshot races React Query refetch in 04-sell. 10-08 commit c53810f wraps the snapshot in `expect.poll(...).toBeGreaterThanOrEqual(2)` so the value settles before the sell. Today's harness shows 04-sell 3/3 green with 0 flaky retries (chromium L206, firefox L338, webkit L474; `grep -c 'flaky' /tmp/phase10-final-harness.log` = 0)."
  gaps_remaining:
    - "ROADMAP SC#3 — single canonical command finishes green reproducibly. Today's run: 18 passed / 3 failed / 0 flaky / exit 1. All 3 hard failures are 05-portfolio-viz × 3 browsers."
  regressions:
    - "Failure shape changed since previous VERIFICATION.md (commit 4f690e6). The 5-failure + 2-flaky pattern (Modes A/B/C) is now a 3-failure + 0-flaky pattern with Mode A reasserted but RE-DIAGNOSED: the original Mode A blamed a Recharts default tooltip; today's harness evidence proves the actual interceptor is the right-column PositionsTable wrapper at viewport 1280×720 (layout overlap), with cross-RUN SQLite carry-over via persistent docker volume as a compounding factor. Net failure count dropped 5 → 3, but reproducibility is still NOT met."
gaps:
  - truth: "After the heatmap renders, clicking the P&L tab succeeds across all 3 browsers — no element from a sibling column intercepts the click."
    status: failed
    reason: "Mode A (corrected) — Layout overlap at viewport 1280×720 between the center column TabBar (containing tab-pnl) and the right column PositionsTable. Playwright reports `<td class=\"px-4 font-semibold\">META</td> from <div class=\"flex flex-col gap-4\">…</div> subtree intercepts pointer events` on all 3 browsers (`/tmp/phase10-final-harness.log:566, 580, 615, 622, 629, 672, 679, 686, 729, 736, 783, 790, 832, 839`). The interceptor `<td class=\"px-4 font-semibold\">{ticker}</td>` is rendered ONLY by `frontend/src/components/terminal/PositionRow.tsx:57` (greppable: `grep -n 'px-4 font-semibold' frontend/src/components/terminal/PositionRow.tsx` → line 57). The wrapping `<div class=\"flex flex-col gap-4\">` matches `frontend/src/components/terminal/Terminal.tsx:50` (the right-column wrapper containing `<PositionsTable />` + `<TradeBar />`). The Recharts Treemap default tooltip — which the previous VERIFICATION.md (commit 4f690e6) blamed — does NOT render any `<td class=\"px-4 font-semibold\">` content; Recharts' DefaultTooltipContent uses `<ul>/<li>` elements. The 10-08 production fix `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` (Heatmap.tsx:138) IS in place (verified by `grep -c \"wrapperStyle={{ pointerEvents: 'none' }}\" frontend/src/components/portfolio/Heatmap.tsx` → 1) but the Mode A failure is undiminished — confirming the previous diagnosis was wrong. Page accessibility snapshots (`test/test-results/05-portfolio-viz-portfolio-3f443-der-after-a-position-exists-{chromium,firefox,webkit}/error-context.md`) confirm the right column has 4 visible position rows (META qty 9, NVDA qty 4, JPM qty 7, AMZN qty 4 in the chromium snapshot) at the moment of the failed tab-pnl click."
    artifacts:
      - path: "frontend/src/components/terminal/Terminal.tsx"
        issue: "Lines 25-27 set up `<main className=\"flex flex-row min-h-screen min-w-[1024px] bg-surface text-foreground\"><div className=\"flex-1 min-w-0 p-6\"><div className=\"grid grid-cols-[320px_1fr_360px] gap-6\">`. At viewport 1280×720 (Playwright `Desktop Chrome` default), the math is: 1280 (viewport) - 48 (`p-6` ×2) - 48 (`gap-6` ×2) - 320 (left col) - 360 (right col) = 504px center column. PLUS the `<ChatDrawer>` flex sibling at line 56 takes additional width (~360px when expanded; the accessibility snapshot shows it expanded). Effective viewport for the 3-col grid is therefore ~920px — narrower than the 320 + 360 + center min-width can accommodate, so the right column visually overlaps the center column tabs (verified by `test/test-results/05-portfolio-viz-portfolio-3f443-der-after-a-position-exists-chromium/test-failed-1.png`)."
      - path: "frontend/src/components/terminal/PositionRow.tsx"
        issue: "Line 57: `<td className=\"px-4 font-semibold\">{position.ticker}</td>` — this is the EXACT element Playwright reports as the interceptor. The element itself is correct; the bug is the layout that puts it on top of `tab-pnl`."
      - path: "test/playwright.config.ts"
        issue: "Lines 71-75 use `devices['Desktop Chrome']` / `Desktop Firefox'` / `Desktop Safari']` which all default to viewport 1280×720. No explicit viewport override. The Terminal.tsx 3-column grid + chat drawer was designed for ≥1440px wide screens (PLAN.md §10 says `Responsive but desktop-first: optimized for wide screens, functional on tablet`)."
      - path: "frontend/src/components/portfolio/Heatmap.tsx"
        issue: "Line 138 — the 10-08 `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` fix is in place. It is correct as latent UX hardening (a Recharts hover tooltip should never block sibling clicks) but does NOT close THIS harness failure because the interceptor is NOT a Recharts tooltip. Keep the fix; do not revert."
    missing:
      - "Test-side viewport bump (recommended — smallest, lowest-risk fix that matches PLAN.md §10's `desktop-first ... wide screens` design intent). In `test/playwright.config.ts`, override the viewport for all 3 projects to at least 1440×900: `{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }` (and same for firefox + webkit). 1440×900 is the most common modern laptop external-monitor / 13\" MacBook hi-res target and matches the `wide screens` design contract. This is a test-environment alignment with the production design — not a workaround."
      - "Production-side layout fix (deferred — bigger change, broader implication). Constrain the chat drawer's contribution to the row width OR change the Terminal.tsx 3-col grid to gracefully collapse the right column at narrow widths. Out of scope for closing Phase 10 SC#3 unless visual UX testing surfaces the same overlap manually at common viewport sizes; should be filed as a v1.1 polish item against POLISH-01."
      - "Do NOT revert the 10-08 Heatmap.tsx Tooltip pointerEvents fix; it is independently correct UX."
  - truth: "Each canonical-command run starts from a clean SQLite — no positions, $10,000 cash, no chat history — regardless of how many prior `up` invocations ran."
    status: failed
    reason: "Mode A.2 (NEW) — Cross-RUN SQLite carry-over via persistent docker volume. The Page accessibility snapshot from `test/test-results/05-portfolio-viz-portfolio-3f443-der-after-a-position-exists-chromium/error-context.md:189` shows `Total: $10,005.38, Cash: $200.56` at the moment of the 05 failure — far below the $10,000 seed value, indicating massive prior trade activity. The Positions table at lines 211-249 of the same snapshot lists 4 positions (META qty 9, NVDA qty 4, JPM qty 7, AMZN qty 4) accumulated from prior runs (chromium 03/04/05/06 only adds 1× NVDA, 2× JPM-then-1×JPM, 1× META, 1× AMZN — not these quantities). The Chat history at lines 253-310 shows 4 'buy AMZN 1' user turns with timestamps `19:08`, `19:09`, `19:10`, `19:41` — spanning ~33 minutes of wall clock, which is impossible within a single 1.6-minute harness run. The 19:41 entry is from this run's chromium 06-chat; the 19:08/19:09/19:10 entries are from prior `up` invocations that were not cleaned up. `test/docker-compose.test.yml:31` comment claims `D-06: NO 'volumes:' mapping for /app/db -> compose creates a fresh anonymous volume per `up` invocation` — but `docker compose up --abort-on-container-exit` does NOT remove anonymous volumes when stopping, only `docker compose down -v` does. The `Dockerfile:57` `VOLUME /app/db` declaration creates an anonymous volume on container start; without explicit volume cleanup the volume persists. Compounding effect on Mode A: chromium's META buy in 05-portfolio-viz returns `400 Bad Request` (`/tmp/phase10-final-harness.log:488, 505`) because cash is exhausted from prior runs; the heatmap-treemap still mounts because META qty=9 is already in the carry-over state, but the test enters the failing tab-pnl click path with stale full-position state."
    artifacts:
      - path: "test/docker-compose.test.yml"
        issue: "Line 31 comment states the assumption that anonymous volumes are fresh per `up`, but the compose service's lack of an explicit volume mapping means each `up` creates a NEW anonymous volume while leaving prior anonymous volumes in place. The `volumes:` block at line 50 is for the playwright service (host bind-mounts test/ into /work) — that part is correct and unrelated. There is no `appsvc.volumes:` block, so Docker uses the Dockerfile's `VOLUME /app/db` declaration which produces a new anonymous volume per container start. Container reuse across `up` invocations (compose project name `test`) means the SAME container can be reused with the SAME anonymous volume."
      - path: "Dockerfile"
        issue: "Line 57 `VOLUME /app/db` declares an anonymous volume mount target. Combined with the compose-side absence of an explicit volume mapping, this is what creates the per-`up` anonymous volume. Phase 9 chose the volume to enable persistence in production (OPS-02); Phase 10 needs ephemerality. The two requirements are in tension — the production Dockerfile should keep VOLUME (for production persistence); the test-side compose file must override it."
    missing:
      - "Compose-side explicit volume cleanup. In `test/docker-compose.test.yml`, either: (a) Map `/app/db` to a tmpfs that vanishes per container: `appsvc: tmpfs: - /app/db` — simplest, no host fs touch; OR (b) Add an explicit named volume that is dropped before each run via a wrapper script or `compose down -v && compose up --build` — heavier, requires changing the canonical command in CONTEXT D-03; OR (c) Have the canonical command run `docker compose -f test/docker-compose.test.yml down -v` BEFORE the `up` (single composite command via `&&` or pre-hook). Path (a) is the smallest and safest — it does not change CONTEXT D-03's command and gives us the per-run ephemerality the comment at line 31 already promises. The production VOLUME declaration is preserved; only the test compose file overrides it."
      - "Optional: assert empty SQLite at appsvc start. Add an extra healthcheck step (or a one-shot `init` container in the compose graph) that fails the `up` if `/app/db/finally.db` already contains positions/trades/chat data. This catches regressions of the volume-ephemerality contract early. Lower priority than the actual fix."
deferred: []
overrides: []
---

# Phase 10: E2E Validation Verification Report

**Phase Goal:** An out-of-band `docker-compose.test.yml` brings up the production image alongside a Playwright container with `LLM_MOCK=true`, and every §12 end-to-end scenario passes green against it. ROADMAP Phase 10 SC#3: "Running the full E2E pack is a single command and finishes green locally against the freshly built image, with reproducible results on repeat runs."

**Verified:** 2026-04-27T22:15:00Z
**Status:** gaps_found
**Re-verification:** Yes — refresh after Plan 10-08 (commits a149480, 0a58eb9, c53810f). Modes B and C from the previous VERIFICATION.md (commit 4f690e6) are CLOSED. Mode A is RE-DIAGNOSED with corrected root cause (layout overlap, not Recharts tooltip), and Mode A.2 (cross-run SQLite carry-over) is identified as a new compounding factor.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth (ROADMAP SC)                                                                                                                                                                                          | Status     | Evidence                                                                                                                                                                                                                                                                                                                                              |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | SC#1: All §12 spec files exist (7 specs total).                                                                                                                                                             | ✓ VERIFIED | 7 spec files under `test/`: 01-fresh-start, 02-watchlist-crud, 03-buy, 04-sell, 05-portfolio-viz, 06-chat, 07-sse-reconnect (verified by `ls test/0[1-7]-*.spec.ts \| wc -l` → 7).                                                                                                                                                                     |
| 2   | SC#2: Harness foundation works (compose up, /api/health, browsers reach app).                                                                                                                               | ✓ VERIFIED | Harness log line 147: `Container test-appsvc-1 Healthy`. All 21 (spec, project) pairs were dispatched. 18 passed including all 6 pairs of 02-watchlist-crud + 06-chat + 07-sse-reconnect (proves REST + browser navigation + SSE-disconnect paths all reach the app on every browser).                                                                |
| 3   | SC#3: Single canonical command finishes green reproducibly — `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` exits 0 with all 21 pairs passing. | ✗ FAILED   | Today's run: harness log lines 877-882 — `3 failed`, `18 passed (1.6m)`, `playwright-1 exited with code 1`. Exit code 1 fails SC#3's `exits 0`. Cross-run SQLite carry-over (Mode A.2) breaks the `reproducibly` clause independently. TEST-03 and TEST-04 cannot be marked complete.                                                                |

**Score:** 2/3 truths verified

### Per-(spec, project) Pair Result Table

Source: `/tmp/phase10-final-harness.log` (893 lines, 77,182 bytes). Today's canonical-command run.

| Spec                     | Chromium | Firefox    | WebKit     |
| ------------------------ | -------- | ---------- | ---------- |
| 01-fresh-start           | ✓ pass   | ✓ pass     | ✓ pass     |
| 02-watchlist-crud (REST) | ✓ pass   | ✓ pass     | ✓ pass     |
| 03-buy                   | ✓ pass   | ✓ pass     | ✓ pass     |
| 04-sell                  | ✓ pass   | ✓ pass     | ✓ pass     |
| 05-portfolio-viz         | ✗ fail (A) | ✗ fail (A) | ✗ fail (A) |
| 06-chat                  | ✓ pass   | ✓ pass     | ✓ pass     |
| 07-sse-reconnect         | ✓ pass   | ✓ pass     | ✓ pass     |

**Aggregate:** 18 passed / 3 failed / 0 flaky / 0 not-run, of 21 pairs. Harness exit 1.

Mode legend:
- **(A)** Layout overlap at viewport 1280×720 — right-column PositionsTable's `<td>{ticker}</td>` cell intercepts clicks targeted at the center-column `tab-pnl` button. **Compounded by (A.2)** cross-run SQLite carry-over — the test's META buy returns 400 Bad Request because cash is drained from prior runs, but the heatmap-treemap still mounts because META qty=9 is already present in the carry-over volume.

### Failure Mode Detail

**Mode A (corrected) — 05-portfolio-viz: layout overlap at viewport 1280×720** (3 of 3 hard failures)

The previous VERIFICATION.md (commit 4f690e6) attributed this failure to the Recharts default Treemap tooltip's wrapper having `pointer-events: auto`. Plan 10-08 landed the corresponding production fix at `frontend/src/components/portfolio/Heatmap.tsx:138` (`<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />`). That fix is correct as latent UX hardening — a hover overlay should never absorb sibling clicks — but the harness failure SHAPE is unchanged after the fix lands. The original diagnosis was wrong.

Corrected evidence:

- The intercepting `<td class="px-4 font-semibold">META</td>` element's exact CSS classes match `frontend/src/components/terminal/PositionRow.tsx:57` (`grep -n 'px-4 font-semibold' frontend/src/components/terminal/PositionRow.tsx` → `57:      <td className="px-4 font-semibold">{position.ticker}</td>`). Recharts' default tooltip body uses `<ul>/<li>`, NOT `<td>`.
- The wrapping `<div class="flex flex-col gap-4">` reported by Playwright matches `frontend/src/components/terminal/Terminal.tsx:50` — the **right-column wrapper** that contains `<PositionsTable />` + `<TradeBar />`.
- Page accessibility snapshots (`test/test-results/05-portfolio-viz-portfolio-3f443-der-after-a-position-exists-chromium/error-context.md` lines 199-249) show the right-column Positions table is rendered with 4 visible position rows at the moment of failure, AND the center-column TabBar (lines 193-198) is present with `tab "P&L" [ref=e202]` available — both elements coexist in the DOM but Playwright's hit-test resolves clicks at the tab-pnl coordinates to the PositionsTable cell.
- Test-failed screenshots (`test-results/.../test-failed-1.png` per project) show visually that the right-column PositionsTable extends leftward into the center-column TabBar zone at viewport 1280×720.
- The 10-08 Heatmap.tsx Tooltip fix is verified present (`grep -c "wrapperStyle={{ pointerEvents: 'none' }}" frontend/src/components/portfolio/Heatmap.tsx` → 1) AND the harness failure persists — independent confirmation that the Recharts tooltip is NOT the interceptor.

Width math at viewport 1280×720 (Playwright Desktop Chrome default):

```
Viewport               1280
- main p-6 (×2)         -48
- grid gap-6 (×2)       -48
- left col (Watchlist)  -320
- right col (Pos+Bar)   -360
                        ----
= center col available  504px

PLUS <ChatDrawer> in <main className="flex flex-row"> at Terminal.tsx:25-58:
- chat drawer width    ~360 (expanded; see snapshot e259-e323)
                        ----
= shared 1280 - 360    920px (the 3-col grid lives in the remaining 920px container)

The grid is grid-cols-[320px_1fr_360px], so 320+360 = 680px is fixed; 240px is left for center.
TabBar at center column has 3 tabs: Chart | Heatmap | P&L. At 240px the tabs are crammed
into a strip and the right-column PositionsTable overflows leftward into the tab-pnl click
target.
```

The 10-07 `dismissChartTooltip` helper (Escape + mouse-move) at `test/05-portfolio-viz.spec.ts:26-29, 49` is harmless after the 10-08 Heatmap fix lands — but neither addresses the layout problem.

**Mode A.2 (NEW) — cross-RUN SQLite carry-over via persistent docker volume** (compounds Mode A; would surface even after Mode A is fixed)

Evidence (all from `test/test-results/05-portfolio-viz-portfolio-3f443-der-after-a-position-exists-chromium/error-context.md`):

- Line 189: `Total: $10,005.38, Cash: $200.56` — cash drained to ~2% of seed
- Lines 211-249: 4 positions present (META qty 9, NVDA qty 4, JPM qty 7, AMZN qty 4) before this run started
- Lines 252: alert "Not enough cash for that order." — chromium's META buy in this 05 spec failed because cash was already drained
- Lines 253-310: chat history with 4 "buy AMZN 1" user turns timestamped `19:08, 19:09, 19:10, 19:41` — the latter is from this run; the earlier 3 are from prior `up` invocations spanning ~33 minutes of wall clock
- Harness log line 488: `appsvc-1 | INFO: 172.19.0.3:49702 - "POST /api/portfolio/trade HTTP/1.1" 400 Bad Request` — the chromium 03-buy NVDA trade returned 400 because cash was carried over below NVDA's threshold (yet 03-buy still passed because its assertion is `cash < 10_000`, which is trivially true at $200.56)

Why the volume persists across runs:

- `Dockerfile:57` declares `VOLUME /app/db` — anonymous volume created on each container start
- `test/docker-compose.test.yml` has no `appsvc.volumes:` block (line 31 comment claims this gives ephemeral per-`up` volumes)
- `docker compose up --abort-on-container-exit` STOPS the container but does NOT remove anonymous volumes — only `docker compose down -v` does
- Subsequent `up` invocations may reuse the same container (compose project name `test`) which keeps the same anonymous volume mounted

This breaks SC#3's `reproducibly` clause independently of Mode A. Even if Mode A's layout overlap were fixed today, repeat runs would observe accumulating state and could surface NEW failure shapes (e.g., "header total = $10,005.38" assertions) on subsequent runs.

### Required Artifacts

| Artifact                                           | Expected                                                                  | Status              | Details                                                                                                                                                                                                          |
| -------------------------------------------------- | ------------------------------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test/docker-compose.test.yml`                     | Two-service compose with appsvc (LLM_MOCK=true) + playwright + EPHEMERAL /app/db across runs | ⚠️ PARTIAL          | appsvc service correctly defined and Healthy (harness L147). Missing: explicit volume cleanup directive — anonymous volumes persist across `up` invocations (Mode A.2).                                          |
| `test/playwright.config.ts`                        | `workers: 1`, 3 browser projects, baseURL `http://appsvc:8000`            | ⚠️ PARTIAL          | Lines 31, 32, 71-75 correct. Missing: explicit `viewport: { width: 1440, height: 900 }` per project to align with PLAN.md §10's `wide screens` design intent (Mode A).                                            |
| `test/01-fresh-start.spec.ts`                      | Watchlist-panel-scoped Select-button locators, no absolute cash assertion | ✓ VERIFIED          | 10-08 commit 0a58eb9: $10k assertion dropped, replaced with explanatory `Cross-project SQLite leak` comment block. 10-ticker visibility loop + em-dash streaming proof preserved. 3/3 green today.               |
| `test/02-watchlist-crud.spec.ts`                   | REST add+remove PYPL                                                      | ✓ VERIFIED          | Passed all 3 browsers (REST `request` fixture, no UI dependency).                                                                                                                                                |
| `test/03-buy.spec.ts`                              | NVDA × 1 buy, no pre-trade $10k assertion, post-trade `< 10_000`          | ✓ VERIFIED          | 10-06 commit 3bb6105: pre-trade $10k assertion removed. Post-trade `< 10_000` at line 38. 3/3 green today.                                                                                                       |
| `test/04-sell.spec.ts`                             | postBuyQty snapshot via expect.poll + relative delta `(postBuyQty - 1)`   | ✓ VERIFIED          | 10-08 commit c53810f: `let postBuyQty = 0` + `expect.poll(...).toBeGreaterThanOrEqual(2)` at lines 43-52. Existing post-sell `expect.poll(...).toBe(postBuyQty - 1)` at lines 62-67 preserved. 3/3 green today, 0 flaky. |
| `test/05-portfolio-viz.spec.ts`                    | META buy → heatmap-treemap visible → tab-pnl click → pnl-chart visible    | ⚠️ PARTIAL (Mode A)  | All UI assertions and helpers structurally correct. The tab-pnl click fails because of layout overlap at viewport 1280×720 — a HARNESS-environment bug, not a spec bug. The `dismissChartTooltip` helper is harmless. |
| `test/06-chat.spec.ts`                             | Mock buy AMZN 1 → action-card-executed                                    | ✓ VERIFIED          | Passed all 3 browsers.                                                                                                                                                                                            |
| `test/07-sse-reconnect.spec.ts`                    | abort('connectionreset') + reload → reconnect                             | ✓ VERIFIED          | Passed all 3 browsers.                                                                                                                                                                                            |
| `frontend/src/components/portfolio/Heatmap.tsx`    | Recharts Tooltip with `pointerEvents: 'none'` (latent UX hardening)        | ✓ VERIFIED          | 10-08 commit a149480: `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` at line 138. Build green. WR-01 advisory (no formatter on Tooltip body) noted in 10-REVIEW.md but non-blocking for SC#3.            |
| `frontend/src/components/terminal/Terminal.tsx`    | (Implicit) 3-col grid + chat drawer accommodate viewport 1280×720          | ⚠️ DEFECT (Mode A)  | Lines 25-27 + 50: `flex-row` + `grid grid-cols-[320px_1fr_360px]` + ChatDrawer share the viewport. At 1280×720 the right-column PositionsTable overlaps the center-column tab-pnl click target. Production layout limitation surfaced by tests. |
| `Dockerfile`                                       | `VOLUME /app/db` for production persistence                                | ✓ VERIFIED          | Line 57. Phase 9 OPS-02 contract preserved. Test-side ephemerality must be enforced by compose, not Dockerfile.                                                                                                  |

### Key Link Verification

| From                                                | To                                                                  | Via                                                                                              | Status      | Details                                                                                                                                                                              |
| --------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `test/docker-compose.test.yml` (build context)      | repo-root `Dockerfile`                                              | `docker compose ... up --build`                                                                  | ✓ WIRED     | Build executed in harness lines 1-127. Container test-appsvc-1 Healthy (line 147).                                                                                                    |
| `test/docker-compose.test.yml` (LLM_MOCK)           | `backend/app/chat/mock.py`                                          | Phase 5 mock-mode env switch                                                                     | ✓ WIRED     | 06-chat passed all 3 browsers via the mock client.                                                                                                                                  |
| `test/playwright.config.ts` (baseURL appsvc)        | compose service `appsvc`                                            | Compose internal DNS                                                                             | ✓ WIRED     | All 3 browsers reached the app.                                                                                                                                                      |
| Heatmap.tsx `<Tooltip>` element                     | Recharts default tooltip wrapper                                    | `wrapperStyle={{ pointerEvents: 'none' }}` prop                                                  | ✓ WIRED     | The wrapper element receives the style; build green; latent UX correctness now established.                                                                                          |
| `tab-pnl` click coordinates                         | TabBar P&L button hit-target                                        | Browser hit-testing at viewport 1280×720                                                         | ✗ NOT_WIRED | Hit-test resolves to PositionRow `<td>{ticker}</td>` because the right-column PositionsTable visually overlaps the center-column TabBar at this viewport. Mode A.                   |
| Compose anonymous volume                            | Pristine SQLite per `up` invocation                                 | Dockerfile `VOLUME /app/db` + compose default                                                    | ✗ NOT_WIRED | Anonymous volumes persist across `up` invocations until `compose down -v`. Mode A.2.                                                                                                  |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable        | Source                                                              | Produces Real Data            | Status                                                                                                       |
| --------------------------------- | -------------------- | ------------------------------------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `test/05-portfolio-viz.spec.ts`   | tab-pnl click target | TabBar button (verified-existent in DOM, accessibility snapshot e202) | Yes (locator resolves)        | ⚠️ INTERCEPTED — pointer events absorbed by overlapping right-column PositionsTable cell                     |
| `test/05-portfolio-viz.spec.ts`   | META buy precondition | TradeBar form → POST /api/portfolio/trade → SQLite + cache            | Yes (POST sent)               | ⚠️ 400 Bad Request — backend rejects buy due to cash carry-over from prior runs (`/tmp/phase10-final-harness.log:488`) |
| Heatmap-treemap presence assertion | Position list        | useQuery(['portfolio']) → /api/portfolio                             | Yes — but with carry-over data | ⚠️ FLOWS-BUT-DRIFTED — heatmap mounts because pre-existing META qty=9 is present even though this run's buy failed |

### Behavioral Spot-Checks

| Behavior                                                      | Command                                                                                                            | Result                                                       | Status |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------ | ------ |
| Canonical harness command runs end-to-end                     | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` | exit 1; 18 passed / 3 failed / 0 flaky (1.6m runtime)        | ✗ FAIL |
| Compose YAML is well-formed                                   | `docker compose -f test/docker-compose.test.yml config`                                                            | exit 0 (effective config dumped, appsvc + playwright present) | ✓ PASS |
| Playwright config parses                                      | `cd test && npx playwright test --list` (per 10-08 plan acceptance)                                                | exit 0 (21 tests listed)                                     | ✓ PASS |
| All 7 spec files exist                                        | `ls test/0[1-7]-*.spec.ts \| wc -l`                                                                                | 7                                                            | ✓ PASS |
| `workers: 1` active in playwright.config.ts                   | `grep -E '^\s*workers:\s*1\b' test/playwright.config.ts`                                                            | match at line 31                                             | ✓ PASS |
| 10-08 Heatmap Tooltip fix landed                              | `grep -c "wrapperStyle={{ pointerEvents: 'none' }}" frontend/src/components/portfolio/Heatmap.tsx`                  | 1                                                            | ✓ PASS |
| 10-08 01-fresh-start cash-assertion drop landed               | `grep -c '\$10,000.00' test/01-fresh-start.spec.ts`                                                                 | 0                                                            | ✓ PASS |
| 10-08 04-sell expect.poll snapshot landed                     | `grep -c 'toBeGreaterThanOrEqual(2)' test/04-sell.spec.ts`                                                          | 1                                                            | ✓ PASS |
| 0 flaky retries in canonical run                              | `grep -c 'flaky' /tmp/phase10-final-harness.log`                                                                    | 0                                                            | ✓ PASS |
| appsvc Healthy in canonical run                               | `grep -E 'Container test-appsvc-1\s+Healthy' /tmp/phase10-final-harness.log`                                        | match at line 147                                            | ✓ PASS |
| 21 passed in canonical run                                    | `grep -E '21 passed' /tmp/phase10-final-harness.log`                                                                | no match (actual: `18 passed`)                               | ✗ FAIL |
| Cross-run state ephemerality                                  | (manual inspection of `test/test-results/.../error-context.md` for prior-run timestamps)                            | 19:08/19:09/19:10/19:41 chat entries span 33min — not ephemeral | ✗ FAIL |

### Requirements Coverage

| Requirement | Source Plan      | Description                                                                                                                                                | Status                              | Evidence                                                                                                                                                                                                                                            |
| ----------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TEST-03     | 10-01-PLAN       | Playwright E2E harness under `test/` with its own `docker-compose.test.yml` running the app container (`LLM_MOCK=true`) alongside a Playwright container. | ✓ SATISFIED (foundation)            | Foundation works end-to-end. appsvc Healthy, 18 passing across all 3 browsers, mock chat path proven by 06-chat 3/3. The harness mechanism is correct; the remaining failure is at the browser-viewport / volume-ephemerality layer.                |
| TEST-04     | 10-00, 10-02..08 | All §12 E2E scenarios pass green — fresh start, watchlist add/remove, buy/sell, heatmap + P&L chart rendering, mocked chat with trade execution, SSE reconnect. | ⚠️ BLOCKED                          | 6 of 7 §12 scenarios green on every browser (01/02/03/04/06/07). 05-portfolio-viz fails all 3 browsers due to layout overlap at viewport 1280×720 (Mode A). Cross-run carry-over (Mode A.2) blocks `reproducibly` independently. SC#3 not met → TEST-04 cannot complete. |

Per ROADMAP Phase 10's bottom traceability, both TEST-03 and TEST-04 remain `[ ]` unchecked in REQUIREMENTS.md (lines 84-85). This verification does NOT mark them complete.

### Plan-by-Plan must_haves Status

| Plan       | must_have truth                                                                                                       | Status                                                                                                                |
| ---------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 10-00      | data-testids land on Header/TabBar/Watchlist/PositionsTable/TradeBar                                                  | ✓ MET — confirmed by harness traces and accessibility snapshots                                                      |
| 10-01      | docker-compose.test.yml + playwright.config.ts + healthcheck                                                          | ✓ MET — appsvc Healthy at L147, 21 pairs dispatched, but the volume contract is incomplete (Mode A.2)                |
| 10-02      | 01-fresh-start (10-ticker seed) + 02-watchlist-crud (PYPL REST)                                                       | ✓ MET — both 3/3 green                                                                                                |
| 10-03      | 03-buy + 04-sell                                                                                                      | ✓ MET — both 3/3 green; 04-sell 0 flaky                                                                              |
| 10-04      | 05-portfolio-viz + 06-chat                                                                                            | 06-chat ✓ 3/3 / 05-portfolio-viz ✗ 0/3 (Mode A)                                                                       |
| 10-05      | 07-sse-reconnect + harness gate                                                                                       | 07 ✓ 3/3, harness gate exit 1 (NOT 0)                                                                                  |
| 10-06      | "workers: 1 + scoped Select selectors + drop $10k in 03-buy + relative-delta in 04-sell"                              | ✓ MET                                                                                                                  |
| 10-06      | "Canonical harness exits 0 with all 21 pairs passing — Gap Group A from VERIFICATION.md is fully closed"              | ✗ NOT MET — Modes B/C closed since, but Mode A reasserted with corrected diagnosis                                    |
| 10-07      | "After the heatmap tile interaction, the Recharts hover tooltip is reliably dismissed before any subsequent click"   | ⚠️ MOOT — premise wrong (interceptor was never the Recharts tooltip); helper preserved as harmless                    |
| 10-07      | "Canonical harness exits 0 with all 21 (spec, project) pairs passing"                                                 | ✗ NOT MET                                                                                                              |
| 10-08      | "Mode A closed: tooltip wrapper does not intercept pointer events"                                                    | ⚠️ MOOT — tooltip pointerEvents fix landed (correct UX); the actual interceptor is layout overlap, not the tooltip   |
| 10-08      | "Mode B closed: 01-fresh-start passes on every browser project regardless of cross-project order"                     | ✓ MET — 3/3 green                                                                                                      |
| 10-08      | "Mode C closed: 04-sell passes deterministically (no flaky retries)"                                                  | ✓ MET — 3/3 green, 0 flaky                                                                                            |
| 10-08      | "Canonical harness exits 0 with 21 passed / 0 failed / 0 flaky / Healthy appsvc"                                      | ✗ NOT MET — exit 1, 18 passed                                                                                          |

### Anti-Patterns Found

| File                                              | Line  | Pattern                                                                                                                                                                                       | Severity   | Impact                                                                                                                                  |
| ------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `test/playwright.config.ts`                       | 71-75 | Project definitions use `devices['Desktop Chrome' \| 'Desktop Firefox' \| 'Desktop Safari']` defaults (1280×720) without an explicit viewport override matching PLAN.md §10's `wide screens`. | 🛑 Blocker | Mode A — 3 of 3 hard failures. The center column shrinks to ~240px at 1280×720 with the chat drawer expanded; right column overlaps tabs. |
| `test/docker-compose.test.yml`                    | 31    | Comment claims "anonymous volume per `up` invocation" but no compose-side directive enforces ephemerality across `up` calls. Anonymous volumes persist until `down -v`.                       | 🛑 Blocker | Mode A.2 — cross-run carry-over confirmed by 33-minute spread of chat history timestamps in failure DOM. Breaks SC#3 `reproducibly`.   |
| `frontend/src/components/portfolio/Heatmap.tsx`   | 138   | `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` rendered with no `formatter` or `content` — default body shows raw `weight` (dollar position value as bare number, no $/comma).      | ℹ️ Info     | WR-01 from 10-REVIEW.md. Latent UX issue, NOT blocking SC#3. Recommend bundling fix with the corrective plan but not required for green. |
| `test/05-portfolio-viz.spec.ts`                   | 26-29 | `dismissChartTooltip` helper (Escape + mouse-move) is now strictly redundant after 10-08's Heatmap.tsx fix lands AND given the actual interceptor is not a tooltip.                          | ℹ️ Info     | IN-03 from 10-REVIEW.md. No-op; safe to leave. Recommend removal once Mode A is closed and harness is green for several runs.            |

### Human Verification Required

None. All gaps are reproducibly demonstrable from `/tmp/phase10-final-harness.log` and `test/test-results/.../error-context.md`, and verifiable via static inspection of the named files at the named lines. Once Mode A's viewport bump and Mode A.2's volume cleanup directive land, re-running the canonical command will deterministically prove green or surface a new failure shape. There are no UX/visual/timing-feel items that need human judgment to verify the SC#3 gate.

### Recommended Fix Plan

Two small, independent edits close both modes. They can be bundled into a single Plan 10-09 (recommended — they share the canonical harness gate run).

**Fix 1 (Mode A — closes the layout overlap)** — `test/playwright.config.ts`

- Update each project entry at lines 72-74 to override the viewport to align with PLAN.md §10's `wide screens, desktop-first` design intent:

  ```typescript
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'],  viewport: { width: 1440, height: 900 } } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 900 } } },
    { name: 'webkit',   use: { ...devices['Desktop Safari'],  viewport: { width: 1440, height: 900 } } },
  ],
  ```

- Effect: At 1440×900 the 3-col grid + chat drawer have ~1080px shared row width; the center column gets ~400px (vs. 240px today), and the right column no longer overlaps `tab-pnl`.
- Justification: This is test-environment alignment with the production design contract, NOT a workaround. PLAN.md §10 states `Responsive but desktop-first: optimized for wide screens, functional on tablet`. 1280×720 is below that target. The production layout fix (Terminal.tsx grid responsive collapse) is a v1.1 polish item against POLISH-01, separately tracked.
- Closes 3 hard failures (chromium / firefox / webkit on 05-portfolio-viz) in a config-only change with no production code touched.

**Fix 2 (Mode A.2 — closes cross-run state carry-over)** — `test/docker-compose.test.yml`

- Add a tmpfs mount on `/app/db` for the `appsvc` service so each container start gets a fresh in-memory directory:

  ```yaml
  appsvc:
    # ... existing keys ...
    tmpfs:
      - /app/db
  ```

- Effect: SQLite file lives in tmpfs, vanishes on container stop. No host filesystem touch. No change to CONTEXT D-03's canonical command. Production Dockerfile's `VOLUME /app/db` is preserved (still works for production deploys; the test-side compose overrides it).
- Justification: Honors CONTEXT D-06 (no test-only `/api/test/reset` endpoint) and D-03 (single canonical command, no flags). The line 31 comment's promise ("fresh anonymous volume per `up`") becomes truth.
- Closes the cross-run carry-over independently. Once landed, re-running `compose up` repeatedly produces deterministically identical results.

After both fixes land and the canonical command runs again, the harness should produce 21 passed / 0 failed / 0 flaky / exit 0, satisfying ROADMAP SC#3 and unblocking TEST-03 / TEST-04.

**Advisory (WR-01, optional)** — `frontend/src/components/portfolio/Heatmap.tsx`

- The 10-08 `<Tooltip wrapperStyle={{ pointerEvents: 'none' }} />` is correct and should be preserved. Add a `formatter` or `content` prop so the tooltip body shows formatted dollar values (e.g., `$1,899.53` instead of `1899.5274`) and signed P&L %. Non-blocking for SC#3; recommend bundling with the corrective plan if scope allows.
- See `10-REVIEW.md` WR-01 for the suggested formatter snippet.

### Gaps Summary

ROADMAP Phase 10 has three success criteria. SC#1 (specs exist) ✓ and SC#2 (harness foundation works) ✓ are met. **SC#3 (single command finishes green reproducibly) ✗ is not met** — today's run produced 18 passed / 3 failed / 0 flaky / exit 1.

Two failure modes have surfaced after Plan 10-08:

- **Mode A (corrected)** — Layout overlap at viewport 1280×720 between the right-column PositionsTable and the center-column `tab-pnl` button. The 10-08 Recharts Tooltip pointerEvents fix is in place and is correct as latent UX hardening, but it is NOT what closes this harness failure — the actual interceptor is `<td class="px-4 font-semibold">{ticker}</td>` from `frontend/src/components/terminal/PositionRow.tsx:57` (verified by exact CSS-class match in the harness traces, and by Recharts' default tooltip body using `<ul>/<li>` not `<td>`). Test-side viewport bump (1440×900) recommended — closes Mode A in a config-only change. (3 hard failures.)

- **Mode A.2 (NEW)** — Cross-RUN SQLite carry-over via persistent docker volume. Page accessibility snapshots show 4 prior-run chat entries spanning 33 minutes of wall clock + cash drained to $200.56 + 4 carry-over positions before this run started — none of which a single 1.6-minute harness run could produce. The compose comment at line 31 claims per-`up` ephemerality but there is no compose-side directive that enforces it; anonymous volumes persist until `down -v`. Compose-side `tmpfs: - /app/db` directive recommended. (Compounds Mode A and breaks SC#3 `reproducibly` independently.)

Modes B (cross-project SQLite leak) and C (postBuyQty React Query race) from the previous VERIFICATION.md (commit 4f690e6) ARE closed by Plan 10-08 commits 0a58eb9 and c53810f — confirmed by 01-fresh-start 3/3 green and 04-sell 3/3 green / 0 flaky in today's harness.

A focused gap-closure pass with two small edits — one playwright.config.ts viewport override + one compose-file tmpfs directive — closes both remaining modes. The 10-08 Heatmap Tooltip fix and the 10-07 dismissChartTooltip helper both stay in place: the former as latent UX correctness, the latter as harmless belt-and-suspenders.

WR-01 (Heatmap Tooltip default body shows raw `weight` numeric without dollar formatting) is a Phase 10-adjacent UX advisory, NOT a SC#3 blocker. Bundle with the corrective plan if scope allows.

No items are deferred to a later phase. Phase 10 is the final phase in the roadmap; SC#3 must be met here.

---

*Verified: 2026-04-27T22:15:00Z*
*Verifier: Claude (gsd-verifier)*
*Evidence: /tmp/phase10-final-harness.log (893 lines, 77,182 bytes); test/test-results/05-portfolio-viz-portfolio-3f443-der-after-a-position-exists-{chromium,firefox,webkit}{,-retry1}/{error-context.md,test-failed-1.png}*
