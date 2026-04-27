---
status: partial
phase: 09-dockerization-packaging
source: [09-VERIFICATION.md]
started: 2026-04-27T15:24:18Z
updated: 2026-04-27T15:24:18Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Windows-host UAT for PowerShell scripts (start_windows.ps1, stop_windows.ps1)
expected: Same idempotency + volume-preserving stop behavior as the bash counterparts; double-clicking start_windows.ps1 (or invoking from PowerShell 5.1+) builds the image (if missing), runs container with finally-data:/app/db + 8000:8000 + --env-file .env, and opens default browser; -Build forces rebuild; -NoOpen suppresses browser; stop_windows.ps1 stops + removes container while preserving volume; running stop twice exits 0.
result: [pending]
why_human: pwsh is not installed on the integration-test host (macOS), so PowerShell scripts were validated by structural grep only (parity table, switches, no-PS7-only operators, no docker volume rm). The runtime contract on a real Windows host is not exercised by automated checks.

### 2. Browser auto-open behavior on macOS / Linux start_mac.sh success
expected: After `bash scripts/start_mac.sh` (no flags), default browser opens to http://localhost:8000; with `--no-open`, browser does NOT open.
result: [pending]
why_human: macOS `open` and Linux `xdg-open` rely on a desktop session; cannot be asserted in headless CI or sandboxed shells. The integration test (09-03 Task 3) ran exclusively with `--no-open` and so did not exercise the auto-open path.

### 3. Visual UI on http://localhost:8000 (after `bash scripts/start_mac.sh`)
expected: The dark-theme terminal loads with a 10-ticker watchlist (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX), $10,000 cash in the header, prices streaming with green/red flash on change, sparklines accumulating, the chart area renders a selected ticker, the portfolio heatmap and P&L chart render, the trade bar accepts orders, and the AI chat panel is visible (and surfaces a 502 from /api/chat with the empty default OPENROUTER_API_KEY).
result: [pending]
why_human: Visual appearance, real-time price-flash CSS animations, sparkline rendering, and chat-panel UX cannot be asserted from curl. The container was confirmed to serve 12,830 bytes of HTML containing `<html lang="en" class="dark">` (Plan 09-03 Task 3 step 3); but actual rendered correctness is a human-eyes check.

### 4. Cross-arch build (linux/amd64 vs linux/arm64) on the user's primary host architecture
expected: `docker build -t finally:latest .` succeeds on the user's host arch (typically Apple Silicon arm64 or Intel/AMD amd64).
result: [pending]
why_human: Cross-arch buildx is deferred per VALIDATION manual section (Phase 9 v2 hardening). Spot-check on the user's primary architecture only. Already PASSED on macOS Apple Silicon during Plan 09-01 cold build (image hash `07a61744cb59`, 564 MB) but documented here for completeness.

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
