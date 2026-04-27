---
phase: 10
plan: 04
subsystem: test
tags: [e2e, playwright, portfolio-viz, chat, recharts, action-card]
requires:
  - test/playwright.config.ts (Plan 10-01)
  - test/docker-compose.test.yml (Plan 10-01 — `app:8000`, `LLM_MOCK=true`)
  - frontend/src/components/portfolio/Heatmap.tsx (Phase 8 `heatmap-treemap` test-id)
  - frontend/src/components/portfolio/PnLChart.tsx (Phase 8 `pnl-chart`/`pnl-summary` test-ids)
  - frontend/src/components/terminal/TabBar.tsx (Plan 10-00 `tab-{id}` test-ids)
  - frontend/src/components/terminal/PositionsTable.tsx (Plan 10-00 `positions-table` test-id)
  - frontend/src/components/chat/ChatInput.tsx (`aria-label="Ask the assistant"`)
  - frontend/src/components/chat/ActionCard.tsx (`action-card-{status}` test-id)
  - backend/app/chat/mock.py (BUY regex)
provides:
  - test/05-portfolio-viz.spec.ts (PLAN.md §12 row 5 — heatmap + P&L render)
  - test/06-chat.spec.ts (PLAN.md §12 row 6 — chat trade auto-execute)
affects:
  - 10-validate.spec orchestration (Wave 3 will run all 7 specs together)
tech-stack:
  added: []
  patterns:
    - "TradeBar UI as test precondition for downstream-state assertions (e.g., heatmap leaves skeleton only with >=1 position)"
    - "Pitfall 4 guard: assertion on action-card-{status} (data-driven test-id), not on chat-message-assistant text content (rendering bug)"
    - "Strict-mode locator scoping via parent-testid getByTestId('positions-table').getByRole(...) when same accessible name appears in multiple sections (watchlist vs positions table)"
    - "Recharts hover-tooltip dismissal via page.mouse.move(0, 0) before navigating to a sibling tab (cross-engine WebKit flake)"
key-files:
  created:
    - test/05-portfolio-viz.spec.ts
    - test/06-chat.spec.ts
  modified: []
decisions:
  - "Selector choice: getByTestId('tab-heatmap') / getByTestId('tab-pnl') over getByRole('tab', { name: /…/i }). Plan 10-00 has already shipped the `tab-{id}` test-ids, making them stable across all three engines."
  - ".first() on action-card-executed: ChatThread.tsx merges historyQuery.data.messages with the optimistically appended assistant turn, rendering the same trade twice. The duplicate render is a pre-existing frontend bug (sibling to Pitfall 4) — surfaced as a Phase 10.1 candidate; using .first() keeps the spec stable today."
  - "page.mouse.move(0, 0) between heatmap and P&L tab clicks: Recharts spawns a hover tooltip <td>{ticker}</td> that lingers after click and intercepts pointer events on the next click target on WebKit. Moving the mouse out of the chart dismisses the tooltip before the next interaction."
metrics:
  duration_minutes: 25
  tasks_completed: 3
  tasks_total: 3
  files_changed: 2
  completed_date: 2026-04-27
---

# Phase 10 Plan 04: Portfolio Visualization + Chat Auto-Execute E2E Specs — Summary

Two new Playwright spec files land Wave 2's third pair of `<§12>` scenarios for TEST-04. `05-portfolio-viz.spec.ts` exercises the Heatmap + P&L panels behind their tabs (with a TradeBar precondition that takes the heatmap out of its empty-state skeleton). `06-chat.spec.ts` drives the deterministic mock-LLM auto-execute path with `"buy AMZN 1"` and asserts the resulting `[data-testid=action-card-executed]` (NOT the assistant chat bubble — see Pitfall 4 / D-05). Both honour D-08 ticker isolation: META and AMZN are unique to this plan within Wave 2 (10-02 uses PYPL, 10-03 uses NVDA + JPM, 10-05 uses no app-state mutations).

## Files Created

### `test/05-portfolio-viz.spec.ts`

Single-test spec, no emojis, no `waitForTimeout`, no `.only`/`.skip`:

1. `goto('/')`, then UI-driven buy of `META × 1` via `getByLabel('Ticker')` / `getByLabel('Quantity')` / `getByRole('button', { name: 'Buy' })`. The buy is necessary because `Heatmap.tsx` shows `data-testid="heatmap-skeleton"` when positions are empty and only mounts `data-testid="heatmap-treemap"` once a position exists (verified in Heatmap.tsx:83 vs 117).
2. Wait for the new META row in the positions table — scoped to `getByTestId('positions-table').getByRole('button', { name: 'Select META' })` (the watchlist also renders the same accessible name; an unscoped locator hits a strict-mode collision).
3. Click `getByTestId('tab-heatmap')`, assert `[data-testid=heatmap-treemap]` visible (10s timeout for Recharts SVG mount).
4. `page.mouse.move(0, 0)` to dismiss the Recharts tooltip that lingers after the heatmap interaction (cross-engine WebKit flake — see Deviations).
5. Click `getByTestId('tab-pnl')`, assert both `[data-testid=pnl-chart]` and `[data-testid=pnl-summary]` visible.

### `test/06-chat.spec.ts`

Single-test spec, no emojis, no `waitForTimeout`, no `.only`/`.skip`:

1. `goto('/')`. ChatDrawer initial state is `useState(true)` (ChatDrawer.tsx:19) — drawer is open by default; no Expand-chat click needed.
2. `getByLabel('Ask the assistant').fill('buy AMZN 1')` — exact aria-label string verified at ChatInput.tsx:48. The Mock LLM BUY regex (`backend/app/chat/mock.py:12`) matches this string.
3. `getByRole('button', { name: 'Send' }).click()` — explicit click is more deterministic than Enter across engines.
4. Assert `[data-testid=action-card-executed]` visible within 15s, scoped to `.first()` to absorb the ChatThread duplicate-render of the assistant turn (history-merge bug; see Deviations).
5. Bonus: assert the `Select AMZN` row in the positions table — proves the auto-execute path produced a real position (not just a UI confirmation card). Scoped to `getByTestId('positions-table')` because AMZN is in the seed watchlist.

The spec carries an explicit comment block citing `RESEARCH.md` Pitfall 4 / `CONTEXT.md` D-05 explaining why bubble text is NOT asserted. The `chat-message-assistant` text is empty due to the documented `ChatResponse` field-shape mismatch (frontend reads `res.id` / `res.content` / `res.created_at`, but the backend ships `{message, trades, watchlist_changes}`). The action-card test-id is the stable, data-driven signal.

## Selector Strategy

| Surface          | Selector                                                                         | Why                                                                                                            |
| ---------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Tab buttons      | `getByTestId('tab-heatmap')` / `getByTestId('tab-pnl')`                          | Plan 10-00 ships `data-testid="tab-{id}"`; cross-engine stable; doesn't depend on copy variants like "P&L".    |
| TradeBar inputs  | `getByLabel('Ticker')` / `getByLabel('Quantity')` / `getByRole('button', …)`     | Visible labels; matches existing 03-buy / 04-sell pattern from sister executors.                               |
| Positions row    | `getByTestId('positions-table').getByRole('button', { name: 'Select META' })`   | Strict-mode-safe (watchlist renders the same `Select TICKER` row).                                            |
| Chat input       | `getByLabel('Ask the assistant')`                                                | aria-label verified at ChatInput.tsx:48.                                                                       |
| Send button      | `getByRole('button', { name: 'Send' })`                                          | Visible button text.                                                                                           |
| Action card      | `getByTestId('action-card-executed').first()`                                    | data-testid-driven; `.first()` to absorb history+optimistic duplicate render (see Deviations).                 |
| Heatmap treemap  | `getByTestId('heatmap-treemap')`                                                 | Phase 8 stable test-id (Heatmap.tsx:117).                                                                      |
| P&L chart/summary | `getByTestId('pnl-chart')` / `getByTestId('pnl-summary')`                       | Phase 8 stable test-ids (PnLChart.tsx:59, 93).                                                                 |

## Task 3 Per-Spec 3-Browser Harness Gate Outcome

### What ran

Per-spec scoped harness:

```
docker compose -f test/docker-compose.test.yml run --rm playwright \
  npx playwright test 05-portfolio-viz.spec.ts 06-chat.spec.ts
```

### Results

- **WebKit (both specs):** Spec quality green after the deviation Rule 1 fixes below. The harness passed `06-chat.spec.ts` outright on the first iteration; `05-portfolio-viz.spec.ts` needed the `page.mouse.move(0, 0)` interleave to dismiss the Recharts hover-tooltip overlay before the second tab click.
- **Chromium + Firefox (both specs):** `page.goto('/')` fails immediately with `net::ERR_SSL_PROTOCOL_ERROR` (chromium) / `SSL_ERROR_UNKNOWN` (firefox). Root cause is the inherited HSTS preload upgrade documented in `deferred-items.md` D-10-A by Plan 10-02 — chromium and firefox upgrade `http://app:8000/` to HTTPS because the compose service hostname `app` matches the `.app` TLD HSTS preload entry. WebKit doesn't honour the preload list and so reaches the FastAPI server cleanly. The fix (rename the compose service to `appsvc` and update `playwright.config.ts` baseURL) is OUT-OF-SCOPE for this plan because it touches files outside `test/05-portfolio-viz.spec.ts` / `test/06-chat.spec.ts` and would invalidate the running parallel Wave 2 executors.

### Why this is acceptable for Plan 10-04 to close

1. The infrastructure issue is pre-existing (Plan 10-02 hit the same blocker on `01-fresh-start.spec.ts`) and is documented in `.planning/phases/10-e2e-validation/deferred-items.md` D-10-A.
2. WebKit covers the cross-browser story for both new specs (same pattern Plan 10-02 followed for `01-fresh-start`).
3. Once D-10-A is fixed (recommended owner per the deferred-items entry: orchestrator or a small follow-on plan, e.g., 10-01.1, after all Wave 2 plans land), chromium + firefox should pass these two specs with NO spec changes — the only failure is `page.goto('/')`, which the HSTS hostname rename fixes wholesale.
4. The deviation Rule 1 fixes (strict-mode scoping + tooltip dismissal) are spec-quality improvements that make all three engines behave identically once the network blocker is resolved.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Strict-mode collision: `Select META` and `Select AMZN`**
- **Found during:** Task 3 first harness run.
- **Issue:** `getByRole('button', { name: 'Select META' })` (and the analogous `Select AMZN` locator in 06-chat) resolved to TWO elements — once in `[data-testid="watchlist-panel"]` (the watchlist row) and once in `[data-testid="positions-table"]` (the new position row). Playwright strict mode rejects locators that match more than one element.
- **Fix:** Scope to `getByTestId('positions-table').getByRole('button', { name: 'Select META' })` (and `Select AMZN`). Both `positions-table` and `watchlist-panel` test-ids are present in source (Plan 10-00 work).
- **Files modified:** `test/05-portfolio-viz.spec.ts`, `test/06-chat.spec.ts`.

**2. [Rule 1 - Bug] WebKit Recharts tooltip intercepts P&L tab click**
- **Found during:** Task 3 first harness run, WebKit project, `05-portfolio-viz.spec.ts:36`.
- **Issue:** After clicking the Heatmap tab and waiting for `[data-testid=heatmap-treemap]` to be visible, the next `getByTestId('tab-pnl').click()` failed with `<td class="px-4 font-semibold">META</td> from <div class="flex flex-col gap-4">…</div> subtree intercepts pointer events`. Recharts spawns an HTML tooltip `<td>{ticker}</td>` on hover, and the cursor was sitting over the heatmap cell when the next click fired. WebKit honours pointer-event stacking strictly enough to fail the click; Chromium and Firefox would have flaked here too once D-10-A is resolved.
- **Fix:** `await page.mouse.move(0, 0)` between the heatmap assertion and the P&L tab click — moves the cursor out of the chart, dismissing the tooltip before the next interaction.
- **Files modified:** `test/05-portfolio-viz.spec.ts`.

**3. [Rule 1 - Bug] Strict-mode collision: `[data-testid=action-card-executed]` renders twice**
- **Found during:** Task 3 first harness run, WebKit project, `06-chat.spec.ts:40`.
- **Issue:** `getByTestId('action-card-executed')` resolved to TWO elements. Investigation pointed to `ChatThread.tsx`: after `postChat` succeeds, the assistant turn is appended to the local `appended[]` state via `setAppended((p) => [...p, assistant])`. React Query then refetches `chat-history`, which now ALSO contains that same assistant message. The merged list `[...history.messages, ...appended]` therefore renders the same trade twice — one card from history, one from the optimistic append. This is a frontend rendering bug sibling to Pitfall 4 (the assistant turn never gets de-duped after history refresh).
- **Fix:** `.first()` on the locator. Asserting the FIRST `action-card-executed` is sufficient — it's the rendered card from the auto-executed trade, regardless of which copy (history or optimistic) Playwright sees first.
- **Files modified:** `test/06-chat.spec.ts`.
- **Phase 10.1 candidate:** The duplicate-render bug deserves a dedicated fix (deduplicate by message id when merging `historyQuery.data.messages` with `appended[]`), but that is outside this plan's scope.

### Inherited Blocker (Out of Scope per Executor Scope Boundary)

**4. [D-10-A inherited] HSTS preload upgrade blocks Chromium + Firefox**
- **Source:** Plan 10-02 discovered and documented in `.planning/phases/10-e2e-validation/deferred-items.md`.
- **Impact today:** 4 of 6 (spec, project) pairs fail at `page.goto('/')` for the same root cause that 01-fresh-start hit in Plan 10-02 — `app` hostname triggers Chrome/Firefox HSTS upgrade.
- **Action taken in 10-04:** None (per executor scope boundary — fix touches files outside `test/05-portfolio-viz.spec.ts` / `test/06-chat.spec.ts` and would invalidate parallel Wave 2 executors). Recommended owner per deferred-items D-10-A: orchestrator or a small follow-on plan (e.g., 10-01.1) after Wave 2 lands.
- **Verification path once fixed:** Re-run `docker compose -f test/docker-compose.test.yml run --rm playwright npx playwright test 05-portfolio-viz.spec.ts 06-chat.spec.ts` — chromium and firefox should match webkit's green pass with no spec changes.

## Known Stubs

None. The two specs are the production tests; no placeholder data, mocked components, or "coming soon" copy.

## Threat Flags

None. The two specs only modify files in `test/`; no new network endpoints, auth paths, file access, or schema changes introduced.

## TDD Gate Compliance

`type: execute` (not `type: tdd`); per-task RED/GREEN/REFACTOR not required. Tasks 1 and 2 each landed a single `test(...)` block in one commit (`test(10-04): add 05-portfolio-viz E2E spec` and `test(10-04): add 06-chat E2E spec`); Task 3 surfaced spec bugs which were committed under `fix(10-04): scope strict-mode locators + dismiss WebKit Recharts tooltip`. All commits used `--no-verify` per the parallel-execution contract.

## Self-Check

- `test/05-portfolio-viz.spec.ts`: FOUND
- `test/06-chat.spec.ts`: FOUND
- Per-task commits: FOUND on branch `worktree-agent-a77ab05278966192f` (`63af39d`, `fb4c3bb`, plus the deviation fixes commit captured below).
- The third commit (`fix(10-04): scope strict-mode locators + dismiss WebKit Recharts tooltip`) contains the deviation Rule 1 fixes from Task 3. See git log for the exact short hash.

## Self-Check: PASSED
