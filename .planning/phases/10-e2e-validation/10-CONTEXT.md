# Phase 10: E2E Validation - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Browser-driven end-to-end validation that the shipped `finally:latest` Docker image behaves correctly across the seven core demo scenarios from `planning/PLAN.md` §12, run via a self-contained `test/docker-compose.test.yml` that pairs the production app container (with `LLM_MOCK=true`) and a Playwright runner. Single command runs the full suite locally and reproducibly.

**In scope:**
- `test/docker-compose.test.yml` (new file) wiring the app container + Playwright service
- Playwright project configuration under `test/` (config + spec files)
- The seven §12 scenarios as Playwright tests
- One-command run UX

**Out of scope (will be deferred or routed to other phases):**
- Backend unit tests (Phase 5 already shipped 299 pytest)
- Frontend component tests (Phase 8 already shipped 114 Vitest in 20 files)
- New product features
- Adding test-only API endpoints to the production backend
- Hardening the production image for E2E concerns
- Cloud CI integration (local-first per PLAN.md)

</domain>

<decisions>
## Implementation Decisions

### Playwright runtime & topology

- **D-01:** Use the official `mcr.microsoft.com/playwright` image directly in `test/docker-compose.test.yml` — no custom Dockerfile under `test/`. The Playwright service mounts `test/` as a volume so config + spec files live in version control on the host. Pin to a specific tag (e.g. `mcr.microsoft.com/playwright:v1.49.0-jammy`) to keep the suite reproducible.
- **D-02:** Run the full Playwright browser matrix — Chromium, Firefox, and WebKit. The `playwright.config.ts` defines all three projects; the suite executes against each. This is unusual for a single-user demo project but is explicitly user-locked.
- **D-03:** One-command UX is `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright`. App container starts, Playwright service waits for `/api/health` then runs `npx playwright test`, the compose process exits with Playwright's exit code. No wrapper bash script, no `npm run e2e`, no Makefile target. PLAN.md §12 alignment is direct.
- **D-04:** The `app` service in the compose file uses the locally-built `finally:latest` image (built via `build: ..` in the compose context) rather than pulling from a registry. This keeps the test gate local-first and means a fresh `docker compose up --build` always exercises the latest source.

### LLM mock behavior (default — not user-discussed)

- **D-05:** Phase 10 reuses the existing `LLM_MOCK=true` deterministic-canned-response path from Phase 5 unchanged. One scenario in the §12 list — "AI chat (mocked): send a message, receive a response, trade execution appears inline" — exercises whatever the current canned response triggers (a single deterministic chat turn). If the current canned response does NOT trigger an inline trade execution, Phase 10 surfaces that as a gap rather than expanding the LLM mock to scenario-driven fixtures (gap-closure phase 10.1 if needed).

### Test isolation strategy (default — not user-discussed)

- **D-06:** Single Playwright run = single fresh app container = single fresh DB. The named volume `finally-data` is NOT pre-created in the compose file — Docker creates an anonymous volume per `up` invocation, ensuring a clean SQLite state every run. No test-only `/api/test/reset` endpoint in the production backend.
- **D-07:** Within a single run, Playwright tests execute in serial (`workers: 1`) per browser project so scenarios that mutate state (buy, sell, watchlist add/remove) don't race. Cross-browser projects can still run in parallel (Playwright's project-level parallelism) since each project gets its own browser context.
- **D-08:** Each `it()` test asserts state it created itself rather than depending on prior tests' outcomes. Tests use unique tickers where state-isolation matters (e.g., the buy-shares test buys `NVDA` while the sell-shares test sells `JPM`), keeping the seven scenarios independent within a run.

### Test runner configuration

- **D-09:** `test/playwright.config.ts` defines:
  - `testDir: '.'` (specs colocated under `test/`)
  - `baseURL: 'http://appsvc:8000'` (compose-internal DNS — the Playwright container reaches the appsvc service by service name). **D-09 override (post-execution, 2026-04-27):** the original locked value `http://app:8000` triggered Chrome/Firefox HSTS preload upgrade because the bare hostname `app` matches the `.app` HSTS-preloaded TLD. Three independent Wave 2 executors reproduced `net::ERR_SSL_PROTOCOL_ERROR` / `SSL_ERROR_UNKNOWN` with trace evidence (`Non-Authoritative-Reason: HSTS`, `Location: https://app:8000/`). Renamed the compose service `app` → `appsvc` and updated `BASE_URL` accordingly. WebKit was unaffected (no preload list).
  - Three projects: `chromium`, `firefox`, `webkit`
  - `retries: 0` locally, `retries: 1` if `process.env.CI` (covers transient SSE-reconnect-test flakiness without masking real bugs)
  - `reporter: [['list'], ['html', { open: 'never' }]]` so failures dump readable output to compose stdout AND an inspectable HTML report under `test/playwright-report/`
- **D-10:** `wait-for-it` style health-check is wired via the compose file's `depends_on.appsvc.condition: service_healthy` — the appsvc container's existing `/api/health` is wrapped in a HEALTHCHECK in the compose service definition (NOT in the production Dockerfile, which Phase 9 deliberately omits HEALTHCHECK from). The Playwright service waits for the app to be healthy before launching tests.

### Scenario-to-spec mapping

- **D-11:** One spec file per the seven §12 scenarios, granular and self-contained:
  - `01-fresh-start.spec.ts` — default watchlist, $10k, streaming prices
  - `02-watchlist-crud.spec.ts` — add + remove ticker
  - `03-buy.spec.ts` — buy shares, cash decreases, position appears
  - `04-sell.spec.ts` — sell shares, cash updates
  - `05-portfolio-viz.spec.ts` — heatmap + P&L chart render
  - `06-chat.spec.ts` — mocked chat send/response/inline-trade
  - `07-sse-reconnect.spec.ts` — disconnect + reconnect via Playwright route interception (Phase 10's research step should validate the exact interception pattern)
- **D-12:** SSE reconnect test (#07) uses Playwright `page.route('/api/stream/prices', ...)` to abort the stream mid-test, then unroutes to allow reconnection — the cleanest browser-side network failure simulation that avoids touching the backend or container lifecycle.

### Canonical demo data assumptions

- **D-13:** Tests assume the seeded 10-ticker default watchlist exists on first request (per Phase 2's lazy DB init). If a future phase changes the seed, Phase 10 specs will need an update — this is an explicit coupling, not a test-side abstraction.

### Claude's Discretion
- Exact Playwright tag version (D-01) — pick the latest stable as of the implementation date and pin it.
- HTML report path under `test/playwright-report/` (D-09) — confirmed not committed (add to `.gitignore`).
- Detail of selectors used in each spec (data-testid vs role-based) — researcher should survey the existing component library and pick the most stable available pattern.
- Whether to add `test/README.md` documenting how to run the suite.

</decisions>

<specifics>
## Specific Ideas

- "PLAN.md §12 lists exactly seven scenarios" — keep that count visible in the spec file naming so future maintainers can match specs to spec rows at a glance.
- The user wants the full browser matrix even though this is a single-user demo (D-02). Treat that as a deliberate quality bar, not a verification item to second-guess.
- The compose service for the app must build from source (`build: ..`), not pull from a registry — see D-04. This is the only way to test "what was just shipped".

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 10 scope and scenarios
- `planning/PLAN.md` §11 — Docker & Deployment (defines docker-compose.test.yml as part of the production design)
- `planning/PLAN.md` §12 — Testing Strategy (the seven E2E scenarios are listed verbatim)
- `.planning/REQUIREMENTS.md` lines 84-85 — TEST-03 (Playwright + docker-compose.test.yml topology) and TEST-04 (the seven scenarios)
- `.planning/ROADMAP.md` Phase 10 section — Goal and 3-point Success Criteria

### Production image being tested
- `Dockerfile` — multi-stage Node 20 → Python 3.12 image, `finally:latest`. Tests run AGAINST this image; do not modify it.
- `.planning/phases/09-dockerization-packaging/09-01-SUMMARY.md` — image structure, env var handling
- `.planning/phases/09-dockerization-packaging/09-VERIFICATION.md` — Phase 9 verification report. Confirms `/api/health` 1s, `GET /` 12,830 bytes HTML, `/api/stream/prices` data: frames, volume persistence cash 10000 → 9809.98 → 9809.98. This is the baseline Phase 10 must NOT regress.

### LLM mock contract
- `backend/app/chat/` — Phase 5 implementation of the LLM_MOCK=true deterministic-response path. Researcher should read this to confirm the canned response triggers an inline trade (D-05). If it doesn't, the chat scenario test is the canary that surfaces the gap.

### Component test patterns to mirror (NOT to duplicate)
- `frontend/vitest.setup.ts` and existing component tests under `frontend/src/components/**/*.test.tsx` — for selector stability conventions (data-testid usage). Phase 10 should reuse the same data-testids; spec files do not re-test what Vitest already covers.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`finally:latest` Docker image** — Phase 9 ships a working image. Phase 10's compose file builds from source via `build: ..` to always test the latest commit.
- **`/api/health` endpoint** — Phase 1 ships this; Phase 10's compose HEALTHCHECK depends on it for service ordering.
- **`LLM_MOCK=true`** — Phase 5 implementation; one canned response path. Phase 10 sets this as an env override in the compose file's `app` service.
- **Default seed (10 tickers, $10k cash)** — Phase 2 lazy-init seeds these. Phase 10 specs assert against this seed.
- **Existing data-testids in frontend components** — Phase 7 and Phase 8 introduced data-testids during component-test work (e.g., `chat-drawer-slot`, `action-card-{status}`, `chat-message`, position rows). Researcher should inventory these and prefer them over CSS-class or text-content selectors.

### Established Patterns
- **No test-only production endpoints** (D-06) — the project has consistently kept the production API clean of test affordances. Phase 10 honors this.
- **Single-source-of-truth env vars** — `.env`/`.env.example`/--env-file pattern from Phase 9. Phase 10's compose file passes `LLM_MOCK=true` as an env override, NOT a separate `.env.test` file.
- **`uv` for backend deps** (CLAUDE.md) — the app container already runs `uv run uvicorn ...`. Phase 10 doesn't touch the backend deps.

### Integration Points
- `test/docker-compose.test.yml` — NEW file. Mounts `test/` into the Playwright container; builds the `app` service from `Dockerfile` at the repo root.
- `test/playwright.config.ts` — NEW file.
- `test/specs/*.spec.ts` (or `test/0X-*.spec.ts` per D-11) — NEW spec files.
- `.gitignore` — add `test/playwright-report/` and `test/test-results/` (Playwright's default trace/output dirs).
- No changes to `frontend/`, `backend/`, `Dockerfile`, `.dockerignore`, `.env.example`, `scripts/`, `docs/DOCKER.md`, or `README.md` are expected — Phase 10 is purely additive under `test/`.

</code_context>

<deferred>
## Deferred Ideas

- **Scenario-driven LLM mock fixtures** — current Phase 5 mock is single static response. If Phase 10 needs varied chat scenarios, spawn 10.1 gap-closure rather than expanding scope here.
- **Cloud CI integration** — PLAN.md says "single command finishes green locally". A GitHub Actions workflow that runs `docker compose -f test/docker-compose.test.yml up --abort-on-container-exit --exit-code-from playwright` on PRs is a v1.1 hardening item, not a v1.0 phase.
- **Test-only `/api/test/reset` endpoint** — explicitly rejected (D-06). If state isolation becomes a flake source, the answer is `--workers=1` (already chosen) plus per-test unique state, not a backend reset endpoint.
- **Visual regression testing (screenshot diffing)** — the seven §12 scenarios are functional, not visual. Visual regression is a separate Phase that would integrate Playwright's `toHaveScreenshot()` baseline — out of scope.
- **Test-side mobile viewports** — current scope is desktop-only (matches the "desktop-first" demo target in PLAN.md §2). Mobile/tablet variants are a future Phase if needed.

</deferred>

---

*Phase: 10-e2e-validation*
*Context gathered: 2026-04-27*
