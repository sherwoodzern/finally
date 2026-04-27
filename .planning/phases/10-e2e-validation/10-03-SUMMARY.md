---
phase: 10
plan: "03"
status: complete
requirements: [TEST-04]
created: 2026-04-27
---

# Plan 10-03 Summary — Buy + Sell E2E Specs

## Outcome

Two Playwright specs landed: `test/03-buy.spec.ts` and `test/04-sell.spec.ts`. Both green on WebKit. Chromium and Firefox remain blocked by the inherited D-10-A HSTS preload upgrade (compose service `app` matches the `.app` HSTS-preloaded TLD, browsers auto-upgrade `http://app:8000/` to `https://...` and SSL fails). Foundation fix is orchestrator-level work (rename compose service + update playwright.config.ts baseURL + override CONTEXT.md D-09).

## Files

- `test/03-buy.spec.ts` — drive TradeBar UI (NVDA × 1), assert position row appears in positions table within 10s, assert header-cash drops below `$10,000` (relative — never absolute, per Pitfall 1).
- `test/04-sell.spec.ts` — buy JPM × 2, sell JPM × 1, assert position-row qty cell text matches `/^\s*1(?:\.0+)?\s*$/` (covers `1`, `1.0`, `1.00`).

## Commits

1. `d76fb4c` — `test(10-03): add 03-buy.spec.ts (NVDA buy — position appears + cash relative)` — initial spec body from plan reference.
2. `20d80c1` — `test(10-03): add 04-sell.spec.ts (JPM buy 2 → sell 1 → qty 1 regex)` — initial spec body from plan reference.
3. `d17cb30` — `test(10-03): apply Rule-1 spec fixes after harness gate` — Rule-1 deviation fixes after harness surfaced strict-mode collisions and a broken word-boundary regex.

## Rule-1 Deviations Applied

**Strict-mode collisions (both specs):**
- `getByText('$10,000.00')` matched both `header-total` and `header-cash` on fresh boot (no positions ⇒ total reads as $10k too). Rescoped to `getByTestId('header-cash')` with `toHaveText`.
- `getByRole('button', { name: 'Select NVDA' })` matched both the watchlist row AND the positions row — NVDA is in the default seed. Same problem with `Select JPM` in 04-sell. Rescoped to `getByTestId('positions-table').getByRole(...)`.

**Quantity regex word-boundary bug (04-sell):**
- Plan's `\bJPM\b.*\b1(?:\.0+)?\b` cannot match the rendered row text `"JPM1$195.02..."` because there is no word boundary between `M` and `1` (both are word chars). Rescoped the assertion to the qty `<td>` cell (column index 1 per `PositionRow.tsx:57-76`) and used `^\s*1(?:\.0+)?\s*$`.

Both fixes rely on `data-testid` hooks that ship from Plan 10-00.

## Verification

- WebKit per-spec smoke (last successful run before sandbox commit denial): both specs PASS, ~5.6s total.
- Chromium + Firefox per-spec: blocked at `page.goto('/')` with `net::ERR_SSL_PROTOCOL_ERROR` / `SSL_ERROR_UNKNOWN`. Trace evidence captured by Plan 10-02 in `test/test-results/01-fresh-start-...-chromium-retry1/trace.zip`.

## Deferred Items

- D-10-A (HSTS rename) — same foundation blocker that 10-02 logged in `.planning/phases/10-e2e-validation/deferred-items.md`. Affects every browser-driven spec. Orchestrator-level fix.

## Sandbox Note

Sub-agent's later `git commit` invocations were denied by the harness sandbox after a long sequence of `docker compose run` calls. The Rule-1 fix-up commit and this SUMMARY were finalized by the orchestrator from the worktree path.
