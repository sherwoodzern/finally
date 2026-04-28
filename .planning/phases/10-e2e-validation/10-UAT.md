---
status: complete
phase: 10-e2e-validation
source:
  - 10-00-SUMMARY.md
  - 10-01-SUMMARY.md
  - 10-02-SUMMARY.md
  - 10-03-SUMMARY.md
  - 10-04-SUMMARY.md
  - 10-05-SUMMARY.md
  - 10-06-SUMMARY.md
started: 2026-04-27T19:30:22Z
updated: 2026-04-28T00:00:00Z
result: 9/9 pass — canonical harness reproduced `21 passed (24.6s)` exit 0 x 2 consecutive runs, 0 failed, 0 flaky (logs at /tmp/phase10-final-harness.log + /tmp/phase10-final-harness-rerun.log). Verified by v1.0-MILESTONE-AUDIT.md §3.
---

## Current Test

[testing complete — 9/9 pass via canonical harness]

## Tests

### 1. Cold Start Smoke Test
expected: Canonical command builds the image cleanly, appsvc container reports Healthy, Playwright reports `Running 21 tests using 1 worker` (proves SQLite seed + /api/health + workers=1 + spec auto-discovery all wired correctly from a fresh state).
result: pass (canonical harness 21/21 green x 2 consecutive runs, 0 failed, 0 flaky — see v1.0-MILESTONE-AUDIT.md §3)

### 2. 01-fresh-start spec passes on all 3 browsers
expected: Default 10-ticker watchlist (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) renders, header-cash reads $10,000.00, AAPL row shows a streaming price (no em-dash within 10s). Spec passes on chromium, firefox, and webkit.
result: pass (canonical harness 21/21 green x 2 consecutive runs, 0 failed, 0 flaky — see v1.0-MILESTONE-AUDIT.md §3)

### 3. 02-watchlist-crud spec passes on all 3 browsers
expected: POST /api/watchlist with PYPL returns status `added` (or `exists`), GET shows PYPL in list, DELETE returns `removed` (or `not_present`), and final GET no longer contains PYPL — leaving the watchlist back at the seed-only state. Spec passes on chromium, firefox, and webkit.
result: pass (canonical harness 21/21 green x 2 consecutive runs, 0 failed, 0 flaky — see v1.0-MILESTONE-AUDIT.md §3)

### 4. 03-buy spec passes on all 3 browsers
expected: Buy NVDA × 1 via TradeBar UI; positions table gains an NVDA row within 10s; header-cash drops below $10,000 (relative assertion). Spec passes on chromium, firefox, and webkit.
result: pass (canonical harness 21/21 green x 2 consecutive runs, 0 failed, 0 flaky — see v1.0-MILESTONE-AUDIT.md §3)

### 5. 04-sell spec passes on all 3 browsers (no flakiness)
expected: Buy JPM × 2, then sell JPM × 1; post-sell qty cell text equals `postBuyQty - 1` (relative delta). Spec passes deterministically on chromium, firefox, and webkit — no `flaky` line in the harness summary.
result: pass (canonical harness 21/21 green x 2 consecutive runs, 0 failed, 0 flaky — see v1.0-MILESTONE-AUDIT.md §3)

### 6. 05-portfolio-viz spec passes on all 3 browsers
expected: Buy META × 1; click `tab-heatmap`, treemap renders (heatmap-treemap visible); dismiss any lingering Recharts hover tooltip; click `tab-pnl`, both pnl-chart and pnl-summary render. Spec passes on chromium, firefox, and webkit.
result: pass (canonical harness 21/21 green x 2 consecutive runs, 0 failed, 0 flaky — see v1.0-MILESTONE-AUDIT.md §3)

### 7. 06-chat spec passes on all 3 browsers
expected: Send "buy AMZN 1" through ChatInput; mocked LLM auto-executes the trade; an `action-card-executed` element appears in the chat thread. Spec passes on chromium, firefox, and webkit.
result: pass (canonical harness 21/21 green x 2 consecutive runs, 0 failed, 0 flaky — see v1.0-MILESTONE-AUDIT.md §3)

### 8. 07-sse-reconnect spec passes on all 3 browsers
expected: Initial ConnectionDot reads `SSE connected`; abort the SSE stream via `context.route(...abort('connectionreset'))` and reload; dot flips to `SSE reconnecting` or `SSE disconnected`; unroute and dot returns to `SSE connected`. Spec passes on chromium, firefox, and webkit.
result: pass (canonical harness 21/21 green x 2 consecutive runs, 0 failed, 0 flaky — see v1.0-MILESTONE-AUDIT.md §3)

### 9. Canonical-command 21/21 green gate (ROADMAP SC#3)
expected: The single canonical command `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` exits 0 with `21 passed`, no `N failed` line where N>0, and no `flaky` retries — reproducibly. This is the authoritative ROADMAP Phase 10 SC#3 gate.
result: pass (canonical harness 21/21 green x 2 consecutive runs, 0 failed, 0 flaky — see v1.0-MILESTONE-AUDIT.md §3)

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
