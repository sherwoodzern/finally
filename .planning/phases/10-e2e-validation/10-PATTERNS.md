# Phase 10: E2E Validation - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 11 new files + 1 modified (.gitignore) + optional Wave 0 frontend test-id additions
**Analogs found:** 1 partial (`frontend/vitest.config.mts` partially constrains `test/playwright.config.ts`); 13 of 14 files are greenfield under `test/`

## Greenfield Notice

Like Phase 9, Phase 10 introduces a new top-level directory (`test/`) that does not yet exist. There is **no existing Docker Compose file**, **no existing Playwright config**, **no existing E2E spec**, and **no existing root-level Node project**. Eleven of the twelve new artefacts have **no in-repo analog**.

This PATTERNS.md therefore mixes two formats:

1. **Pattern Assignment** for the one partial analog (`playwright.config.ts` ← `frontend/vitest.config.mts`).
2. **Constraint Inventory** (Phase 9 style) for everything else — for each new file, the in-repo "source of truth" files that constrain it (selectors the test must hit, env vars the compose service must set, container layout, mock keywords), with verbatim excerpts the planner MUST preserve.

The "patterns" here are mostly **invariants the new artefacts must respect**, not code excerpts to copy. The CONTEXT.md decisions (D-01..D-13) and RESEARCH.md drafts (full compose YAML, full playwright.config.ts, per-spec outlines) are the primary authority — this map ensures the planner plumbs each plan back into the **right existing-codebase anchor points**.

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `test/docker-compose.test.yml` (NEW) | config (orchestration) | batch / event-driven (compose lifecycle) | `Dockerfile` (build target only); `scripts/start_mac.sh` (run-args mirror) | partial — see Constraint Inventory |
| `test/playwright.config.ts` (NEW) | config (test runner) | request-response (browser ↔ app) | `frontend/vitest.config.mts` | partial role match (test-runner config) |
| `test/package.json` (NEW) | config (Node project) | batch (npm ci) | `frontend/package.json` | shape-only (mirror lockfile pattern) |
| `test/package-lock.json` (NEW, generated) | config (lockfile) | batch (npm ci) | `frontend/package-lock.json` | shape-only |
| `test/01-fresh-start.spec.ts` (NEW) | test (E2E) | request-response | `frontend/src/components/terminal/Header.test.tsx` | role-only — Vitest, not Playwright |
| `test/02-watchlist-crud.spec.ts` (NEW) | test (E2E API) | CRUD | none (no existing API-driven test in repo) | constraint-only |
| `test/03-buy.spec.ts` (NEW) | test (E2E) | CRUD via UI | `frontend/src/components/terminal/TradeBar.test.tsx` | role-only — Vitest, not Playwright |
| `test/04-sell.spec.ts` (NEW) | test (E2E) | CRUD via UI | `frontend/src/components/terminal/TradeBar.test.tsx` | role-only — Vitest, not Playwright |
| `test/05-portfolio-viz.spec.ts` (NEW) | test (E2E) | request-response | `frontend/src/components/portfolio/Heatmap.test.tsx`, `frontend/src/components/portfolio/PnLChart.test.tsx` | role-only — Vitest, not Playwright |
| `test/06-chat.spec.ts` (NEW) | test (E2E) | request-response | `frontend/src/components/chat/ChatInput.test.tsx`, `frontend/src/components/chat/ActionCardList.test.tsx` | role-only — Vitest, not Playwright |
| `test/07-sse-reconnect.spec.ts` (NEW) | test (E2E network) | streaming | none (Vitest tests don't exercise SSE network paths) | constraint-only |
| `test/README.md` (NEW, recommended) | documentation | static | `README.md`, `docs/DOCKER.md` | tone-only |
| `.gitignore` (MODIFIED) | config (VCS) | batch | `.gitignore` (existing) | edit-in-place |
| **Optional Wave 0:** `frontend/src/components/terminal/Header.tsx`, `TabBar.tsx`, `Watchlist.tsx`, `PositionsTable.tsx`, `TradeBar.tsx` (MODIFIED — add `data-testid`) | UI attribute | n/a | existing `data-testid` usage in `chat/`, `portfolio/`, `skeleton/` | excellent — see "Test-ID addition pattern" |

## Pattern Assignments

### `test/playwright.config.ts` (test runner config)

**Analog (partial):** `frontend/vitest.config.mts`

The match is shallow (both are TypeScript test-runner configs that `defineConfig`-export a single object), but the analog establishes the project's preferred shape: ESM module, `defineConfig` from the framework, top-level config object, no `module.exports` / CommonJS.

**Imports pattern** (`frontend/vitest.config.mts:1-3`):
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
```

**Apply to `playwright.config.ts`:** mirror the `import { defineConfig, devices } from '@playwright/test';` shape — same single-line import-then-export style.

**Top-level config pattern** (`frontend/vitest.config.mts:5-12`):
```typescript
export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
  },
});
```

**Apply to `playwright.config.ts`:** single `export default defineConfig({...})`. RESEARCH.md §"Playwright Configuration" (lines 311-379) provides the **full file body** verbatim — copy that, do not invent.

**Limitation of the analog:** Vitest config has NO `projects` array, NO browser matrix, NO worker count, NO retries, NO reporters, NO baseURL. All of those are net-new — derived from D-02, D-07, D-09, NOT from the Vitest config.

### `test/0X-*.spec.ts` (seven Playwright spec files)

**Analog (role-only):** Vitest component tests under `frontend/src/components/**/*.test.tsx`.

**The match is structural, not behavioural.** Vitest tests render components in jsdom and stub `fetch`; Playwright tests drive a real browser against a live container. The shared shape is:

| Property | Vitest pattern | Playwright Phase 10 pattern |
|----------|----------------|------------------------------|
| `describe(...)` block | yes | optional (Playwright recommends top-level `test()`) |
| `it(...)` / `test(...)` | yes — both | use `test(...)` (matches Playwright examples) |
| Selector convention | `screen.getByPlaceholderText`, `getByRole`, `getByTestId` | `page.getByLabel`, `page.getByRole`, `page.getByTestId` |
| Assertion style | `expect(el).toBeInTheDocument()`, `toHaveTextContent(...)` | `expect(locator).toBeVisible()`, `toContainText(...)`, `toHaveText(...)` |
| Network mocking | `vi.stubGlobal('fetch', ...)` | `page.route('**/path', ...)`, `route.abort('connectionreset')` |
| Test isolation | `afterEach(() => vi.unstubAllGlobals())` | `test.afterEach(...)` (rarely needed; per-test fresh page) |

**Concrete selector excerpts to mirror across Vitest → Playwright:**

`frontend/src/components/terminal/TradeBar.test.tsx:13-18`:
```typescript
function fillAndClick(ticker: string, qty: string, side: 'Buy' | 'Sell') {
  const tickerInput = screen.getByPlaceholderText('AAPL') as HTMLInputElement;
  const qtyInput = screen.getByPlaceholderText('1') as HTMLInputElement;
  fireEvent.change(tickerInput, { target: { value: ticker } });
  fireEvent.change(qtyInput, { target: { value: qty } });
  fireEvent.click(screen.getByRole('button', { name: side }));
}
```

→ Playwright equivalent for `03-buy.spec.ts` and `04-sell.spec.ts` (RESEARCH.md §"03-buy.spec.ts" lines 466-495 and §"04-sell.spec.ts" lines 514-533):
```typescript
await page.getByLabel('Ticker').fill('NVDA');
await page.getByLabel('Quantity').fill('1');
await page.getByRole('button', { name: 'Buy' }).click();
```

**WHY** the selector swap: Vitest's `getByPlaceholderText('AAPL')` works because jsdom respects `placeholder=`; Playwright tests against a real DOM where the `<label>` text "Ticker" / "Quantity" wraps the input (`TradeBar.tsx:84-86, 100-102`), so `getByLabel(...)` is more stable AND uses the canonical Playwright "user-facing" locator strategy.

`frontend/src/components/chat/ChatInput.test.tsx:15-19`:
```typescript
const ta = screen.getByPlaceholderText('Ask me about your portfolio…');
fireEvent.change(ta, { target: { value: '  hello  ' } });
fireEvent.keyDown(ta, { key: 'Enter' });
```

→ Playwright equivalent for `06-chat.spec.ts` (RESEARCH.md §"06-chat.spec.ts" lines 602-619):
```typescript
await page.getByLabel('Ask the assistant').fill('buy AMZN 1');
await page.getByRole('button', { name: 'Send' }).click();
```

**WHY** the locator swap: ChatInput has `aria-label="Ask the assistant"` (`ChatInput.tsx:48`) — that is the canonical accessibility-tree label and works identically across Chromium / Firefox / WebKit.

`frontend/src/components/portfolio/Heatmap.test.tsx:60`:
```typescript
expect(screen.getByTestId('heatmap-skeleton')).toBeInTheDocument();
```

→ Playwright equivalent for `05-portfolio-viz.spec.ts` (RESEARCH.md §"05-portfolio-viz.spec.ts" lines 555-573):
```typescript
await expect(page.getByTestId('heatmap-treemap')).toBeVisible({ timeout: 10_000 });
await expect(page.getByTestId('pnl-chart')).toBeVisible({ timeout: 10_000 });
await expect(page.getByTestId('pnl-summary')).toBeVisible();
```

**WHY** the assertion swap: jsdom's `toBeInTheDocument()` is layout-blind; the real browser actually paints, so `toBeVisible()` is the correct cross-engine assertion.

**Imports pattern (Playwright spec):**
```typescript
import { test, expect } from '@playwright/test';
```

That single-line import is the entire boilerplate. No render helper, no provider wrapper, no fixture import — Playwright's `page` and `request` arrive via the test fixture.

## Constraint Inventory (no analog — copy-from-source-of-truth)

### `test/docker-compose.test.yml` (NEW)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `Dockerfile` lines 9-65 — locks `WORKDIR /app/backend`, `EXPOSE 8000`, `STOPSIGNAL SIGINT`, `CMD ["uv","run","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]`. Compose's `app` service builds from this exact Dockerfile via `build: context: ..` (D-04).
- `Dockerfile:29` — `FROM python:3.12-slim AS runtime`. The compose-side HEALTHCHECK uses `python3 -c "import urllib.request..."` because curl is intentionally absent (RESEARCH.md §"Why python3 in the healthcheck instead of curl" lines 300-304).
- `Dockerfile:53-57` — `ENV DB_PATH=/app/db/finally.db`, `VOLUME /app/db`. The compose service deliberately omits a `volumes:` mapping for `/app/db` so an anonymous volume is created per `up` invocation (D-06). DO NOT add `finally-data:/app/db` to the compose file.
- `.env.example` (sibling file) — declares `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`. The compose `app.environment` block sets `LLM_MOCK: "true"` + `OPENROUTER_API_KEY: ""` + `MASSIVE_API_KEY: ""` (D-05). DO NOT use `--env-file .env` here — Phase 10 must NOT depend on the developer's local API keys.
- `scripts/start_mac.sh` lines 52-57 — the canonical `docker run` argument set for production. The compose `app` service is the **same image** as production but with **only one delta** (`LLM_MOCK=true`) and **no host volume mount**. Drift between `start_mac.sh` and the compose service's runtime config beyond that single env override = bug.
- `backend/app/main.py` (entrypoint) — confirms `app.main:app` import works against the workdir set by Dockerfile.
- `RESEARCH.md` lines 209-271 — full YAML body draft. Planner copies this verbatim into `test/docker-compose.test.yml`.

**Compose architecture invariants:**

1. **Build context (D-04):** `build: { context: .., dockerfile: Dockerfile }`. The `..` is relative to `test/docker-compose.test.yml`'s directory, i.e. the repo root. NOT a registry pull. NOT a separate Dockerfile under `test/`.
2. **Service names (Pitfall 6):** `app` and `playwright`. The Playwright container's `baseURL: http://app:8000` only works because compose-default DNS exposes `app` to other services in the same compose project. DO NOT rename either service without also updating `playwright.config.ts` and the compose-internal `BASE_URL` env override.
3. **HEALTHCHECK location (D-10):** Compose-side ONLY. The production `Dockerfile` does NOT have a HEALTHCHECK (Phase 9 / D-08 of Phase 9 CONTEXT). Adding HEALTHCHECK to the production Dockerfile is OUT OF SCOPE for Phase 10.
4. **Service ordering (D-10):** `playwright.depends_on.app.condition: service_healthy`. Eliminates the need for `wait-for-it.sh` shims.
5. **Volume mount (Playwright service):** `../test:/work` — host-relative to compose file's directory. The Playwright container reads `/work/playwright.config.ts`, `/work/package.json`, `/work/0X-*.spec.ts` and writes `/work/playwright-report/` + `/work/test-results/` back to the host (which is gitignored).
6. **Anonymous node_modules volume (Pitfall 8 — optional optimization):** RESEARCH.md §"Pitfall 8" lines 977-991 documents an anonymous-volume mount for `/work/node_modules` to preserve `npm ci` between runs. Planner discretion.

**The one-command UX is fixed (D-03):**
```bash
docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright
```
NO wrapper script. NO `npm run e2e`. NO Makefile target. The compose CLI is the entire UX surface.

### `test/playwright.config.ts` (NEW)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `RESEARCH.md` lines 311-379 — full TypeScript body draft. Planner copies this verbatim.
- `frontend/vitest.config.mts` (analog) — establishes the project's preferred config-file shape (ESM, `defineConfig` from framework, single default-export).
- `frontend/tsconfig.json` — confirms TypeScript is the project standard (the spec files are `.ts`, the config is `.ts`, no `.js` mixed in).
- `RESEARCH.md` §"Worker-semantics confirmation" lines 382-388 — proves `workers: 3` + `fullyParallel: false` achieves D-07's intent (one worker per spec file, three browsers in parallel via project-level scheduling).

**Configuration invariants from CONTEXT.md (NOT inferable from any in-repo file):**

| Property | Value | Source |
|----------|-------|--------|
| `testDir` | `'.'` | D-09 |
| `testMatch` | `/\d{2}-.+\.spec\.ts$/` | RESEARCH.md line 320 |
| `baseURL` | `process.env.BASE_URL ?? 'http://app:8000'` | D-09 |
| `retries` | `process.env.CI ? 1 : 0` | D-09 |
| `workers` | `3` | D-07 + RESEARCH §worker-semantics |
| `fullyParallel` | `false` | D-07 + RESEARCH §worker-semantics |
| `reporter` | `[['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]]` | D-09 |
| `outputDir` | `'test-results'` | RESEARCH §gitignore |
| `projects` | `[chromium, firefox, webkit]` (use `devices['Desktop Chrome'/Firefox/Safari']`) | D-02 |
| `timeout` | `30_000` (per-test) | RESEARCH.md line 369 |
| `actionTimeout` | `10_000` | RESEARCH.md line 364 |

**DO NOT** reuse Vitest's `setupFiles: ['./vitest.setup.ts']` pattern. The Vitest setup file stubs `ResizeObserver` for jsdom (`frontend/vitest.setup.ts:9-14`) — irrelevant in a real browser. Phase 10 has no setup-file requirement; specs are self-sufficient.

### `test/package.json` (NEW)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `frontend/package.json` (shape analog) — establishes `name`, `private: true`, `version`, `scripts.test`, `devDependencies` shape.
- `RESEARCH.md` lines 185-198 — full JSON body draft.

**Shape excerpt to mirror** (`frontend/package.json:1-15`):
```json
{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "engines": {
    "node": ">=20.0.0 <21"
  },
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    ...
    "test": "vitest",
    "test:ci": "vitest run"
  },
  ...
}
```

**Apply to `test/package.json`:**
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

**Invariants:**

1. **Pin exact, not caret** (per CLAUDE.md "Use latest APIs as of NOW" + RESEARCH.md line 155): `"@playwright/test": "1.59.1"` — no `^`. Reproducibility wins over churn-friendliness inside a test harness.
2. **NO `node` engines field** — the Playwright Docker image ships its own Node v22 LTS (RESEARCH.md line 171); pinning the host Node version here would be misleading.
3. **`scripts.test`** matches the `frontend/package.json:13` shape (`"test": "vitest"` → `"test": "playwright test"`). Both stay valid `npm test` invocations.
4. **Lockfile commitment** — `test/package-lock.json` MUST be committed (RESEARCH.md line 200, line 1015), generated once via `npm install` then locked in.

### `test/package-lock.json` (NEW, generated)

**Source-of-truth files the planner MUST reference:**

- `frontend/package-lock.json` (shape reference; do not copy contents) — generated by `npm install`, committed to the repo, used by `npm ci` in Stage 1 of the Dockerfile (`Dockerfile:18`).

**Generation procedure:**
1. Inside `test/`, run `npm install` once locally (or use a temporary node container).
2. Commit the resulting `package.json` AND `package-lock.json` together.
3. Inside the compose Playwright service: `npm ci` (NOT `npm install`) — deterministic install from lockfile.

This mirrors the Stage 1 Dockerfile pattern (`Dockerfile:17-18`):
```dockerfile
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
```

### `test/01-fresh-start.spec.ts` (E2E test, request-response)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `RESEARCH.md` §"01-fresh-start.spec.ts" lines 394-415 — full assertion list and selector strategy.
- `backend/app/db/seed.py` + `backend/app/market/seed_prices.py:5-39` — confirms the 10-ticker seed (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) and `cash_balance=10000.0`.
- `frontend/src/components/terminal/WatchlistRow.tsx:45-46` — selector source: each row is `<tr role="button" aria-label="Select {ticker}">`.
- `frontend/src/components/terminal/Header.tsx:38-53` — header structure: `Total $X` then `Cash $X`. Cash is the second money span, hence the `nth(1)` fallback (or `data-testid="header-cash"` after the optional Wave 0 plan).
- `frontend/src/components/terminal/ConnectionDot.tsx:30` — `aria-label={`SSE ${status}`}`. For "streaming" assertion, prefer asserting the connection-dot eventually reports `SSE connected`, OR assert a price cell stops being `—`.

**Invariants:**

1. **Default seed is the assertion target.** D-13 explicitly couples this spec to Phase 2's seed. If a future phase changes the seed list, this spec needs updating. NOT a test-side abstraction.
2. **Cash format is `$10,000.00`** — verified by `Header.tsx:15-20` `formatMoney()`: `minimumFractionDigits: 2, maximumFractionDigits: 2`, `en-US` locale. Match exactly.
3. **Streaming proof.** RESEARCH.md recommends `expect(row).not.toContainText('—')` with a generous timeout. Em-dash `—` is the `WatchlistRow` placeholder (verify in `WatchlistRow.tsx`).

### `test/02-watchlist-crud.spec.ts` (E2E API test, CRUD)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `RESEARCH.md` §"02-watchlist-crud.spec.ts" lines 417-452 — strategy decision (REST via `request.post()` over UI form).
- `backend/app/watchlist/routes.py` (Phase 4) — confirms `POST /api/watchlist {ticker}` returns `{status: "added" | "exists"}`, `DELETE /api/watchlist/{ticker}` returns `{status: "removed" | "not_present"}`.
- RESEARCH.md "Open Question 1" lines 1048-1052 — the UI has no add/remove form; the canonical CRUD path is REST. Acceptable per literal PLAN.md §12 wording.
- D-08 (CONTEXT.md) — pick a ticker NOT in the seed: `PYPL`, `IBM`, `ORCL`. Recommended: `PYPL`.

**Invariants:**

1. **Use `request` fixture, not `page`.** Playwright's `{ request }` test fixture issues HTTP from the test runner directly, hitting `http://app:8000` via `baseURL`. No browser process spawned for this spec → minimal cross-engine overhead.
2. **Status-code AND status-string assertion.** Both `add.ok()` AND `(await add.json()).status === 'added' | 'exists'` — the API treats duplicates as idempotent, not 4xx (verify against Phase 4 routes).

### `test/03-buy.spec.ts`, `test/04-sell.spec.ts` (E2E UI test, CRUD via UI)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `RESEARCH.md` §"03-buy.spec.ts" lines 454-505 and §"04-sell.spec.ts" lines 508-540 — full assertion list and code shape.
- `frontend/src/components/terminal/TradeBar.tsx:82-141` — trade-bar UI structure, label-driven inputs, button names.
- `frontend/src/components/terminal/PositionRow.tsx:53-54` — `<tr role="button" aria-label="Select {ticker}">` for positions table rows.
- `backend/app/portfolio/routes.py` (Phase 3) — `POST /api/portfolio/trade` request/response shape. The trade is what the UI calls; the test does NOT call this directly, but it MUST confirm the same shape is acknowledged.

**Selector excerpts (verbatim, copy into spec)** — RESEARCH.md §"03-buy.spec.ts" lines 466-472:
```typescript
await page.getByLabel('Ticker').fill('NVDA');
await page.getByLabel('Quantity').fill('1');
await page.getByRole('button', { name: 'Buy' }).click();
await expect(
  page.getByRole('button', { name: 'Select NVDA' })
).toBeVisible({ timeout: 10_000 });
```

**Invariants:**

1. **D-08 unique-ticker rule:** 03-buy uses `NVDA`, 04-sell uses `JPM`, 05-portfolio-viz uses `META`, 06-chat uses `AMZN`. Cross-spec collisions = state interference within a single `up` invocation.
2. **Cold-cache mitigation (RESEARCH §Pitfall 1 lines 906-914):** the simulator must have produced ≥1 tick for the ticker before the trade fires. The 15s `start_period` healthcheck plus `goto('/')` + Playwright's auto-wait is the recommended mitigation.
3. **No exact cash-amount assertion** — the simulator price moves; assert `cashAmount < 10_000` or use a tolerance. Hard-coding `$9,809.98` (the Phase 9 verification observed value) WILL flake.

### `test/05-portfolio-viz.spec.ts` (E2E test, request-response)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `RESEARCH.md` §"05-portfolio-viz.spec.ts" lines 542-582.
- `frontend/src/components/portfolio/Heatmap.tsx:83, 117` — `data-testid="heatmap-skeleton"` (no positions) and `data-testid="heatmap-treemap"` (with positions).
- `frontend/src/components/portfolio/PnLChart.tsx:59, 70, 93` — `data-testid="pnl-summary"`, `pnl-skeleton`, `pnl-chart`.
- `frontend/src/components/terminal/TabBar.tsx` — tab buttons have `role="tab"`; `aria-pressed` toggles state.

**Invariants:**

1. **Test buys its own setup state** (D-08): heatmap renders skeleton if no positions; this spec buys `META × 1` to trigger the treemap render.
2. **Use `data-testid` everywhere viz surfaces are concerned** — these IDs are stable across copy and theme changes. RESEARCH.md §"Component Test-ID Inventory" lines 791-812 confirms each.
3. **TabBar role** — `getByRole('tab', { name: /heatmap/i })` and `getByRole('tab', { name: /p.+l/i })`. Regex tolerates "P&L" / "PnL" / "P/L" copy variants.

### `test/06-chat.spec.ts` (E2E test, request-response)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `RESEARCH.md` §"06-chat.spec.ts" lines 584-633.
- `backend/app/chat/mock.py:9-55` — the four LLM_MOCK regexes and trigger phrases.
- `backend/app/chat/models.py:83-88` — `ChatResponse` Pydantic shape (returns `message`, `trades`, `watchlist_changes`).
- `frontend/src/components/chat/ChatThread.tsx:30-35, 100` — frontend reads `res.id`, `res.content`, `res.created_at` (FIELD-SHAPE MISMATCH — see Pitfall 4).
- `frontend/src/components/chat/ActionCard.tsx:98` — `data-testid={`action-card-${status}`}`. Trade-executed → `action-card-executed`. Trade-failed → `action-card-failed`.
- `frontend/src/components/chat/ChatInput.tsx:48` — `aria-label="Ask the assistant"`.
- `frontend/src/components/chat/ChatInput.tsx:56` — Send button has text "Send".

**KNOWN GAP — DO NOT ASSERT ON ASSISTANT BUBBLE TEXT.** RESEARCH.md §"06-chat.spec.ts" lines 621-625 documents the ChatResponse field-shape mismatch: the assistant bubble renders as empty string. **Phase 10 specs assert on `[data-testid=action-card-executed]`, NOT on `[data-testid=chat-message-assistant]` text content.** This is the CONTEXT.md D-05 anticipated gap.

**LLM mock keyword** (verbatim from `backend/app/chat/mock.py:9-15`):
```
\bbuy\s+([A-Z][A-Z0-9.]{0,9})\s+(\d+(?:\.\d+)?)\b
```
→ `"buy AMZN 1"` triggers a TradeAction; mock returns `{message: "Mock: executing buy AMZN 1.0", trades: [{...status:"executed"|"failed"}], watchlist_changes: []}`. Phase 5 UAT confirms the auto-execution path works (RESEARCH.md lines 887-892).

### `test/07-sse-reconnect.spec.ts` (E2E network test, streaming)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `RESEARCH.md` §"07-sse-reconnect.spec.ts" lines 635-729 AND §"SSE Reconnect Test Pattern" lines 731-783.
- `frontend/src/components/terminal/ConnectionDot.tsx:9-30` — three statuses (`connected` / `reconnecting` / `disconnected`) and the `aria-label={`SSE ${status}`}` template.
- `frontend/src/lib/price-store.ts` (read for `selectConnectionStatus`) — confirms how SSE error events propagate to `status: 'reconnecting' | 'disconnected'`.
- `backend/app/market/sse_routes.py` (Phase 1) — the SSE response includes `retry: 1000` (verified Phase 9 row 5). Gives a known 1s reconnect floor.

**Invariants:**

1. **Use `route.abort('connectionreset')`, not `route.fulfill()`** — Playwright issue #15353 affects fulfilling, not aborting (RESEARCH.md §"Pitfall 3" lines 926-934).
2. **Use `context.route()` over `page.route()`** — survives navigation, covers EventSource auto-retries (RESEARCH.md §"SSE Reconnect Test Pattern" lines 740-768).
3. **Tolerate either `reconnecting` OR `disconnected`** — the yellow→red transition can be too fast to catch deterministically; regex match `/^SSE (reconnecting|disconnected)$/` (RESEARCH.md line 661).
4. **WebKit timing** — RESEARCH.md §"WebKit caveat" lines 781-783 + §"Pitfall 7" lines 966-974 — use 15-20s timeouts on reconnect assertions; never `waitForTimeout(N)`.
5. **Run this spec early in dev (Open Question 4)** — WebKit-specific reconnect determinism is the highest-risk unknown; verify before later waves.

### `test/README.md` (NEW, recommended)

**Source-of-truth files the planner MUST reference:**

- `README.md` (existing repo Quick Start) — establishes voice / brevity.
- `docs/DOCKER.md` (Phase 9 D-14) — the user-facing "how to run" doc; this README mirrors that two-paragraph style.

**Invariants (from CLAUDE.md):**

- "Keep README.md concise" → two paragraphs maximum.
- "Never use emojis" → plain text only.
- "Use latest APIs as of NOW" → reference exact pinned Playwright tag.

**Required content:**

1. The exact one-command invocation (D-03):
   ```bash
   docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright
   ```
2. Where to find the HTML report after a run: `test/playwright-report/index.html`.
3. How to run a single spec/browser pair locally for debugging (Open Question 3 recommendation).

### `.gitignore` (MODIFIED)

**Source-of-truth file:** `.gitignore` (existing, 211 lines).

**Excerpt to mirror — section-comment style** (`.gitignore:1-3, 33-35, 49-51`):
```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
...

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Unit test / coverage reports
htmlcov/
.tox/
...
```

**Append (RESEARCH.md §".gitignore Additions" lines 993-1019):**
```gitignore
# Phase 10 E2E artefacts (Playwright)
test/playwright-report/
test/test-results/
test/node_modules/
```

**Invariants:**

1. **NOT gitignored (intentional, per RESEARCH.md lines 1012-1018):**
   - `test/package.json` — committed (declares the Playwright dep version)
   - `test/package-lock.json` — committed (deterministic install)
   - `test/playwright.config.ts` — committed (the config itself)
   - `test/0X-*.spec.ts` — committed (the seven specs)
   - `test/docker-compose.test.yml` — committed (the harness)
   - `test/README.md` — committed (if added)
2. **`*.spec` exclusion conflict** — `.gitignore:36` already has `*.spec` (PyInstaller spec files). The new specs `*.spec.ts` are NOT matched by `*.spec` (gitignore only matches files named exactly `*.spec` — different extension). VERIFIED no conflict; no change needed.
3. **Do NOT touch `.dockerignore`** — line 43 already excludes `test/` from the production image build context (RESEARCH.md line 1019, A5). Phase 10 files do NOT leak into the production image regardless.

### Optional Wave 0: data-testid additions (frontend/src/components/terminal/*.tsx)

**Source-of-truth files (existing test-id pattern to mirror):**

- `frontend/src/components/chat/ChatDrawer.tsx:22, 29` — the `data-testid` attribute placement on `<aside>` and `<div>` containers.
- `frontend/src/components/chat/ActionCardList.tsx:23` — `data-testid="action-card-list"` on a wrapping `<div>`.
- `frontend/src/components/portfolio/Heatmap.tsx:83, 117` — `data-testid` on skeleton placeholder + treemap container.
- `frontend/src/components/portfolio/PnLChart.tsx:59, 70, 93` — `data-testid` on summary, skeleton, chart.
- `frontend/src/components/skeleton/SkeletonBlock.tsx:16` — generic primitive that already has `data-testid="skeleton-block"`.

**Test-ID addition pattern (verbatim, the established style):**

`Heatmap.tsx:117`:
```tsx
<div className="flex-1 w-full" data-testid="heatmap-treemap">
```

`PnLChart.tsx:93`:
```tsx
<div className="flex-1 w-full" data-testid="pnl-chart">
```

→ Apply identically to:

| Component | File | Recommended attribute | DOM node |
|-----------|------|----------------------|----------|
| Header cash value | `frontend/src/components/terminal/Header.tsx:48-50` | `data-testid="header-cash"` | the `Cash` `<span>` |
| Header total value | `frontend/src/components/terminal/Header.tsx:42-45` | `data-testid="header-total"` | the `Total` `<span>` |
| TabBar individual tab buttons | `frontend/src/components/terminal/TabBar.tsx` | `data-testid={`tab-${id}`}` | each `<button role="tab">` |
| Watchlist panel root | `frontend/src/components/terminal/Watchlist.tsx:25` | `data-testid="watchlist-panel"` | the `<aside>` |
| Positions table root | `frontend/src/components/terminal/PositionsTable.tsx:28` | `data-testid="positions-table"` | the `<section>` |
| TradeBar root | `frontend/src/components/terminal/TradeBar.tsx:82` | `data-testid="trade-bar"` | the `<section>` |

**Invariants:**

1. **Zero behavioral change** — `data-testid` is a non-rendering attribute. No CSS, no event handlers reference it.
2. **Preserve existing className / aria-label / role** — additions only.
3. **No corresponding Vitest test changes required** — existing component tests use `getByTestId` where convenient (e.g., `Heatmap.test.tsx:60`); new test-ids are additive selectors that don't break old assertions.
4. **Planner discretion:** RESEARCH.md "Open Question 2" (lines 1054-1057) recommends YES; CONTEXT.md does not strictly forbid — it just says Phase 10 is "purely additive under `test/`". The test-id additions are 6 lines of additive code in `frontend/`. The alternative is brittle DOM-index selectors. Recommend doing this Wave 0.

---

## Shared Patterns

### Selector hierarchy (apply to all 7 spec files)

**Source:** RESEARCH.md §"Component Test-ID Inventory" lines 785-841 + observed practice in `frontend/src/components/**/*.test.tsx`.

**Rule (preference order, most stable first):**

1. `page.getByTestId(...)` — when a `data-testid` exists. Stable across copy, role, theme.
2. `page.getByLabel(...)` — for form inputs (`<label>` wrapping) and explicit `aria-label` attributes.
3. `page.getByRole(role, { name: ... })` — for buttons, tabs, semantic landmarks.
4. `page.getByText(...)` — last resort; couples test to UI copy.

**NEVER:**
- CSS class selectors (`page.locator('.bg-up')`) — couples to Tailwind, breaks on style refactor.
- DOM-index selectors (`page.locator('header span').nth(1)`) — brittle. Replace with test-id additions if needed.
- `waitForTimeout(N)` for "wait until streaming" — anti-pattern. Use `expect(...).toBeVisible({ timeout })` auto-wait.

### Compose-internal DNS (apply to docker-compose.test.yml + playwright.config.ts)

**Source:** Compose-default networking (RESEARCH.md §"Pitfall 6" lines 956-964).

**Rule:** From the `playwright` container, the `app` service is reachable as `http://app:8000`. Both services must live in the SAME compose project (single `docker compose -f test/docker-compose.test.yml up` invocation). Do not split into multiple compose files invoked separately.

**Apply to:**
- `playwright.config.ts`: `baseURL: process.env.BASE_URL ?? 'http://app:8000'`
- `docker-compose.test.yml`: `playwright.environment.BASE_URL: "http://app:8000"`

The env var override is belt-and-suspenders; the hardcoded fallback covers ad-hoc local runs (e.g., `npx playwright test --project=chromium` against `localhost:8000` after `docker run` of just the app container).

### LLM_MOCK env override (apply to docker-compose.test.yml + 06-chat.spec.ts)

**Source:** `backend/app/chat/mock.py:9-55` + RESEARCH.md §"LLM Mock Trigger Phrases" lines 846-902 + Phase 5 implementation.

**Rule:**
- Compose `app.environment.LLM_MOCK: "true"` is the single switch.
- Trigger phrases: `"buy <TKR> <QTY>"`, `"sell <TKR> <QTY>"`, `"add <TKR>"`, `"remove <TKR>"` (case-insensitive).
- Each trigger produces deterministic structured output that auto-executes through the same code path as a manual trade.
- DO NOT use `LLM_MOCK=false` in Phase 10 — the suite has no OpenRouter API key access in CI.
- DO NOT expand the mock to scenario-driven fixtures — explicitly out of scope per CONTEXT.md "Deferred Ideas".

### No-emojis project rule

**Source:** `CLAUDE.md` ("Never use emojis in code or in print statements or logging").

**Apply to:** All artefacts — compose YAML comments, playwright.config.ts comments, spec files (test names, console.log calls, error messages), README.md prose. The em-dash `—` is Unicode punctuation, not emoji; verify any glyph against Unicode "Symbol, Other" / "Emoji" categories before using.

### Per-spec unique tickers (apply to specs 03–06)

**Source:** D-08 + RESEARCH.md §"Pitfall 5" lines 947-955.

**Rule:**

| Spec | Ticker | Rationale |
|------|--------|-----------|
| `03-buy.spec.ts` | `NVDA` | In default seed; not used by any other state-mutating spec |
| `04-sell.spec.ts` | `JPM` | In default seed; not used by any other state-mutating spec |
| `05-portfolio-viz.spec.ts` | `META` | In default seed; not used by 03/04 |
| `06-chat.spec.ts` | `AMZN` | In default seed; not used by 03/04/05 |
| `02-watchlist-crud.spec.ts` (if REST strategy) | `PYPL` | NOT in default seed → tests true add path |
| `01-fresh-start.spec.ts` | (asserts the seed only; no mutation) | n/a |
| `07-sse-reconnect.spec.ts` | (no trade; only network manipulation) | n/a |

Cross-spec ticker collisions inside a single `up` invocation = state interference = flaky suite.

---

## No Analog Found — Files Without Match

All eleven new files under `test/` have NO in-repo behavioural analog. Rationale per file:

| File | Why no analog |
|------|---------------|
| `test/docker-compose.test.yml` | First Compose file in repo. Use the YAML body in RESEARCH.md lines 209-271 verbatim. |
| `test/playwright.config.ts` | `frontend/vitest.config.mts` is the closest shape match, but the content (`projects`, `workers`, `reporter`) is entirely net-new. Use the TS body in RESEARCH.md lines 311-379 verbatim. |
| `test/package.json` | First root-level `test/` Node project. Mirror `frontend/package.json` shape; pin `@playwright/test: 1.59.1` exact. |
| `test/package-lock.json` | First lockfile under `test/`. Generated by `npm install` once; committed; consumed by `npm ci`. |
| `test/01-fresh-start.spec.ts` | First Playwright spec. Vitest tests are jsdom-only; cannot serve as code-shape analog. |
| `test/02-watchlist-crud.spec.ts` | First API-only Playwright spec; uses `request` fixture. |
| `test/03-buy.spec.ts` | First UI-driven Playwright spec; structurally mirrors `TradeBar.test.tsx` (Vitest), but selectors and assertions differ (label-driven vs placeholder-driven; `toBeVisible` vs `toBeInTheDocument`). |
| `test/04-sell.spec.ts` | Same as 03-buy. |
| `test/05-portfolio-viz.spec.ts` | Heatmap and PnLChart Vitest tests use jsdom + Recharts mock; Playwright runs against a real browser → no Recharts mocking needed. |
| `test/06-chat.spec.ts` | First chat-flow E2E spec; documented gap (ChatResponse field-shape mismatch). |
| `test/07-sse-reconnect.spec.ts` | First spec that exercises browser SSE retry logic; no Vitest analog (jsdom doesn't simulate `EventSource` retry). |

**Planner guidance for these files:** Follow RESEARCH.md drafts as the primary source of truth. The in-repo selector inventory (data-testid + aria-label + role) is the secondary source. CLAUDE.md project rules (no emojis, latest APIs, simple/incremental) are the cross-cutting binding rules.

---

## Metadata

**Analog search scope:** repo root, `Dockerfile`, `.dockerignore`, `.gitignore`, `scripts/`, `frontend/`, `frontend/src/components/**/*.tsx`, `frontend/src/components/**/*.test.tsx`, `frontend/vitest.config.mts`, `frontend/vitest.setup.ts`, `frontend/package.json`, `backend/app/chat/`, `.planning/phases/09-dockerization-packaging/09-PATTERNS.md` (style precedent).

**Files scanned (read for constraint extraction):**
- `.planning/phases/10-e2e-validation/10-CONTEXT.md` (decisions D-01..D-13, scope boundaries)
- `.planning/phases/10-e2e-validation/10-RESEARCH.md` (1111 lines — pinned versions, full compose YAML draft, full playwright.config.ts draft, per-spec outlines, SSE reconnect pattern, test-id inventory, gitignore additions, pitfalls)
- `Dockerfile` (container layout, entrypoint, healthcheck-absence, STOPSIGNAL, build-arg shape for compose `build:`)
- `.dockerignore` (confirms `test/` already excluded from production image)
- `.gitignore` (existing structure, section-comment style)
- `scripts/start_mac.sh` (canonical `docker run` arg set; the production-side baseline that the compose `app` service mirrors with one delta)
- `frontend/vitest.config.mts` (config-file shape analog for `playwright.config.ts`)
- `frontend/vitest.setup.ts` (deliberately NOT mirrored — jsdom-specific)
- `frontend/package.json` (Node project shape analog for `test/package.json`)
- `frontend/src/components/terminal/Header.tsx` (header structure for 01-fresh-start, 03-buy, 04-sell)
- `frontend/src/components/terminal/ConnectionDot.tsx` (aria-label SSE status for 01-fresh-start, 07-sse-reconnect)
- `frontend/src/components/terminal/TradeBar.tsx` (label-driven inputs for 03-buy, 04-sell)
- `frontend/src/components/terminal/TradeBar.test.tsx` (Vitest analog → translation pattern)
- `frontend/src/components/terminal/WatchlistRow.tsx` + `PositionRow.tsx` (aria-label="Select X" pattern)
- `frontend/src/components/chat/ChatInput.tsx` + `ChatHeader.tsx` (aria-label patterns for 06-chat)
- `frontend/src/components/chat/ChatInput.test.tsx` (Vitest analog → translation pattern)
- `frontend/src/components/chat/ChatThread.tsx` + `ActionCard.tsx` + `ActionCardList.tsx` + `ChatMessage.tsx` (data-testid inventory)
- `frontend/src/components/chat/ActionCardList.test.tsx` (data-testid query pattern)
- `frontend/src/components/portfolio/Heatmap.tsx` + `PnLChart.tsx` (data-testid surfaces for 05-portfolio-viz)
- `frontend/src/components/portfolio/Heatmap.test.tsx` + `PnLChart.test.tsx` (Vitest analog → translation pattern)
- `frontend/src/components/skeleton/SkeletonBlock.tsx` (data-testid placement pattern)
- `.planning/phases/09-dockerization-packaging/09-PATTERNS.md` (greenfield-with-constraint-inventory style precedent)
- Repo root `ls -la` (verified absence of `test/` directory)

**Pattern extraction date:** 2026-04-27

**Files NOT scanned (out of scope for Phase 10 patterns):**
- `backend/app/portfolio/`, `backend/app/watchlist/`, `backend/app/market/`, `backend/app/chat/` source — Phase 10 only cares that the existing API endpoints respond as documented in PLAN.md §8 against the running container. The internal implementation is Phase 3/4/5 contract.
- `frontend/src/lib/`, `frontend/src/app/` — Phase 10 only cares that the rendered DOM exposes the documented selectors. The React Query / Zustand internals are Phase 6/7/8 contract.
- `backend/tests/`, `frontend/src/**/*.test.tsx` — beyond the selector-translation analogs already extracted; the test bodies themselves are jsdom-coupled.
