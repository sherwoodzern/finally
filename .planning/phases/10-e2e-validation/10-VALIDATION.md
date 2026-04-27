---
phase: 10
slug: e2e-validation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-27
updated: 2026-04-27
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Integration-tier phase: most validations are shell + curl + Playwright runs against a built `finally:latest` image, not unit tests. Existing pytest (299/299) and Vitest (114/114) suites cover the unit layer; Phase 10 adds the end-to-end browser layer.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `@playwright/test 1.59.1` (pinned) running inside `mcr.microsoft.com/playwright:v1.59.1-jammy`; existing pytest (backend) and Vitest (frontend) carry forward unchanged. |
| **Config file** | `test/playwright.config.ts` (Wave 1 creates) — three browser projects (chromium/firefox/webkit), `baseURL: http://app:8000`, `workers: 3`, `fullyParallel: false`, `retries: process.env.CI ? 1 : 0`, list+html reporter |
| **Quick run command** | Per-spec, lighter: `docker compose -f test/docker-compose.test.yml run --rm playwright npx playwright test {spec} --project=chromium` (no rebuild; ~10–30s) |
| **Full suite command** | Canonical one-command (D-03): `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` (build 150–180s cold + healthcheck wait + 7 specs × 3 browsers ≈ 5–10 min total) |
| **Estimated runtime** | Per-spec quick: ~10–30s · Full suite cold: ~5–10 min · Full suite warm (image cached): ~3–5 min |

---

## Sampling Rate

- **After every task commit:** Run the relevant subset (e.g., compose-config syntax check, playwright.config.ts lint, single-spec `run --rm` invocation, `grep` invariants on the file).
- **After every plan wave:** Wave 1 (10-01) closes with the full `up --build` smoke. Wave 2 plans (10-02, 10-03, 10-04) close with `run --rm playwright` for their two specs across all three browsers (~30–60s per plan). 10-05 closes with the canonical 7-spec × 3-browser full gate.
- **Before `/gsd-verify-work`:** Full suite must exit 0 across all three browser projects.
- **Max feedback latency:** ~30s for per-spec verifies; full integration gate is multi-minute by nature (acknowledged WARNING per checker dimension 8b — unavoidable for an integration-tier phase whose entire purpose IS the full-stack gate).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command (abbreviated) | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------------------|-------------|--------|
| 10-00-01 | 00 | 0 | TEST-04 | T-10-00-01 (mitigated) | Additive `data-testid` on Header.tsx — zero behavior change | grep | `grep -c "data-testid=\"header-cash\"" frontend/src/components/terminal/Header.tsx` outputs ≥ 1 | ❌ W0 (Wave 0 creates) | ⬜ pending |
| 10-00-02 | 00 | 0 | TEST-04 | T-10-00-01 | Additive `data-testid` on TabBar.tsx — zero behavior change | grep | `grep -c 'data-testid={\`tab-' frontend/src/components/terminal/TabBar.tsx` ≥ 1 | ❌ W0 | ⬜ pending |
| 10-00-03 | 00 | 0 | TEST-04 | T-10-00-01 | Additive `data-testid` on Watchlist.tsx, PositionsTable.tsx, TradeBar.tsx | grep + frontend Vitest regression | grep invariants + `cd frontend && npm test -- --run` exits 0 | ❌ W0 | ⬜ pending |
| 10-01-01 | 01 | 1 | TEST-03 | T-10-01-01..06 (mitigated) | `test/package.json` pins `@playwright/test 1.59.1`; no leakage into root or frontend `package.json` | shell + jq | `jq -r '.devDependencies["@playwright/test"]' test/package.json` outputs `1.59.1` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | TEST-03 | T-10-01-02 | `playwright.config.ts` defines 3 browser projects, baseURL=app:8000, workers=3, fullyParallel=false, retries=ci?1:0 | grep + tsc | `grep -E "^\\s*name: '(chromium\\|firefox\\|webkit)'" test/playwright.config.ts \| wc -l` ≥ 3 | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | TEST-03 | T-10-01-03..06 | `docker-compose.test.yml` has `app` (build: ..) + `playwright` services with healthcheck + service_healthy depends_on; LLM_MOCK=true literal; no `--env-file ../.env` | yaml + grep | `docker compose -f test/docker-compose.test.yml config --quiet` exits 0; `grep -q "LLM_MOCK=true" test/docker-compose.test.yml`; `! grep -q "env-file ../.env" test/docker-compose.test.yml` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 1 | TEST-03, TEST-04 | T-10-01-01 | `.gitignore` excludes test artifacts; `test/README.md` documents canonical command; full suite smoke `up --build` exits 0 with at least 1 spec passing across all 3 browsers | shell + integration | `grep -E "^test/(playwright-report\\|test-results\\|node_modules)/$" .gitignore`; `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` exits 0 | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 2 | TEST-04 | T-10-02-01 | `01-fresh-start.spec.ts`: 10-ticker default seed, $10k cash header, streaming dot green within ~5s. No assertion on chat-message-assistant text (per Pitfall 4) | playwright (per-spec) | `docker compose run --rm playwright npx playwright test 01-fresh-start.spec.ts` exits 0 across 3 browsers | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 2 | TEST-04 | T-10-02-02 | `02-watchlist-crud.spec.ts`: PYPL add+remove via `request.post('/api/watchlist')` and DELETE; assert PYPL card appears/disappears | playwright + REST | `docker compose run --rm playwright npx playwright test 02-watchlist-crud.spec.ts` exits 0 | ❌ W0 | ⬜ pending |
| 10-02-03 | 02 | 2 | TEST-04 | T-10-02-01..02 | Wave 2 cohort gate: 01+02 specs pass across all 3 browsers; full suite still green | playwright (multi-spec) | `docker compose run --rm playwright npx playwright test 01 02` exits 0 across browsers | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | TEST-04 | T-10-03-01 | `03-buy.spec.ts`: NVDA × 1 via TradeBar UI; cash decreases, position appears | playwright | `docker compose run --rm playwright npx playwright test 03-buy.spec.ts` exits 0 | ❌ W0 | ⬜ pending |
| 10-03-02 | 03 | 2 | TEST-04 | T-10-03-02 | `04-sell.spec.ts`: JPM × 2 buy then sell × 1; final qty=1, cash transitions correct | playwright | `docker compose run --rm playwright npx playwright test 04-sell.spec.ts` exits 0 | ❌ W0 | ⬜ pending |
| 10-03-03 | 03 | 2 | TEST-04 | T-10-03-01..02 | Wave 2 cohort gate: 03+04 specs pass across all 3 browsers | playwright (multi-spec) | `docker compose run --rm playwright npx playwright test 03 04` exits 0 | ❌ W0 | ⬜ pending |
| 10-04-01 | 04 | 2 | TEST-04 | T-10-04-01 | `05-portfolio-viz.spec.ts`: META buy → heatmap-treemap renders + pnl-chart renders + pnl-summary present | playwright | `docker compose run --rm playwright npx playwright test 05-portfolio-viz.spec.ts` exits 0 | ❌ W0 | ⬜ pending |
| 10-04-02 | 04 | 2 | TEST-04 | T-10-04-01 (Pitfall 4 mitigated) | `06-chat.spec.ts`: mock `"buy AMZN 1"` → `action-card-executed` testid present. MUST NOT assert on chat-message-assistant TEXT (frontend Pitfall 4 — empty bubble) | playwright + multi-line grep guard | `docker compose run --rm playwright npx playwright test 06-chat.spec.ts` exits 0; `! grep -A2 "chat-message-assistant" test/06-chat.spec.ts \| grep -qE "toContainText\\|toHaveText"` (multi-line — checker W4 fix) | ❌ W0 | ⬜ pending |
| 10-04-03 | 04 | 2 | TEST-04 | T-10-04-01 | Wave 2 cohort gate: 05+06 specs pass across all 3 browsers | playwright (multi-spec) | `docker compose run --rm playwright npx playwright test 05 06` exits 0 | ❌ W0 | ⬜ pending |
| 10-05-01 | 05 | 2 | TEST-04 | T-10-05-01..05 (mitigated) | `07-sse-reconnect.spec.ts`: `context.route('**/api/stream/prices', r => r.abort('connectionreset'))` → `page.reload()` → connection-status dot transitions yellow/red → `context.unroute()` → dot returns green within 15s | playwright | `docker compose run --rm playwright npx playwright test 07-sse-reconnect.spec.ts` exits 0 across 3 browsers (WebKit may flake — retry once per CI config) | ❌ W0 | ⬜ pending |
| 10-05-02 | 05 | 2 | TEST-04 | T-10-05-01 | Closing 21-pair gate (7 specs × 3 browsers) — proves ROADMAP SC#1, SC#2, SC#3 | integration | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` exits 0 | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `bash` (system) — for compose invocation and grep verifies
- [x] `docker` CLI (Docker Desktop or Docker Engine) — build/run finally:latest + Playwright services
- [x] `node` ≥ 20 (host or Playwright container) — `npm ci` inside Playwright service
- [x] Existing `pytest` (backend) + `vitest` (frontend) infrastructure carries forward — Phase 10 does NOT add unit tests; it adds the browser-driven E2E layer.
- [x] `@playwright/test 1.59.1` installed via `npm ci` inside the Playwright container at runtime (NOT pre-installed on the host) — keeps browser deps out of the production image per PLAN.md §12.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| First-run image pull (~2 GB) UX | TEST-03 | Visible to the user, not testable in headless CI | After committing 10-01, run `docker compose -f test/docker-compose.test.yml up --build` once and confirm the user sees a clear progress indicator from Docker pulling the Playwright image. |
| Browser-specific timing of SSE reconnect | TEST-04 (scenario 7) | WebKit's EventSource implementation has historically had `text/event-stream` quirks; reconnect timing may vary by ~500ms across browsers — automated retries cover this but visual confirmation desirable for first run | Run `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` and inspect `test/playwright-report/index.html` for the 07-sse-reconnect spec across all three browser projects. |

All other phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify (no MISSING references)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 dependencies covered (Docker + node + existing pytest/Vitest)
- [x] No watch-mode flags (Playwright runs headless one-shot via `npx playwright test` — no `--watch`)
- [⚠️] Feedback latency < 30s: per-task quick verifies meet this; full integration-gate verifies (10-01-04, 10-05-02) are multi-minute by nature — accepted as inherent to integration-tier phase (checker dimension 8b WARNING acknowledged)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-27 (post plan-checker pass with 0 blockers)

---

## Notes

- The 4 plan-checker warnings (W1-W4) were reviewed and dispositioned: W1 (this VALIDATION.md scaffold) addressed by filling in the per-task map above; W2 (10-01 Task 4 over-bundling) accepted as cosmetic — sub-steps are well-sequenced; W3 (multi-minute integration verifies) accepted as inherent to phase purpose; W4 (single-line grep in 10-04 Task 2) addressed inline above by switching to multi-line `grep -A2 ... | grep -qE` form.
- The 3 plan-checker info items (selector fallback paths, frontend test-id additions in 10-00, brittle backslash-escape in 10-00 Task 2) are documented in 10-CONTEXT.md, 10-RESEARCH.md, and 10-PATTERNS.md respectively; no action required.
- Phase 10 makes ZERO modifications to production source (Dockerfile, .dockerignore, backend/, .env.example, scripts/, docs/DOCKER.md, README.md) EXCEPT 10-00's research-recommended additive `data-testid` lines on five `frontend/src/components/terminal/*.tsx` files. Threat model T-10-00-01 explicitly accepts this as a discretionary deviation from CONTEXT.md "purely additive under test/" line 134.
