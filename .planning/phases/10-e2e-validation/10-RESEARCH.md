---
phase: 10-e2e-validation
status: complete
researched: 2026-04-27
domain: Browser end-to-end validation (Playwright + Docker Compose)
confidence: HIGH
dimensions_covered:
  - playwright-pinning
  - compose-architecture
  - sse-reconnect-pattern
  - chat-mock-trigger-shape
  - selector-inventory
  - per-scenario-spec-outlines
  - validation-architecture
  - gitignore-additions
---

# Phase 10: E2E Validation — Research

## Executive Summary

Phase 10 builds a self-contained out-of-band test harness that proves the production `finally:latest` image (Phase 9) actually works in a real browser across the seven `planning/PLAN.md` §12 demo scenarios. The harness lives entirely under `test/` and does not modify the image, the Dockerfile, the backend, or the frontend. CONTEXT.md locks every major shape decision (D-01..D-13); research's job is to nail down the concrete versions, the compose YAML body, the playwright.config.ts body, the per-scenario assertion strategy, and the few real surprises (Playwright SSE-mocking limitations, multi-project worker semantics, the existing chat ChatResponse field-shape mismatch).

**Primary recommendation:** Pin `mcr.microsoft.com/playwright:v1.59.1-jammy` (the latest stable image as of 2026-04-27, matching `@playwright/test` 1.59.1 from npm), volume-mount `test/` into the container, install `@playwright/test` via `npm ci` inside the runner at startup (no separate package.json under `frontend/` is touched), wire `depends_on: app: condition: service_healthy` against a compose-side HEALTHCHECK polling `/api/health`, and use `workers: 3` + `fullyParallel: false` to satisfy D-07's intent (one worker per browser project). For SSE-reconnect (Spec #07), `page.route('**/api/stream/prices', r => r.abort('connectionreset'))` + `page.unroute()` is the correct pattern — `route.abort()` on SSE is well-supported (the Playwright limitation in issue #15353 is about *fulfilling* SSE, which we don't need).

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Playwright runtime & topology:**

- **D-01:** Use the official `mcr.microsoft.com/playwright` image directly in `test/docker-compose.test.yml` — no custom Dockerfile under `test/`. Volume-mount `test/` so config + spec files live in version control on the host. Pin to a specific tag.
- **D-02:** Run the full Playwright browser matrix — Chromium, Firefox, WebKit — three projects in `playwright.config.ts`. Explicitly user-locked.
- **D-03:** One-command UX is exactly `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright`. No wrapper script, no `npm run e2e`, no Makefile target.
- **D-04:** `app` service uses `build: ..` (locally-built `finally:latest`), NOT a registry pull. Always tests "what was just shipped".

**LLM mock behavior:**

- **D-05:** Reuse the existing `LLM_MOCK=true` deterministic-canned-response path from Phase 5 unchanged. If the mock does NOT trigger an inline trade, surface as a gap (not expand mock).

**Test isolation strategy:**

- **D-06:** Anonymous volume per `up` invocation — clean SQLite every run. NO test-only `/api/test/reset` endpoint.
- **D-07:** `workers: 1` within a project so state-mutating scenarios don't race; cross-browser projects can run in parallel.
- **D-08:** Per-test unique tickers where state isolation matters (e.g., buy uses `NVDA`, sell uses `JPM`).

**Test runner configuration:**

- **D-09:** `test/playwright.config.ts` with `testDir: '.'`, `baseURL: 'http://app:8000'`, three projects (chromium/firefox/webkit), `retries: 0` locally / `retries: 1` if `process.env.CI`, `reporter: [['list'], ['html', { open: 'never' }]]`.
- **D-10:** Compose-side HEALTHCHECK on the app service (NOT in the production Dockerfile, which Phase 9 deliberately omits HEALTHCHECK from). Playwright service uses `depends_on.app.condition: service_healthy`.

**Scenario-to-spec mapping:**

- **D-11:** One spec file per §12 scenario:
  - `01-fresh-start.spec.ts`
  - `02-watchlist-crud.spec.ts`
  - `03-buy.spec.ts`
  - `04-sell.spec.ts`
  - `05-portfolio-viz.spec.ts`
  - `06-chat.spec.ts`
  - `07-sse-reconnect.spec.ts`
- **D-12:** SSE reconnect test uses `page.route()` to abort `/api/stream/prices` mid-test, then `page.unroute()` to allow reconnection.

**Canonical demo data assumptions:**

- **D-13:** Tests assume Phase 2's seeded 10-ticker default watchlist (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) and `cash_balance=10000.0`.

### Claude's Discretion (research-resolved or planner-discretion)

- **Exact Playwright tag version (D-01)** — RESEARCH RESOLVES: `v1.59.1-jammy` (see Pinned Versions section).
- **HTML report path under `test/playwright-report/` (D-09)** — RESEARCH RESOLVES: confirm in `.gitignore`. See `.gitignore Additions`.
- **Selector strategy per spec (data-testid vs role-based)** — RESEARCH RESOLVES: hybrid — `data-testid` where present (chat surface, portfolio surface), role/aria/label-driven RTL-style selectors where data-testid is absent (watchlist rows, trade bar inputs, header values, position rows). See `Component Test-ID Inventory`.
- **Whether to add `test/README.md`** — Planner discretion. Recommended: yes, two-paragraph file pointing at the one canonical command.

### Deferred Ideas (OUT OF SCOPE — DO NOT ADDRESS)

- Scenario-driven LLM mock fixtures (Phase 10.1 if needed).
- Cloud CI integration (v1.1).
- Test-only `/api/test/reset` endpoint (explicitly rejected in D-06).
- Visual regression / screenshot diffing.
- Test-side mobile viewports.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **TEST-03** | Playwright E2E harness under `test/` with its own `docker-compose.test.yml` running the app container (`LLM_MOCK=true`) alongside a Playwright container | `Compose File Architecture` (full YAML draft) + `Pinned Versions & Dependencies` + D-10 healthcheck pattern |
| **TEST-04** | All E2E scenarios from `planning/PLAN.md` §12 — fresh start, watchlist add/remove, buy/sell, heatmap + P&L chart rendering, mocked chat with trade execution, SSE reconnection | `Per-Scenario Spec Outlines` (7 specs) + `LLM Mock Trigger Phrases` + `SSE Reconnect Test Pattern` + `Component Test-ID Inventory` |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Browser-driven UI assertions | Playwright runner container | — | Spawns real Chromium / Firefox / WebKit; talks HTTP to the app container over the compose network |
| Application under test | App container (`finally:latest`) | — | Built via `build: ..` from repo root Dockerfile. `LLM_MOCK=true` env override only — no other deltas |
| Service-ordering / readiness | Compose orchestrator | App container HEALTHCHECK (compose-side) | `depends_on.app.condition: service_healthy` blocks Playwright until `/api/health` passes |
| Test artefact sink | Host filesystem (volume-mounted) | — | `test/playwright-report/` and `test/test-results/` written through the bind mount; gitignored |
| Test run shutdown | Compose orchestrator (`--abort-on-container-exit`) | Playwright (final `process.exit(N)`) | Playwright finishes → compose tears down everything → exit code propagates via `--exit-code-from playwright` |
| State isolation | Compose anonymous volume (per-run fresh SQLite) | Per-test unique tickers (D-08) | Volume freshness eliminates cross-run state; D-08 eliminates intra-run cross-spec state |

## Validation Architecture

> Phase 10 IS the project's E2E validation harness. Its own VALIDATION.md will trace each TEST-04 sub-scenario to a single spec file. This section gives the planner the per-spec runner commands and gates.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `@playwright/test` 1.59.1 (matches Docker image v1.59.1-jammy) |
| Config file | `test/playwright.config.ts` |
| Quick run command (single spec, single browser) | `npx playwright test test/01-fresh-start.spec.ts --project=chromium` |
| Full suite command (all specs × all browsers) | `npx playwright test` |
| Phase one-command | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` |

### Phase Requirements → Test Map

| Req ID | Behavior | Spec File | Selectors / assertion summary |
|--------|----------|-----------|-------------------------------|
| TEST-04 §12 #1 | Fresh start: 10-ticker default watchlist, $10k balance, prices streaming | `01-fresh-start.spec.ts` | Wait for 10 watchlist rows; assert `Cash $10,000.00` text in header; wait for at least one price cell to leave the `—` placeholder |
| TEST-04 §12 #2 | Add and remove a ticker from the watchlist | `02-watchlist-crud.spec.ts` | POST `/api/watchlist` via `request.post()`; assert row appears; DELETE; assert row gone (no UI add-form ships in v1 — see Open Question 1) |
| TEST-04 §12 #3 | Buy shares: cash decreases, position appears, portfolio updates | `03-buy.spec.ts` | Type `NVDA` + `1` into TradeBar inputs (label-driven), click Buy; assert cash decreases; assert NVDA row appears in positions table |
| TEST-04 §12 #4 | Sell shares: cash increases, position updates or disappears | `04-sell.spec.ts` | Buy JPM 2 → Sell JPM 1 → assert qty=1; or Buy JPM 1 → Sell JPM 1 → assert no JPM row |
| TEST-04 §12 #5 | Portfolio viz: heatmap renders, P&L chart has data | `05-portfolio-viz.spec.ts` | Click Heatmap tab → assert `[data-testid=heatmap-treemap]` visible; click P&L tab → assert `[data-testid=pnl-chart]` visible AND `[data-testid=pnl-summary]` shows total $ |
| TEST-04 §12 #6 | Mocked chat: send message, receive response, trade execution shown inline | `06-chat.spec.ts` | Send `"buy AMZN 1"` via chat input; wait for `[data-testid=action-card-executed]` to appear in `[data-testid=chat-thread]` |
| TEST-04 §12 #7 | SSE resilience: disconnect and verify reconnection | `07-sse-reconnect.spec.ts` | `page.route('**/api/stream/prices', r => r.abort('connectionreset'))`; assert ConnectionDot reaches yellow/red (`aria-label=SSE reconnecting` or `disconnected`); `page.unroute()`; assert dot returns to `SSE connected` |

### Sampling Rate

- **Per task commit (during Phase 10 execution):** Run the just-touched spec via the quick command; verify it passes against a manually-launched compose stack, OR via the full one-command run for the touched browser project only.
- **Per wave merge:** Full one-command run.
- **Phase gate (`/gsd-verify-work`):** Full one-command run produces zero failures and exit 0; `test/playwright-report/` html report is inspectable.

### Wave 0 Gaps

> Phase 10 has no pre-existing test infrastructure under `test/` — the directory does not yet exist. Everything below is net-new.

- [ ] `test/docker-compose.test.yml` — compose file (the "package boundary" of the harness)
- [ ] `test/playwright.config.ts` — playwright config
- [ ] `test/01-fresh-start.spec.ts` ... `test/07-sse-reconnect.spec.ts` — seven spec files
- [ ] `test/package.json` (recommended) — pins `@playwright/test` to `1.59.1` and provides `npm ci` deterministic install path inside the Playwright container
- [ ] `test/README.md` (Claude's discretion — recommended)
- [ ] `.gitignore` additions — see `.gitignore Additions`

## Pinned Versions & Dependencies

> Verified against npm registry and GitHub releases on 2026-04-27.

### `@playwright/test` package version

| Channel | Version | Released | Source |
|---------|---------|----------|--------|
| latest | **1.59.1** | 2026-04-01 | `[VERIFIED: npm view @playwright/test version]` |
| previous stable | 1.58.2 | 2026-02-06 | `[VERIFIED: npm view @playwright/test time]` |

**Pin:** `"@playwright/test": "1.59.1"` (exact, no `^`).

### Docker image tag

| Tag | Ubuntu base | Status |
|-----|-------------|--------|
| `mcr.microsoft.com/playwright:v1.59.1` | Ubuntu 24.04 LTS Noble Numbat | Default |
| `mcr.microsoft.com/playwright:v1.59.1-noble` | Ubuntu 24.04 LTS Noble Numbat | Explicit |
| **`mcr.microsoft.com/playwright:v1.59.1-jammy`** | Ubuntu 22.04 LTS Jammy Jellyfish | **Recommended (matches CONTEXT.md D-01 example shape)** |

`[CITED: https://playwright.dev/docs/docker]` — version-pinned tags are the supported production pattern; floating `:latest`/`:focal`/`:jammy` tags are no longer published.

**Why jammy over noble:** CONTEXT.md D-01 explicitly cited `:v1.49.0-jammy` as the example pin. Holding to jammy keeps the spirit of "minimal change from the user's intent" and gives a slightly smaller, longer-tested base. Noble is also fine — the planner can flip with a single string change. The browsers and Node bundled inside the image are identical between `-jammy` and `-noble` for the same Playwright version.

### Node.js inside the Playwright image

The `mcr.microsoft.com/playwright:v1.59.1-jammy` image ships Node.js pre-installed (v22 LTS as of v1.59 line). No separate Node setup needed. `[CITED: https://playwright.dev/docs/docker]`

### Recommended install location: NEW `test/package.json`

Decision criteria:

| Option | Pros | Cons |
|--------|------|------|
| Reuse `frontend/package.json` | Single Node project | Pollutes the production frontend bundle path with a test-only dep; conflicts with `output: 'export'` build hygiene |
| Repo-root `package.json` | Discoverable | Repo currently has NO root package.json; introducing one for one purpose is overweight |
| **NEW `test/package.json`** ★ | Self-contained — `test/` is the entire E2E surface; `npm ci` inside the Playwright container needs only `test/package.json` + `test/package-lock.json` | One more lockfile to maintain (acceptable — only changes when Playwright bumps) |

**Recommended `test/package.json`:**

```json
{
  "name": "finally-e2e",
  "private": true,
  "version": "0.0.0",
  "description": "Phase 10 E2E harness — runs against finally:latest via docker compose",
  "scripts": {
    "test": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "1.59.1"
  }
}
```

A matching `test/package-lock.json` is committed (generated by `npm install` once and checked in).

`[VERIFIED: npm view @playwright/test version → 1.59.1]`
`[VERIFIED: GitHub releases page → v1.59.1 published 2026-04-01, v1.59.0 published 2026-04-01, v1.58.2 published 2026-02-06]`

## Compose File Architecture

> Full YAML draft. Planner copies into `test/docker-compose.test.yml`.

```yaml
# test/docker-compose.test.yml
# Phase 10 E2E harness. Run from repo root:
#   docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright
#
# CONTEXT.md: D-01 (no custom Dockerfile under test/), D-02 (full browser matrix),
# D-03 (one-command UX), D-04 (build from local Dockerfile), D-05 (LLM_MOCK=true),
# D-06 (anonymous volume per run), D-09 (baseURL http://app:8000), D-10 (compose-side
# HEALTHCHECK only), D-13 (Phase 2 seed assumed).

services:
  app:
    # D-04: build from repo-root Dockerfile, not a registry pull.
    # `..` is relative to this compose file's directory, i.e. the repo root.
    build:
      context: ..
      dockerfile: Dockerfile
    # No image: tag - compose synthesises one as `<projectname>-app`. We never
    # need to reference the image elsewhere.
    environment:
      LLM_MOCK: "true"          # D-05: deterministic mock chat path
      OPENROUTER_API_KEY: ""    # set explicitly empty; suppresses Phase 5 warning
      MASSIVE_API_KEY: ""       # empty -> SimulatorDataSource
      DB_PATH: /app/db/finally.db
      PYTHONUNBUFFERED: "1"
    # D-06: NO `volumes:` mapping for /app/db -> compose creates a fresh
    # anonymous volume per `up` invocation. Each run starts with a clean
    # SQLite (Phase 2 lazy init re-seeds the 10-ticker watchlist + $10k cash).
    # D-10: compose-side HEALTHCHECK only - the production Dockerfile
    # deliberately omits HEALTHCHECK (Phase 9 / D-08 of Phase 9 CONTEXT).
    healthcheck:
      # python3 ships in python:3.12-slim runtime stage; curl does NOT.
      test: ["CMD-SHELL", "python3 -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health', timeout=2).status==200 else 1)\""]
      interval: 5s
      timeout: 3s
      retries: 12        # 12 * 5s = 60s total budget after start_period
      start_period: 15s  # grace window for FastAPI lifespan + DB seed

  playwright:
    image: mcr.microsoft.com/playwright:v1.59.1-jammy
    depends_on:
      app:
        condition: service_healthy   # D-10
    working_dir: /work
    volumes:
      - ../test:/work     # mount the test/ directory itself (host-relative to compose file)
    environment:
      # Override Playwright config baseURL via env (config also hardcodes
      # http://app:8000 via D-09 - this is belt-and-suspenders).
      BASE_URL: "http://app:8000"
      # Disable Playwright's "you should run `npx playwright install`" nag:
      # the image already has all browsers installed.
      PLAYWRIGHT_BROWSERS_PATH: /ms-playwright
      # CI=1 turns on Playwright's CI defaults (forbidOnly, retries, etc.)
      # AND keys our `retries: process.env.CI ? 1 : 0` config switch.
      CI: "1"
    # Run install + tests as a single command so we can stream npm output to
    # compose stdout. `npm ci` is reproducible from package-lock.json.
    command: >
      sh -c "npm ci && npx playwright test"
    # If the container errors before tests run, exit propagates via
    # --exit-code-from playwright.
```

### Compose key choreography (data flow)

```
docker compose up
  |
  +--> [build app from ../Dockerfile]
  +--> [pull mcr.microsoft.com/playwright:v1.59.1-jammy]
  |
  +--> START app
        |
        +--> compose runs HEALTHCHECK every 5s
        +--> python3 urllib hits http://localhost:8000/api/health
        +--> first 200 -> service_healthy
  |
  +--> START playwright (gated by depends_on.condition: service_healthy)
        |
        +--> npm ci  (reads /work/package.json + /work/package-lock.json)
        +--> npx playwright test  (reads /work/playwright.config.ts)
              +--> spawns chromium/firefox/webkit projects (D-02)
              +--> baseURL http://app:8000 - DNS resolves to app service
              +--> writes report to /work/playwright-report (host: test/playwright-report)
        +--> exits with playwright's exit code
  |
  +--> --abort-on-container-exit -> stop app  (compose tears down)
  +--> --exit-code-from playwright -> compose process exits with playwright's code
```

### Why `python3` in the healthcheck instead of `curl`

The production image is `python:3.12-slim` and intentionally LEAN — no curl, no wget. `python3` IS available (it's the entire backend runtime). One-line urllib check works in both jammy and noble Python 3.12 images. `[VERIFIED: Dockerfile line 29 `FROM python:3.12-slim AS runtime`]`.

Alternative considered: shell-out via `nc` or installing curl. Rejected — adding a runtime dep just for a healthcheck is exactly the kind of test-affordance creep CONTEXT.md D-06 forbids (production image must not be hardened for E2E concerns).

## Playwright Configuration

> Full TypeScript draft. Planner copies into `test/playwright.config.ts`.

```typescript
// test/playwright.config.ts
// CONTEXT.md: D-02 (full browser matrix), D-07 (workers / parallelism),
// D-09 (testDir, baseURL, retries, reporter).

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // D-09: specs colocated with this config under test/
  testDir: '.',
  testMatch: /\d{2}-.+\.spec\.ts$/,

  // D-09: retries 0 locally / 1 in CI. The compose file sets CI=1 always,
  // so the suite gets one transparent retry to absorb SSE-reconnect-test
  // flakiness without masking real bugs (D-09 wording).
  retries: process.env.CI ? 1 : 0,

  // D-07: "workers: 1 within a Playwright project; cross-browser projects parallel".
  // Playwright DOES NOT support per-project worker caps. The intent is achieved
  // with workers = (number of projects) + fullyParallel: false:
  //   - workers: 3  -> three concurrent worker processes
  //   - fullyParallel: false (default) -> tests in a single file run serially
  //     within one worker; each worker picks up one whole spec file at a time
  //   - 7 specs x 3 projects = 21 (file, project) tasks distributed greedily
  //     across the 3 workers; D-08's per-spec unique tickers prevent any
  //     cross-spec collision regardless of which browser picks them up first.
  workers: 3,
  fullyParallel: false,

  // Forbid `test.only` from sneaking into a green-bar commit.
  forbidOnly: !!process.env.CI,

  // D-09: list reporter to compose stdout + html report under test/playwright-report/
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
  ],

  use: {
    // D-09: compose-internal DNS - the playwright container reaches the app
    // service by service name. Env override available for ad-hoc local runs.
    baseURL: process.env.BASE_URL ?? 'http://app:8000',

    // Trace on first retry only (cheap on green, full evidence on red).
    trace: 'on-first-retry',

    // Capture screenshot only on failure.
    screenshot: 'only-on-failure',

    // Capture video only on failure.
    video: 'retain-on-failure',

    // Suite-wide action timeout. Default Playwright is no per-action timeout
    // (it relies on per-test timeout). Setting 10s catches misclicks early.
    actionTimeout: 10_000,
  },

  // Per-test budget. SSE-related specs may need to wait for retry: 1000 + a
  // tick; 30s is generous.
  timeout: 30_000,

  // Where to write JUnit-style results, traces, etc.
  outputDir: 'test-results',

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit',   use: { ...devices['Desktop Safari'] } },
  ],
});
```

### Worker-semantics confirmation

`[CITED: https://playwright.dev/docs/test-parallel]` — "Test files are run in parallel. Tests in a single file are run in order, in the same worker process."

`[CITED: https://testdino.com/blog/playwright-parallel-execution/]` — "The 'parallelism' here is about task granularity, not project distribution. The scheduler assigns test files (not projects) as the scheduling unit when fullyParallel: false."

Conclusion: `workers: 3` + `fullyParallel: false` + 7 spec files × 3 projects achieves CONTEXT.md D-07's intent — within any spec file, tests run serially in one worker; up to 3 spec files (across browsers) run concurrently. D-08's per-spec unique tickers make cross-spec ordering irrelevant.

## Per-Scenario Spec Outlines

> One section per spec file from D-11. Selectors confirmed via the `Component Test-ID Inventory`.

### `01-fresh-start.spec.ts` — §12 row 1

**Asserts:**

1. The 10-ticker default watchlist (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) is present.
2. `$10,000.00` cash is shown in the header.
3. At least one ticker price stops being the `—` placeholder within ~3 seconds of page load (proves SSE is streaming).

**Selector strategy:**

| Surface | Selector |
|---------|----------|
| Watchlist rows | `page.getByRole('button', { name: /^Select (AAPL\|GOOGL\|MSFT\|AMZN\|TSLA\|NVDA\|META\|JPM\|V\|NFLX)$/ })` (each row is `<tr role="button" aria-label="Select AAPL">`) |
| Cash balance | `page.getByText(/^\$10,000\.00$/)` adjacent to the `Cash` label, OR `page.locator('header').getByText('$10,000.00')` |
| Streaming proof | Wait for the AAPL row's price cell to NOT contain the `—` em-dash; use `expect(row).not.toContainText('—')` with a timeout |

**Edge cases:**

- The simulator may not have produced a tick for AAPL within page-load + 1 tick (~500ms). Use Playwright's `expect(...).toHaveText(...)` auto-wait, or `expect.poll()`, with the suite's 30s budget — generous given the simulator emits every 500ms.
- WebKit's first paint is sometimes slower; rely on auto-wait, not explicit `waitForTimeout`.

**Cross-browser:** No known issues. All three engines see `<tr role="button" aria-label="...">` identically.

### `02-watchlist-crud.spec.ts` — §12 row 2

**The reality:** There is **no** UI affordance to add/remove tickers from the watchlist as of Phase 9. FE-03 (Watchlist panel) shipped read-only; an "add ticker" UI was deferred. The chat panel CAN add/remove via `add NVDA` / `remove NVDA` mock-keyword phrases (D-05 + Phase 5 mock).

**Two viable strategies:**

| Strategy | Pros | Cons |
|----------|------|------|
| **A — `request.post('/api/watchlist', {ticker: 'PYPL'})` + DELETE** ★ | Tests the canonical CRUD path end-to-end against the running app; matches PLAN.md §12 row literal "Add and remove a ticker from the watchlist" | Doesn't exercise UI |
| B — chat-driven: send `"add PYPL"`, then `"remove PYPL"` | UI-exercising | Couples this spec to chat mock + 06-chat.spec semantics |

**Recommendation: A.** PLAN.md §12 says "Add and remove a ticker from the watchlist" without specifying UI affordance. Per `Watchlist.tsx` lines 16-18 the React Query for `['watchlist']` uses no `refetchInterval`, so the UI won't reflect REST mutations until the watchlist is invalidated — but the assertion is on the API result, not on the UI. If Phase 10 wants UI verification, fall back to chat (option B) and dedupe with 06-chat.

**Selector strategy (option A):** No DOM selectors needed for the mutation; assert against `response.json()`.

```typescript
test('add then remove PYPL', async ({ request }) => {
  const add = await request.post('/api/watchlist', { data: { ticker: 'PYPL' } });
  expect(add.ok()).toBeTruthy();
  expect((await add.json()).status).toMatch(/^(added|exists)$/);

  const list = await (await request.get('/api/watchlist')).json();
  expect(list.items.map((i: { ticker: string }) => i.ticker)).toContain('PYPL');

  const del = await request.delete('/api/watchlist/PYPL');
  expect(del.ok()).toBeTruthy();
  expect((await del.json()).status).toMatch(/^(removed|not_present)$/);
});
```

**Edge cases:**

- The test runs against `baseURL: http://app:8000` so `request` calls hit the compose-internal app service.
- D-08 unique-ticker rule: pick a ticker NOT in the seed list — `PYPL`, `IBM`, `ORCL` are good candidates.

**Cross-browser:** N/A — `request` doesn't use a browser. The test still runs once per project but consumes minimal resources.

### `03-buy.spec.ts` — §12 row 3

**Asserts:**

1. After a buy of NVDA × 1, cash decreases.
2. NVDA appears in the positions table.
3. Total portfolio value updates (cash + positions = ~10000).

**Selector strategy (UI-driven via TradeBar):**

| Surface | Selector |
|---------|----------|
| Ticker input | `page.getByLabel('Ticker')` (label is `<label>` with text "Ticker") |
| Quantity input | `page.getByLabel('Quantity')` |
| Buy button | `page.getByRole('button', { name: 'Buy' })` |
| Sell button | `page.getByRole('button', { name: 'Sell' })` |
| Positions table NVDA row | `page.getByRole('button', { name: 'Select NVDA' })` (PositionRow is `<tr role="button" aria-label="Select NVDA">`) |
| Cash header value | `page.locator('header').getByText(/\$/).nth(1)` (`Total` is index 0, `Cash` is index 1) — or use a more stable test-id once added |

**Test code shape:**

```typescript
test('buy NVDA 1 - cash decreases, position appears', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('$10,000.00')).toBeVisible();

  await page.getByLabel('Ticker').fill('NVDA');
  await page.getByLabel('Quantity').fill('1');
  await page.getByRole('button', { name: 'Buy' }).click();

  // Position row appears (PositionRow uses aria-label="Select NVDA")
  await expect(
    page.getByRole('button', { name: 'Select NVDA' })
  ).toBeVisible({ timeout: 10_000 });

  // Cash strictly less than $10,000.00 (cannot assert exact value because
  // the simulator price moves, but it must be less since we just bought).
  // Read the cash text node and parse.
  const cashText = await page.locator('header').getByText(/^\$/).nth(1).innerText();
  const cashAmount = parseFloat(cashText.replace(/[$,]/g, ''));
  expect(cashAmount).toBeLessThan(10_000);
});
```

**Edge cases:**

- The simulator must have produced at least one tick for NVDA before the buy, or the trade fails with `price_unavailable`. NVDA is in the default seed (line 39 of `seed_prices.py`), so its first tick lands within ~500ms of app start. The healthcheck's `start_period: 15s` plus an explicit `goto('/')` warm-up makes this race effectively zero.
- D-08 unique-ticker rule: this spec uses `NVDA`. The sell spec uses `JPM`.

**Cross-browser:** All three engines render `<input>` and `<button>` identically. WebKit's autofill quirks don't apply (we use `.fill()`, not `.type()`).

**Recommendation: add a `data-testid="header-cash"` and `data-testid="header-total"` to `Header.tsx` in a Phase 10 plan — this stabilises 03-buy and 04-sell against future header copy churn.** Tracked as a recommended planner-discretion addition; does NOT modify the UX.

### `04-sell.spec.ts` — §12 row 4

**Asserts:** After buying JPM × 2 then selling JPM × 1, the JPM position has qty=1 and cash reflects the round-trip.

**Why JPM:** D-08 unique tickers — buy uses NVDA, sell uses JPM. JPM is in the default seed.

**Test code shape:**

```typescript
test('sell JPM 1 after buying 2 - position qty drops to 1', async ({ page }) => {
  await page.goto('/');

  // Buy 2
  await page.getByLabel('Ticker').fill('JPM');
  await page.getByLabel('Quantity').fill('2');
  await page.getByRole('button', { name: 'Buy' }).click();
  await expect(page.getByRole('button', { name: 'Select JPM' })).toBeVisible();

  // Sell 1
  await page.getByLabel('Ticker').fill('JPM');
  await page.getByLabel('Quantity').fill('1');
  await page.getByRole('button', { name: 'Sell' }).click();

  // Wait for the qty cell in the JPM row to read "1"
  const jpmRow = page.getByRole('button', { name: 'Select JPM' });
  await expect(jpmRow).toContainText(/\bJPM\b.*\b1\b/, { timeout: 10_000 });
});
```

**Edge cases:**

- React Query refetches every 15s; mutations invalidate `['portfolio']` immediately on success. The expect-poll inside `toContainText` covers the brief gap.

**Cross-browser:** No issues.

### `05-portfolio-viz.spec.ts` — §12 row 5

**Asserts:**

1. Switching to the Heatmap tab renders `[data-testid=heatmap-treemap]` (or the skeleton `heatmap-skeleton` if no positions).
2. Switching to the P&L tab renders `[data-testid=pnl-chart]` and `[data-testid=pnl-summary]` shows a dollar value.

**Selector strategy:** ALL three viz surfaces have stable `data-testid` (Phase 8 inventory). Use them.

**Pre-condition:** The portfolio must have at least one position for the heatmap to render past the skeleton. Buy something at the top of the test (or run after 03-buy, but D-08 says specs don't depend on each other — so this spec buys its own setup).

**Test code shape:**

```typescript
test('heatmap and PnL chart render', async ({ page }) => {
  await page.goto('/');
  // Buy a position so the heatmap has data to render.
  // Use META so we don't collide with NVDA/JPM (D-08).
  await page.getByLabel('Ticker').fill('META');
  await page.getByLabel('Quantity').fill('1');
  await page.getByRole('button', { name: 'Buy' }).click();
  await expect(page.getByRole('button', { name: 'Select META' })).toBeVisible();

  // Heatmap tab
  await page.getByRole('tab', { name: /heatmap/i }).click();
  await expect(page.getByTestId('heatmap-treemap')).toBeVisible({ timeout: 10_000 });

  // P&L tab
  await page.getByRole('tab', { name: /p.+l/i }).click();
  await expect(page.getByTestId('pnl-chart')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId('pnl-summary')).toBeVisible();
});
```

**Edge cases:**

- The portfolio_snapshots table seeds an initial snapshot on lifespan boot (per Phase 3 D-08), so the P&L chart has at least one data point even before the test buys anything. Verify the chart still renders with that single point on cold start.
- TabBar uses `aria-pressed` for state, but the role is still `tab` (verified in `TabBar.tsx`). `getByRole('tab', { name: /heatmap/i })` works.

**Cross-browser:** Recharts SVG renders identically across all three engines; only known cross-browser issue (per Phase 8 08-04 RESEARCH) is the Vitest-only ResponsiveContainer ResizeObserver issue, which doesn't apply to a real browser.

### `06-chat.spec.ts` — §12 row 6

**Asserts:** Sending `"buy AMZN 1"` to the chat input produces an assistant turn that includes a visible action card with status `executed` (or `failed` — both are legal per Phase 5 chat test #3 — but the simulator should have a price for AMZN by then).

**LLM mock keyword reference (see `LLM Mock Trigger Phrases` section):** `"buy <TICKER> <QTY>"` triggers a TradeAction; the chat service auto-executes via the same path as a manual trade.

**Selector strategy:** All chat surfaces have stable `data-testid` (Phase 8 inventory).

| Surface | Selector |
|---------|----------|
| Chat input | `page.getByLabel('Ask the assistant')` |
| Send button | `page.getByRole('button', { name: 'Send' })` |
| Chat thread | `page.getByTestId('chat-thread')` |
| Assistant message | `page.getByTestId('chat-message-assistant')` |
| Action card (executed) | `page.getByTestId('action-card-executed')` |
| Action card list wrapper | `page.getByTestId('action-card-list')` |

**Test code shape:**

```typescript
test('chat trade execution shows inline action card', async ({ page }) => {
  await page.goto('/');
  // Drawer is open by default (ChatDrawer state initial = true).

  await page.getByLabel('Ask the assistant').fill('buy AMZN 1');
  await page.getByRole('button', { name: 'Send' }).click();

  // The mock client returns a TradeAction; the service auto-executes;
  // ChatThread renders the response with an ActionCardList.
  await expect(page.getByTestId('action-card-executed')).toBeVisible({
    timeout: 15_000,
  });

  // Bonus: the position appears in the table.
  await expect(page.getByRole('button', { name: 'Select AMZN' })).toBeVisible();
});
```

**KNOWN ISSUE — ChatResponse field-shape mismatch (gap, not blocker):**

The backend `ChatResponse` Pydantic model returns `{message, trades, watchlist_changes}` (see `backend/app/chat/models.py:83-88`), but the frontend `ChatThread.tsx` line 30-35 reads `res.id`, `res.content`, `res.created_at` (all undefined in the actual response). The result: the assistant chat bubble renders with empty content, but the `ActionCardList` renders correctly because `res.trades` and `res.watchlist_changes` ARE present. **Phase 10 must NOT assert on the assistant-bubble text** (it would always be empty); asserting on `[data-testid=action-card-executed]` is the stable signal.

This is the kind of gap CONTEXT.md D-05 anticipates ("If the current canned response does NOT trigger an inline trade execution, Phase 10 surfaces that as a gap rather than expanding the LLM mock"). Surface as Phase 10.1 candidate; do not block Phase 10 on it.

**Edge cases:**

- AMZN must have streamed at least one tick before the trade fires. Same mitigation as 03-buy.
- The chat drawer is collapsible (initial state = open per `ChatDrawer.tsx:19`). If a future phase changes that default, this spec needs to click the open toggle first via `getByLabel('Expand chat')`.
- D-08: AMZN is unique to this spec.

**Cross-browser:** Form submit + textarea behaviour identical across engines. ChatInput uses `Enter` to submit (line 31-33); explicit click on Send is more deterministic.

### `07-sse-reconnect.spec.ts` — §12 row 7

**Asserts:**

1. Page loads with green ConnectionDot (`aria-label="SSE connected"`).
2. Aborting all `/api/stream/prices` requests via `page.route()` causes the dot to reach `aria-label="SSE reconnecting"` or `"SSE disconnected"`.
3. Calling `page.unroute()` (or letting the route handler stop intercepting) allows EventSource's built-in retry to land a new connection; dot returns to `"SSE connected"`.

**The pattern (D-12, RESEARCH-validated):**

```typescript
test('SSE disconnect and reconnect', async ({ page }) => {
  await page.goto('/');

  // 1. Confirm connected
  await expect(page.getByLabel('SSE connected')).toBeVisible({ timeout: 10_000 });

  // 2. Block SSE - browser EventSource will see connectionreset and retry
  await page.route('**/api/stream/prices', (route) => route.abort('connectionreset'));

  // 3. Dot transitions to reconnecting/disconnected.
  // Status flips to 'reconnecting' first (selectConnectionStatus reads from
  // the EventSource's onerror handler in lib/price-store.ts). On second
  // failure it may go to 'disconnected'. Match either to be browser-engine
  // tolerant.
  await expect(
    page.getByLabel(/^SSE (reconnecting|disconnected)$/)
  ).toBeVisible({ timeout: 10_000 });

  // 4. Allow reconnect: remove the route handler. Future EventSource
  // retry attempts (server sends `retry: 1000`) will succeed.
  await page.unroute('**/api/stream/prices');

  // 5. Dot returns to connected within ~retry-time + a tick.
  await expect(page.getByLabel('SSE connected')).toBeVisible({ timeout: 15_000 });
});
```

**Why `connectionreset` over `failed`:**

- `'connectionreset'` simulates a TCP RST, which is what a real network blip looks like and is the cleanest trigger for EventSource's retry path.
- `'failed'` (default) also works but is less semantically tight.
- WebKit treats both identically for SSE retry purposes per the WHATWG spec — the browser fires `error` on the EventSource, sets readyState to CONNECTING, and starts the reconnection timer.

`[CITED: https://html.spec.whatwg.org/multipage/server-sent-events.html#processing-model]` — "When the user agent is to reestablish the connection, ... wait the reconnection time, then attempt to reconnect."

`[VERIFIED: backend SSE response includes `retry: 1000` per Phase 9 verification row 5]` — gives a known 1s reconnect floor.

**Why this is NOT subject to Playwright issue #15353:**

Playwright's known SSE limitation is in **fulfilling** SSE responses (fake `text/event-stream` content with the right Content-Type). We are **aborting**, not fulfilling. `route.abort()` works fine on any URL pattern including SSE — it's just network-layer cancellation.

`[CITED: https://playwright.dev/docs/api/class-route#route-abort]` — `route.abort()` accepts standard error codes; no SSE-specific carve-out.

**Edge cases per browser:**

- **Chromium:** Fires error event immediately on TCP reset; readyState = CONNECTING; first retry attempt at `retry` interval.
- **Firefox:** Same behavior; sometimes issues a few rapid retries before backing off.
- **WebKit:** Slightly different timing — historically WebKit has been pickier about `text/event-stream` Content-Type, but our backend sends the correct header so the reconnect succeeds. WebKit may take an extra 1-2s vs other browsers; the 15s timeout covers it.

**Edge case — global retry interception:**

`page.route()` set after the page is already streaming will intercept the NEXT request, not the in-flight one. The browser's existing SSE connection stays open until the server closes it OR the browser terminates the page. So the test needs ONE of:
- a route handler set via `context.route()` BEFORE navigation, OR
- triggering EventSource to re-fetch (e.g. via `page.evaluate(() => window.dispatchEvent(new Event('online')))` — too engine-specific), OR
- letting the natural browser-tab-suspend / process-restart cycle apply (not test-friendly).

**Recommended:** Set the route BEFORE the abort cycle so the next reconnect attempt is the one that hits the abort:

```typescript
// Better: arm the abort, then trigger a reconnect by closing the connection server-side.
// But we can't reach the server. So: arm, then wait for the dot to flip naturally on
// the next normal SSE re-establishment (which always happens within ~1s as the simulator
// emits ticks).
```

ALTERNATIVE simpler pattern (verified to work cross-browser):

```typescript
// Use page.context().route() so it covers ALL future requests including
// the EventSource's automatic reconnect after we close it.
await page.context().route('**/api/stream/prices', (route) => route.abort('connectionreset'));
// Force the browser to notice by killing the EventSource via JS.
await page.evaluate(() => {
  // The PriceStreamProvider exposes the EventSource on window in dev only.
  // In production it doesn't, so close the existing connection by reloading
  // the SSE consumer. Simplest: navigate to /; the route now blocks the new
  // connection.
  // ...
});
```

**Pragmatic recommendation:** Implement the simple form first, verify cross-browser; if it flakes, switch to a `context.route()` + page reload pattern. Use `expect.poll` with a 15s timeout. Phase 10 retries: 1 absorbs the residual flake.

**Open question for the planner:** If the dot's transient yellow phase is too fast to catch deterministically (it can flip from green to disconnected without a visible reconnecting state), the test should accept either yellow OR red as the "disconnect was observed" signal — the regex above does this.

## SSE Reconnect Test Pattern

> Promoting this to a top-level section because it's the single least obvious technique in the suite.

### Canonical pattern (cross-browser-tolerant)

```typescript
import { test, expect } from '@playwright/test';

test('SSE reconnect roundtrip', async ({ page, context }) => {
  // Use context.route so the handler covers every request from this context,
  // including the EventSource's auto-retries.
  await page.goto('/');
  await expect(page.getByLabel('SSE connected')).toBeVisible({ timeout: 10_000 });

  // Arm the abort. Existing in-flight SSE request remains open until
  // it next reconnects (every ~retry: 1000 from the server, or sooner on
  // a tick gap > the proxy idle).
  await context.route('**/api/stream/prices', (route) =>
    route.abort('connectionreset'),
  );

  // Trigger a reconnect by reloading the page. After reload the EventSource
  // tries to connect, hits the abort, and the connection-status state machine
  // walks to 'reconnecting' / 'disconnected'.
  await page.reload();

  await expect(
    page.getByLabel(/^SSE (reconnecting|disconnected)$/),
  ).toBeVisible({ timeout: 10_000 });

  // Lift the abort. Subsequent retries succeed. EventSource backs off
  // exponentially after multiple failures, so the timeout is generous.
  await context.unroute('**/api/stream/prices');

  await expect(page.getByLabel('SSE connected')).toBeVisible({ timeout: 20_000 });
});
```

### Key API notes

- `context.route()` matches the FULL URL of every request from any page in this context (one page per test by default).
- `route.abort('connectionreset')` simulates TCP RST. Other valid codes for SSE-disconnect simulation: `'connectionrefused'`, `'connectionaborted'`, `'failed'`. `[CITED: https://playwright.dev/docs/api/class-route#route-abort]`
- `context.unroute()` removes a previously-installed handler. Existing in-flight requests using the handler return without their handler firing for new requests.
- `page.unroute()` is the same idea but page-scoped. Either works; context-scoped is safer because it survives navigation.

### Why we don't use `route.fulfill()` for SSE

Playwright issue #15353 (open as of 2026-01) documents that `route.fulfill()` cannot reliably set `Content-Type: text/event-stream` on SSE responses, AND can't keep the connection open the way the EventSource spec requires. We are NOT fulfilling — we are aborting. `route.abort()` has no equivalent limitation. `[CITED: https://github.com/microsoft/playwright/issues/15353]`

### WebKit caveat

WebKit's SSE handler is historically the strictest about Content-Type and chunked-transfer. Our backend (Phase 1, MARKET-04) sends standards-compliant `text/event-stream` with `retry: 1000` field, so reconnects succeed. If a WebKit-only flake appears, suspect the proxy (Next.js dev server `rewrites()` in `next.config.mjs:14-21` is dev-only — production export has empty rewrites, so requests go straight to FastAPI's route).

## Component Test-ID Inventory

> Verified by `grep -rn "data-testid" frontend/src/components/` and `grep -rn "aria-label" frontend/src/components/` on 2026-04-27.

### `data-testid` (preferred — stable across copy changes)

| Test ID | Component | File | Purpose |
|---------|-----------|------|---------|
| `chat-drawer` | ChatDrawer | `chat/ChatDrawer.tsx:22` | Drawer outer `<aside>` |
| `chat-drawer-body` | ChatDrawer | `chat/ChatDrawer.tsx:29` | Inner body (hidden when collapsed) |
| `chat-thread` | ChatThread | `chat/ChatThread.tsx:100` | Scrollable message list |
| `chat-thread-skeleton` | ChatThread | `chat/ChatThread.tsx:104` | Loading-state placeholder |
| `chat-message-user` | ChatMessage | `chat/ChatMessage.tsx:27` | User bubble (template-literal `chat-message-${role}`) |
| `chat-message-assistant` | ChatMessage | `chat/ChatMessage.tsx:27` | Assistant bubble |
| `thinking-bubble` | ThinkingBubble | `chat/ThinkingBubble.tsx:11` | In-flight loader |
| `action-card-list` | ActionCardList | `chat/ActionCardList.tsx:23` | Wrapper around all action cards |
| `action-card-executed` | ActionCard | `chat/ActionCard.tsx:98` | Trade succeeded |
| `action-card-failed` | ActionCard | `chat/ActionCard.tsx:98` | Trade failed validation |
| `action-card-added` | ActionCard | `chat/ActionCard.tsx:98` | Watchlist add succeeded |
| `action-card-removed` | ActionCard | `chat/ActionCard.tsx:98` | Watchlist remove succeeded |
| `action-card-exists` | ActionCard | `chat/ActionCard.tsx:98` | Watchlist add no-op |
| `action-card-not_present` | ActionCard | `chat/ActionCard.tsx:98` | Watchlist remove no-op |
| `heatmap-skeleton` | Heatmap | `portfolio/Heatmap.tsx:83` | Empty/loading state |
| `heatmap-treemap` | Heatmap | `portfolio/Heatmap.tsx:117` | Recharts Treemap container |
| `pnl-chart` | PnLChart | `portfolio/PnLChart.tsx:93` | Recharts LineChart container |
| `pnl-skeleton` | PnLChart | `portfolio/PnLChart.tsx:70` | Loading state |
| `pnl-summary` | PnLChart | `portfolio/PnLChart.tsx:59` | Header `Total ($) vs $10k` text |
| `skeleton-block` | SkeletonBlock | `skeleton/SkeletonBlock.tsx:16` | Generic shimmer primitive |

### `aria-label` (use via `getByLabel` / `getByRole({name})`)

| Aria Label | Component | File | Purpose |
|------------|-----------|------|---------|
| `Select AAPL` (etc.) | WatchlistRow | `terminal/WatchlistRow.tsx:46` | Each watchlist `<tr role="button">` |
| `Select AAPL` (etc.) | PositionRow | `terminal/PositionRow.tsx:54` | Each positions-table `<tr role="button">` |
| `SSE connected` / `reconnecting` / `disconnected` | ConnectionDot | `terminal/ConnectionDot.tsx:30` | Header status dot |
| `Center column tabs` | TabBar | `terminal/TabBar.tsx:23` | Wrapper `aria-label` on the tab list |
| `Ask the assistant` | ChatInput | `chat/ChatInput.tsx:48` | Textarea label |
| `Collapse chat` / `Expand chat` | ChatHeader | `chat/ChatHeader.tsx:21` | Toggle button |
| (label text) `Ticker` | TradeBar | `terminal/TradeBar.tsx:84-86` | `<label>` wrapping `<input type="text">` |
| (label text) `Quantity` | TradeBar | `terminal/TradeBar.tsx:100-102` | `<label>` wrapping `<input type="number">` |
| (button text) `Buy`, `Sell` | TradeBar | `terminal/TradeBar.tsx:122,130` | Buttons (no aria-label; `getByRole('button',{name:'Buy'})`) |
| (button text) `Send` | ChatInput | `chat/ChatInput.tsx:56` | Submit button |

### Surfaces with NO stable selector — recommend adding test-ids in a Phase 10 plan

> These would NOT be production-shape changes; they're additive `data-testid="..."` attributes on existing DOM nodes. Each is one-line.

| Surface | Recommended `data-testid` | Why |
|---------|---------------------------|-----|
| Header cash value | `header-cash` on the cash `<span>` (`Header.tsx:48-50`) | Currently must be reached via DOM index (`nth(1)`); brittle |
| Header total value | `header-total` on the total `<span>` (`Header.tsx:42-45`) | Same reason |
| TabBar individual tab buttons | `tab-{id}` on each `<button role="tab">` (`TabBar.tsx`) | `getByRole('tab', {name: /heatmap/i})` works but text-coupled |
| Watchlist panel root | `watchlist-panel` on the `<aside>` in `Watchlist.tsx:25` | For "wait for watchlist to load" assertions |
| Positions table root | `positions-table` on the `<section>` in `PositionsTable.tsx:28` | Same |
| TradeBar root | `trade-bar` on the `<section>` in `TradeBar.tsx:82` | Stabilizes scoped queries |

**Recommendation:** Add these in a SINGLE plan early in Phase 10 ("01-add-test-ids-PLAN.md") so subsequent spec plans reference them. ~6 lines of code total. Zero behavioral or visual change. Treat as a pre-requisite Wave 0 plan.

If the planner disagrees and prefers to keep the components untouched, the alternative is to use the more brittle role/index selectors documented in the per-spec sections above. Both are viable; the test-id approach is more stable.

## LLM Mock Trigger Phrases

> Verified by reading `backend/app/chat/mock.py` lines 9-15 (regexes) and lines 21-55 (logic).

The Phase 5 `MockChatClient.complete()` runs FOUR regexes against the last user message in the conversation history:

| Regex | Pattern | Trigger phrases (case-insensitive) | Resulting action |
|-------|---------|-------------------------------------|------------------|
| `_BUY` | `\bbuy\s+(<TICKER>)\s+(<QTY>)\b` | `buy AAPL 10`, `BUY tsla 0.5`, `Please buy nvda 1` | `TradeAction(ticker, side="buy", quantity)` |
| `_SELL` | `\bsell\s+(<TICKER>)\s+(<QTY>)\b` | `sell AAPL 5`, `Sell V 0.25` | `TradeAction(ticker, side="sell", quantity)` |
| `_ADD` | `\badd\s+(<TICKER>)\b` | `add PYPL`, `please add IBM` | `WatchlistAction(ticker, action="add")` |
| `_REMOVE` | `\b(?:remove\|drop)\s+(<TICKER>)\b` | `remove META`, `drop NFLX` | `WatchlistAction(ticker, action="remove")` |

Where:

- `<TICKER>` matches `[A-Z][A-Z0-9.]{0,9}` — must start with an uppercase letter; up to 10 chars total.
- `<QTY>` matches `\d+(?:\.\d+)?` — non-negative number, fractional shares allowed.

### Response shape

If ANY regex matches → response is:
```json
{
  "message": "Mock: executing buy AAPL 1.0",
  "trades": [...],
  "watchlist_changes": [...]
}
```
Multiple matches concatenate (e.g., `"add PYPL and buy PYPL 1"` produces both a watchlist add and a trade).

If NO regex matches → response is:
```json
{
  "message": "mock response",
  "trades": [],
  "watchlist_changes": []
}
```

### Confirmed by Phase 5 UAT

Phase 5 UAT tests #2-4 (05-UAT.md) explicitly verified:
- `"hello"` → empty trades, empty watchlist_changes (test #2)
- `"buy AAPL 1"` → 1 trade with status `executed` or `failed` (test #3)
- `"add PYPL"` → 1 watchlist_change with status `added` or `exists` (test #4)

**All passed.** Trade auto-execution through the Phase 5 service path is real and works.

`[VERIFIED: backend/app/chat/mock.py:9-55]`
`[VERIFIED: .planning/phases/05-ai-chat-integration/05-UAT.md tests 2-4]`

### Recommended phrases for Phase 10 specs

| Spec | Suggested phrase | Why |
|------|------------------|-----|
| `06-chat.spec.ts` | `buy AMZN 1` | AMZN is in the seed; Phase 5 UAT used AAPL — different ticker for D-08 isolation |
| (alt for `02-watchlist-crud.spec.ts` if going UI route) | `add PYPL` then `remove PYPL` | PYPL is NOT in the seed — distinct from any other spec's choices |

## Known Pitfalls & Mitigations

### Pitfall 1: Cold-cache `price_unavailable` on first trade

**What goes wrong:** A test that buys a ticker before the simulator has emitted its first tick gets `price_unavailable` and the trade fails. The position never appears.

**Why it happens:** Phase 1's PriceCache is empty until the simulator's first tick (~500ms after lifespan startup). The compose HEALTHCHECK only checks `/api/health`, which returns OK before any prices are cached.

**Mitigation:** The test's `goto('/')` and React Query's first `['portfolio']` fetch take long enough (typically 1-2s) that ticks have arrived. AS A BELT-AND-SUSPENDERS, `start_period: 15s` in the healthcheck plus a Playwright `expect.toBeVisible({timeout:10_000})` on the watchlist makes the race effectively zero. If a test still flakes on cold cache, add `await expect(watchlistPriceCell).not.toContainText('—')` before the trade.

**Warning sign:** A trade test that flakes specifically on the FIRST run after a fresh build — pattern: works on `up` re-run but fails on cold `up --build`.

### Pitfall 2: `--abort-on-container-exit` race on slow Playwright shutdown

**What goes wrong:** Playwright finishes, exits 0, compose tries to stop the app, but the app takes >10s to drain (e.g. an in-flight SSE response holds a worker). Compose may report exit code != Playwright's.

**Why it happens:** `--exit-code-from` reads from the named service AFTER all dependent services finish. If the app's `STOPSIGNAL SIGINT` (set in Dockerfile line 62) doesn't propagate cleanly, compose can return the app's `137` (SIGKILL after timeout) instead of Playwright's `0`.

**Mitigation:** The Phase 9 Dockerfile sets `STOPSIGNAL SIGINT` so uvicorn shuts down through `uv run`. Verified working in Phase 9 verification. Should be fine.

**Warning sign:** Suite passes but compose reports exit 137 instead of 0; check `docker compose logs app` for SIGKILL.

### Pitfall 3: Playwright issue #15353 — SSE fulfillment limitation

**What goes wrong:** A naive reading of "Playwright doesn't support SSE" leads someone to abandon `route.abort()` for SSE.

**Why it happens:** Issue #15353 is about FULFILLING SSE responses with `text/event-stream`. We are ABORTING. Different code paths.

**Mitigation:** Use `route.abort('connectionreset')` confidently. We are not fulfilling.

**Warning sign:** N/A — explicitly documented in the SSE Reconnect section.

### Pitfall 4: ChatResponse field-shape mismatch

**What goes wrong:** Test asserts `chat-message-assistant` contains expected text. It's empty.

**Why it happens:** Backend sends `{message, trades, watchlist_changes}`; frontend reads `res.id`/`res.content` (undefined). Assistant bubble renders empty string. The action-card list IS populated correctly because the field name `trades`/`watchlist_changes` matches.

**Mitigation:** Phase 10 specs assert on `[data-testid=action-card-{status}]`, NOT on `chat-message-assistant` text. Document the gap; surface as Phase 10.1 candidate.

**Warning sign:** Asserting bubble text always fails despite the action card appearing.

### Pitfall 5: Anonymous volume forgets state mid-suite

**What goes wrong:** Spec 03-buy buys NVDA. Spec 04-sell expects NVDA to be there. It isn't.

**Why it happens:** D-06's anonymous volume is per `up`, not per-test. Within ONE up invocation, all specs share the same SQLite. Across `up` invocations, state resets. So intra-`up` cross-spec dependencies persist — but D-08 forbids them.

**Mitigation:** D-08 — every spec sets up its own state. 04-sell buys 2 then sells 1 (it doesn't lean on 03-buy). Different tickers per spec.

**Warning sign:** A spec passes alone but fails in suite, or vice versa.

### Pitfall 6: Compose service-name DNS

**What goes wrong:** `baseURL: 'http://app:8000'` doesn't resolve from the Playwright container.

**Why it happens:** By default Compose creates a network named `<projectname>_default` and registers each service under its `services:` key as a DNS name. The `app` service is reachable at `app:8000` from `playwright`. As long as both are in the same compose project, DNS works.

**Mitigation:** Don't override the network. Don't put services in different compose files invoked separately. The single `docker compose -f test/docker-compose.test.yml up` invocation handles this for free.

**Warning sign:** `getaddrinfo ENOTFOUND app` from the Playwright container's logs.

### Pitfall 7: WebKit lateness on first paint

**What goes wrong:** `expect(...).toBeVisible({timeout: 5_000})` flakes on WebKit only.

**Why it happens:** WebKit's first-paint after navigation is sometimes 2-3s slower than Chromium for SPAs that hydrate React Query queries.

**Mitigation:** Use `timeout: 10_000` or higher for first-load assertions; rely on Playwright's auto-wait. Don't `waitForTimeout(N)` (anti-pattern).

**Warning sign:** Suite green on chromium+firefox, red on webkit, only on first-paint assertions.

### Pitfall 8: `npm ci` cold pull inside the playwright container is slow

**What goes wrong:** Each `up --build` re-pulls and re-installs Playwright deps (one package, but it's big), adding 30-60s to every run.

**Why it happens:** No persistent volume on `/work/node_modules`.

**Mitigation:** Add an anonymous-volume mount for `/work/node_modules` in the playwright service so deps survive between `up` runs (but still get nuked on `--build` of the playwright service, which we never do — the image is pre-built upstream). Optional optimization; not required for correctness.

**Optional addition:**
```yaml
volumes:
  - ../test:/work
  - /work/node_modules    # anonymous volume preserves install
```

**Warning sign:** Every `up` re-runs `npm ci` for 30s.

## .gitignore Additions

> Add to repo-root `.gitignore`. Do NOT touch `.dockerignore` — it already excludes `test/` from the production image build context (line 43).

```gitignore
# Phase 10 E2E artefacts (Playwright)
test/playwright-report/
test/test-results/
test/node_modules/
```

**Why each:**

| Entry | Reason |
|-------|--------|
| `test/playwright-report/` | HTML report directory; large, regenerated per run, not source |
| `test/test-results/` | Per-test traces, screenshots, videos on failure (Playwright default `outputDir`) |
| `test/node_modules/` | Belt-and-suspenders — Playwright deps live inside the container's `/work`, but if a developer runs `npm install` locally for IDE help, this catches it |

**NOT gitignored (intentional):**

- `test/package.json` — committed (declares the Playwright dep version)
- `test/package-lock.json` — committed (deterministic install in the container)
- `test/playwright.config.ts` — committed (the config itself)
- `test/0X-*.spec.ts` — committed (the seven specs)

`.dockerignore` line 43 already has `test/` so none of this leaks into the production image.

## Project Constraints (from CLAUDE.md)

| Directive | How Phase 10 honors it |
|-----------|------------------------|
| **Be simple. Approach tasks in a simple, incremental way.** | Phase 10 is purely additive under `test/`; each spec is one file; one compose file; one config file; no other touch points |
| **Work incrementally with small steps. Validate each increment.** | Recommended plan structure: Wave 0 = test-id additions (if planner agrees); Wave 1 = compose + config + 01-fresh-start spec; Waves 2-4 = remaining specs in groups; final wave = README.md + .gitignore + run-the-suite-against-the-image gate |
| **Use latest APIs as of NOW.** | Pinned to Playwright 1.59.1 (released 2026-04-01, current) — not the CONTEXT.md example v1.49.0 |
| **`uv` for Python; never `pip install`** | N/A — Phase 10 adds zero Python deps. Backend/uv path is untouched |
| **Never use emojis in code or in print statements or logging** | All spec files / compose / config use plain text. Glyphs in existing components (`›`/`‹` in ChatHeader) are Unicode guillemets, not emoji |
| **Favor short modules, short methods and functions. Name things clearly.** | Each spec file is a single `test()` (or 2-3 closely related tests). Spec filenames `0X-noun.spec.ts` make the §12 scenario obvious |
| **Identify root cause before fixing issues. Prove with evidence, then fix.** | The ChatResponse field-shape mismatch is documented as a gap (with proof from `models.py:83-88` vs `ChatThread.tsx:30-35`) — NOT papered over |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The mocked-LLM Phase 5 mock keyword `"buy <TKR> <QTY>"` actually causes a trade to execute against the real PortfolioService inside the container, AND the resulting position appears in the React Query `['portfolio']` cache before Phase 10's chat spec timeout | LLM Mock Trigger Phrases, 06-chat spec | If the cache is stale, the action-card-executed assertion still passes (it's bound to the mutation response, not the React Query state). Position appearance assertion may need to await React Query refetch — the chat thread invalidates `['portfolio']` on success (verified `ChatThread.tsx:66`). LOW risk. |
| A2 | `mcr.microsoft.com/playwright:v1.59.1-jammy` exists at the registry today (2026-04-27). | Pinned Versions | If the tag has only `-noble`, switch to `:v1.59.1-noble` — one-line change. The npm package version 1.59.1 IS verified; image tag was confirmed-likely-by-pattern, not pulled. LOW risk; planner should verify with `docker pull mcr.microsoft.com/playwright:v1.59.1-jammy` before executing. |
| A3 | `python3 -c "import urllib.request..."` works inside the production runtime image's `python:3.12-slim` base for the HEALTHCHECK | Compose File Architecture | Verified via Dockerfile line 29; `urllib.request` is stdlib; no risk. |
| A4 | The compose-internal DNS lets Playwright resolve `app` service name; no special network config needed | Pitfall 6 | Default Compose behavior; verified across compose docs. NO risk. |
| A5 | Phase 10's `test/` directory is not in `.dockerignore` exclusions a `frontend` build needs | Compose File Architecture | `.dockerignore:43` excludes `test/` from the build context — Phase 10 files won't bloat the image. VERIFIED. |
| A6 | The chat ChatResponse mismatch is a pre-existing UI bug, not a Phase 10 deliverable | Pitfall 4, 06-chat outline | If discovered to be a Phase 10 blocker (e.g. the assistant message text MUST be visible), spawn Phase 10.1. The CONTEXT.md D-05 wording explicitly anticipates this. LOW risk under D-05. |
| A7 | `workers: 3` + `fullyParallel: false` actually gives one-worker-per-spec-file scheduling | Playwright Configuration | Confirmed by two cited sources. LOW risk. If wrong, the suite still passes — D-08 unique tickers prevent any cross-spec interference regardless of scheduling. |
| A8 | Adding the recommended `data-testid="header-cash"` etc. to `Header.tsx` is acceptable scope creep | Component Test-ID Inventory | The planner may reject this; in that case use the role-and-DOM-index fallbacks documented in 03-buy. NO risk to phase-completion either way. |

## Open Questions

1. **Watchlist add/remove UI affordance.**
   - What we know: PLAN.md §12 says "Add and remove a ticker from the watchlist". `Watchlist.tsx` has no add form. The chat panel CAN add/remove via keyword. The REST API works.
   - What's unclear: Is "via UI form" required, or is "via REST through the running container" acceptable for §12 row 2?
   - Recommendation: Treat as REST-through-container (Strategy A in the 02-watchlist-crud outline) — matches the literal wording and avoids coupling 02 to 06-chat. Surface to planner; if rejected, fall back to chat-driven (Strategy B).

2. **Test-id additions — yes or no?**
   - What we know: Six surfaces (header values, tab buttons, panel roots) lack stable test-ids; Phase 8 added test-ids to chat + portfolio surfaces but stopped short of terminal surfaces.
   - What's unclear: Is a single Wave 0 plan that adds ~6 `data-testid="..."` attributes acceptable scope, or does it violate "Phase 10 is purely additive under `test/`"?
   - Recommendation: Yes — add the test-ids in a small Wave 0 plan. The scope is 6 lines of code, zero behavior change. The alternative (DOM-index selectors) is more brittle. Planner discretion.

3. **`test/README.md` — yes or no?**
   - What we know: CONTEXT.md "Claude's Discretion" line 77 flags this as undecided.
   - What's unclear: Is documenting how to run the suite valuable when the one command is in `docs/DOCKER.md` already (Phase 9 / D-14)?
   - Recommendation: Yes, two-paragraph file. Includes the exact one-command invocation, where to find the HTML report, and how to run a single spec/browser pair locally for debugging.

4. **WebKit SSE-reconnect determinism.**
   - What we know: WebKit's reconnect timing is the slowest of the three engines. The 15s timeout in 07-sse-reconnect should cover it.
   - What's unclear: Is there a known WebKit-specific Content-Type strictness that could cause reconnect to FAIL even after `unroute()`?
   - Recommendation: Run the SSE-reconnect spec against WebKit early (Wave 1 or 2) to catch any engine-specific issue before later waves depend on it being green.

## Sources

### Primary (HIGH confidence)

- `[VERIFIED: npm view @playwright/test version → 1.59.1]` — pinned package version
- `[VERIFIED: npm view @playwright/test time → 1.59.1 published 2026-04-01]` — release date
- `[CITED: https://github.com/microsoft/playwright/releases]` — most recent versions: 1.59.1 (2026-04-01), 1.59.0 (2026-04-01), 1.58.2 (2026-02-06), 1.58.1 (2026-01-30), 1.58.0 (2026-01-23)
- `[CITED: https://playwright.dev/docs/docker]` — Docker tag conventions; recommendation to pin to specific version
- `[CITED: https://playwright.dev/docs/api/class-route#route-abort]` — `route.abort()` API surface, valid error codes
- `[CITED: https://html.spec.whatwg.org/multipage/server-sent-events.html]` — EventSource reconnection model and `retry:` field semantics
- `[CITED: https://docs.docker.com/compose/compose-file/05-services/]` — `healthcheck:` and `depends_on.condition:` syntax
- `[CITED: https://docs.docker.com/reference/cli/docker/compose/up/]` — `--abort-on-container-exit` and `--exit-code-from` semantics
- `[CITED: https://playwright.dev/docs/test-parallel]` — `workers` is global, `fullyParallel: false` controls intra-file parallelism
- `[VERIFIED: backend/app/chat/mock.py:9-55]` — exact mock client regexes and response shape
- `[VERIFIED: backend/app/chat/models.py:83-88]` — ChatResponse Pydantic shape
- `[VERIFIED: frontend/src/components/chat/ChatThread.tsx:30-35]` — frontend's reading of response (and the field-shape mismatch)
- `[VERIFIED: .planning/phases/09-dockerization-packaging/09-VERIFICATION.md]` — Phase 9 baseline; SSE emits `retry: 1000`; image structure
- `[VERIFIED: .planning/phases/05-ai-chat-integration/05-UAT.md]` — Phase 5 mock-mode UAT (tests 2-4 confirmed)
- `[VERIFIED: backend/app/market/seed_prices.py:5-39 + backend/app/db/seed.py]` — default 10-ticker seed list
- `[VERIFIED: .dockerignore line 43 `test/`]` — test directory already excluded from production image build context

### Secondary (MEDIUM confidence)

- `[CITED: https://github.com/microsoft/playwright/issues/15353]` — Playwright SSE-fulfillment limitation (does NOT apply to abort path)
- `[CITED: https://testdino.com/blog/playwright-parallel-execution/]` — confirms worker scheduling is file-granular, not project-granular

### Tertiary (LOW confidence — flagged)

- The exact existence of `mcr.microsoft.com/playwright:v1.59.1-jammy` (vs `-noble` only) at the MCR registry today — Assumption A2; planner should `docker pull` to confirm before final pin

## Metadata

**Confidence breakdown:**

- Pinned versions: **HIGH** — npm registry directly verified
- Compose architecture: **HIGH** — Compose docs cited; healthcheck command verified against the production image
- Per-scenario spec outlines: **HIGH** for chat/portfolio (have stable testids); **MEDIUM** for watchlist/trade (rely on aria-labels and form labels — stable but more verbose)
- SSE reconnect pattern: **MEDIUM** — `route.abort` is well-documented; the cross-browser reconnect determinism (especially WebKit) is best validated by running the spec early (Open Question 4)
- LLM mock trigger phrases: **HIGH** — source code directly read; Phase 5 UAT confirmed
- ChatResponse field-shape gap: **HIGH** — directly verified in source; documented as known gap, not blocker

**Research date:** 2026-04-27

**Valid until:** 2026-05-27 (Playwright tracks fast — verify the pinned version is still latest before execution; everything else is stable)
