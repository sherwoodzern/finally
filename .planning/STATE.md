---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: "Phase 8 — Wave 3 part 1 complete (08-06 chat primitives + ChatDrawer SHELL + 8 tests landed); 08-07 (ChatThread + ChatInput + Terminal mount) and Wave 4 (08-08 polish + build gate) still outstanding"
last_updated: "2026-04-26T12:30:00.000Z"
last_activity: 2026-04-26
progress:
  total_phases: 10
  completed_phases: 7
  total_plans: 33
  completed_plans: 31
  percent: 94
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-19)

**Core value:** One Docker command opens a Bloomberg-style terminal where prices stream live, trades execute instantly, and an AI copilot can analyze the portfolio and execute trades on the user's behalf.
**Current focus:** Phase 8 — Portfolio Visualization & Chat UI

## Current Position

Phase: 8
Plan: 08-06 complete; 08-07 (ChatThread + ChatInput + Terminal mount) and Wave 4 (08-08) still outstanding
Status: Phase 8 executing — 6 of 8 plans complete (08-06 merged: 101 vitest green = 93 prior + 8 new chat primitives)
Last activity: 2026-04-26

Progress: [######    ] 75% of Phase 08 (6 of 8 plans complete; 08-07 next)

## Performance Metrics

**Velocity:**

- Total plans completed: 10
- Average duration: 2.5min
- Total execution time: 0.08 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 (App Shell) | 2 | 5min | 2.5min |
| 7 | 8 | - | - |

**Recent Trend:**

- Last 5 plans: 01-01 (3min), 01-02 (2min)
- Trend: Stable (fine-granularity single-task plans).

*Updated after each plan completion*
| Phase 01 P03 | 60min | 3 tasks | 6 files |
| Phase 03 P01 | 4m 9s | 4 tasks | 4 files |
| Phase 03 P02 | 7m 6s | 4 tasks | 8 files |
| Phase 03 P03 | 7m 9s | 4 tasks | 10 files |
| Phase 04 P01 | 4m 14s | 3 tasks | 9 files |
| Phase 04 P02 | 6m 22s | 4 tasks | 8 files |
| Phase 06 P01 | 1h 5m 15s | 3 tasks | 17 files |
| Phase 06 P02 | 15m 28s | 4 tasks | 5 files |
| Phase 06 P03 | ~45m (incl. post-checkpoint finalize) | 5 tasks (5 pre-checkpoint commits + user auto-approve) | 5 files |
| Phase 08 P03 | ~10m | 2 tasks | 4 files |
| Phase 08 P04 | ~14m 36s | 2 tasks | 3 files |
| Phase 08 P05 | ~12m | 3 tasks | 4 files |
| Phase 08 P06 | ~13m | 3 tasks | 9 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Adopt `planning/PLAN.md` wholesale as v1 scope — all 40 Active requirements mapped to 10 phases.
- Market-data subsystem (MARKET-01..06) treated as Validated and inherited — not planned.
- Granularity is "fine" (10 phases; 3–6 requirements each); workflow flags enabled: research, plan_check, verifier, nyquist_validation, ui_phase, ai_integration_phase.
- D-02 (Plan 01-01): PriceCache is constructed inside the lifespan and attached to `app.state` — no module-level singletons.
- D-04 (Plan 01-01): SSE router `create_stream_router(cache)` is mounted during lifespan startup (before `yield`) so `/api/stream/prices` is live for the app's lifetime.
- Plan 01-01: python-dotenv chosen over pydantic-settings / manual `os.environ` — smallest dependency that satisfies APP-03 and the "missing values must not crash startup" constraint.
- Plan 01-01: `.env` loading happens in Plan 02's `main.py` BEFORE the app is constructed — not in the lifespan, so the factory sees env vars at construction time.
- Plan 01-01: Missing `OPENROUTER_API_KEY` logs a single warning but does NOT raise; Phase 5 will fail loud when `/api/chat` is hit.
- D-01 (Plan 01-02): Shell split across `backend/app/main.py` + `backend/app/lifespan.py` — no `config.py` (premature for three env vars).
- D-03 (Plan 01-02): No `if __name__ == "__main__":` block in `main.py`. Canonical run is `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`; the same line becomes Phase 9's Docker `CMD`.
- D-04 (Plan 01-02): `/api/health` defined inline in `main.py` returning `{"status": "ok"}`; SSE router is mounted by the lifespan, NOT by `main.py`.
- Plan 01-02: `load_dotenv()` runs at line 16 of `main.py` BEFORE `app = FastAPI(lifespan=lifespan)` at line 20 — load order is load-bearing (factory reads `MASSIVE_API_KEY` at lifespan entry).
- Plan 01-02: Health endpoint kept trivial (no `"source"` enrichment) because source is attached to `app.state` AFTER construction; ops visibility is a deferred idea.
- [Phase ?]: D-05 (01-03): SSE tests use a real in-process uvicorn server (not ASGITransport) — httpx ASGITransport buffers the full ASGI response and cannot drain infinite SSE generators.
- [Phase ?]: D-06 (01-03): create_stream_router builds a fresh APIRouter per call — pre-existing module-level router accumulated duplicate /prices routes across factory calls (Rule 1 auto-fix).
- [Phase ?]: 01-03: httpx and asgi-lifespan declared in [project.optional-dependencies].dev (not PEP 735 [dependency-groups]) to match uv sync --extra dev.
- [Phase ?]: 01-03: Fresh FastAPI(lifespan=lifespan) per test (via _build_app helper) — avoids shared state on module-level app.main.app across tests.
- [Phase 03]: 03-01: register_tick_observer declared as zero-arg Callable on MarketDataSource ABC; per-callback nested try/except + logger.exception in Simulator._run_loop and Massive._poll_once isolates broken observers from the tick/poll loop (D-04, D-08)
- [Phase 03]: 03-02: Portfolio service is pure functions (conn + cache + business args) with zero FastAPI imports — keeps service.py easy to unit-test and lets routes in 03-03 thin-wrap it (D-02)
- [Phase 03]: 03-02: Domain exception hierarchy rooted at TradeValidationError with `code: str` class attributes (`insufficient_cash`, `insufficient_shares`, `unknown_ticker`, `price_unavailable`) — routes in 03-03 map these 1:1 to 400-level responses (D-09)
- [Phase 03]: 03-02: execute_trade uses validate-then-write with a single conn.commit() at the end — any raise leaves zero DB writes, enforced by the 6-test validation suite asserting row-count invariants (D-12)
- [Phase 03]: 03-02: Positions with `abs(new_qty) < 1e-9` are DELETEd rather than stored as zero-quantity rows, preserving the "no position" invariant for both get_portfolio and future trade math (D-15)
- [Phase 03]: 03-02: Buy updates avg_cost as weighted-average `(old_qty*old_avg + new_qty*price)/(old_qty+new_qty)`; sell leaves avg_cost unchanged — realized P&L is a reporting concern, not a position-row concern (D-16)
- [Phase 03]: 03-02: make_snapshot_observer(state) returns a zero-arg closure checking `time.monotonic() - state.last_snapshot_at >= 60.0`; observer is registered in 03-03's lifespan, keeping the observer pattern decoupled from FastAPI itself (D-05, D-06, D-07)
- [Phase 03]: 03-03: create_portfolio_router(db, cache) is a factory-closure APIRouter mirroring create_stream_router — fresh router per call, no module-level state, prefix="/api/portfolio"; TradeValidationError subclasses translate 1:1 to HTTPException(400, detail={error: code, message: str(exc)}) at a single catch site (D-03, D-09, D-10)
- [Phase 03]: 03-03: Route-level post-trade clock reset (`request.app.state.last_snapshot_at = time.monotonic()`) keeps service.execute_trade FastAPI-agnostic; the observer only double-fires if a trade and a 60s-natural-tick collide within the same moment, which is now impossible (D-07)
- [Phase 03]: 03-03: Boot-time initial snapshot — make_snapshot_observer special-cases `last_snapshot_at == 0.0` so the first observer tick writes a snapshot unconditionally; Plan 02's pure 60s gate was tightened to `!= 0.0 and delta < 60` (Rule 2 fix, assumption A2 in 03-RESEARCH.md)
- [Phase 03]: 03-03: Integration test harness = `asgi_lifespan.LifespanManager` + `httpx.ASGITransport(app=app)` + `async with httpx.AsyncClient(...)` with a fresh `FastAPI(lifespan=lifespan)` per test and `patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True)` — established as the canonical pattern for all remaining API phases
- [Phase 04]: 04-01: Watchlist service mirrors portfolio — pure functions on `(conn, cache, *args)` with zero FastAPI imports so Phase 5 chat auto-exec can import `add_ticker`/`remove_ticker` directly (D-02)
- [Phase 04]: 04-01: `normalize_ticker(value)` is a module-level helper shared by Pydantic `WatchlistAddRequest`'s `field_validator(mode="before")` and the future Plan 04-02 `DELETE /{ticker}` path-param pre-check — regex `^[A-Z][A-Z0-9.]{0,9}$`, service trusts its input (D-04)
- [Phase 04]: 04-01: Idempotent mutations return a status-literal discriminator (`AddResult(status="added"|"exists")`, `RemoveResult(status="removed"|"not_present")`) instead of raising — 04-02 translates all four to HTTP 200 with `WatchlistMutationResponse`, never 409/404 (D-06)
- [Phase 04]: 04-01: `add_ticker` uses `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING` + `cursor.rowcount` branching (one query, atomic, race-free); `remove_ticker` uses `DELETE` + `cursor.rowcount` — commit only when rowcount==1 (D-09)
- [Phase 04]: 04-01: `get_watchlist` orders `ORDER BY added_at ASC, ticker ASC` (same as `get_watchlist_tickers`) and falls back to `None` on every price field when the cache has no tick yet — never 0, never omitted (D-05, D-08)
- [Phase 04]: 04-02: create_watchlist_router(db, cache, source) factory mirrors create_portfolio_router; mounted natively in lifespan BEFORE `yield` (line 68, `# D-13`) so `/api/watchlist` + `/api/watchlist/{ticker}` are in app.router.routes the moment LifespanManager.__aenter__ returns — no shim, no post-startup registration
- [Phase 04]: 04-02: DB-first-then-source choreography with try/except around `await source.{add,remove}_ticker` only; post-commit source failure logs WARNING with `exc_info=True` and still returns 200 (D-11). DB row-count arithmetic asserted strictly as `== before + 1` / `== before - 1`, not `>=`
- [Phase 04]: 04-02: Idempotent mutation responses always 200 with `status="added"/"exists"/"removed"/"not_present"` (SC#4); never 409/404. Uniform discriminator lets Phase 5 LLM handler branch without HTTP-code sniffing (D-06)
- [Phase 04]: 04-02: Module-scoped `app_with_lifespan` + `client` fixtures with `@pytest_asyncio.fixture(loop_scope="module", scope="module")` + `pytestmark = pytest.mark.asyncio(loop_scope="module")` + module-scoped `event_loop_policy` override in each test file — required by pytest-asyncio 1.x for module-scoped async fixtures. 21 integration tests across 3 files, exactly 1 SimulatorDataSource start per file (runtime <1s per file, well under 30s VALIDATION.md budget)
- [Phase 06]: 06-01: create-next-app scaffold with `--import-alias "@/*"` (D-01's `--no-import-alias=false` is invalid CLI syntax per RESEARCH G6). Next.js 16.2.4, Tailwind 4.2.4, React 19.2.4, TypeScript 5.9.3, Zustand 5.0.12, Vitest 4.1.5 landed. Scaffolded `frontend/CLAUDE.md` + `frontend/AGENTS.md` deleted (G11); repo-root CLAUDE.md is authoritative.
- [Phase 06]: 06-01: Tailwind v4 CSS-first @theme block in `src/app/globals.css` replaces the v3 `tailwind.config.ts` pattern from CONTEXT.md D-09 (RESEARCH G1 override). No `tailwind.config.ts` file needed in Phase 06. `@tailwindcss/postcss` in postcss.config.mjs (not v3 `tailwindcss` plugin).
- [Phase 06]: 06-01: Tailwind v4 tree-shakes `@theme` tokens without utility references — Phase 7-reserved tokens (accent-purple, surface-alt, border-muted, up, down, foreground-muted) redeclared in a plain `:root` block so the compiled CSS bundle always contains all four brand hex values required by the Wave 1 build gate (#0d1117, #ecad0a, #209dd7, #753991). `@theme` block still drives utility generation when Phase 7 adds `text-accent-purple` etc.
- [Phase 06]: 06-01: `next.config.mjs` (not `.ts`) with dev-only `async rewrites()` guarded by `NODE_ENV === 'development'`; stream rewrite `/api/stream/:path*` precedes generic `/api/:path*` for correct path-matching precedence. Production export has an empty rewrites array — the benign `rewrites + output: 'export'` warning is expected per RESEARCH G2.
- [Phase 06]: 06-01: Turbopack 16 emits CSS under `out/_next/static/chunks/*.css`, not `out/_next/static/css/*.css`. Plans 06-02/06-03 verify blocks should use the `chunks/*.css` path.
- [Phase 06]: 06-02: Zustand store is the single source of truth for live ticker state — `prices: Record<string, Tick>`, `status: ConnectionStatus`, `lastEventAt: number | null`, methods `connect/disconnect/ingest/reset`. `session_start_price` is frozen client-side on first-seen (D-14) via `prior?.session_start_price ?? raw.price`. Single `es: EventSource | null` module-level singleton with D-15 idempotent guard `if (es && es.readyState !== 2) return` for StrictMode safety. Named exports only: `usePriceStore`, `__setEventSource`, `selectTick`, `selectConnectionStatus`.
- [Phase 06]: 06-02: `PriceStreamProvider` is the React-mounted lifecycle owner — `'use client'`, `useEffect(() => { connect(); return () => disconnect(); }, [])` with empty deps. Placed outermost in `layout.tsx` so Plan 06-03 `/debug` page inherits the live EventSource without remounting. Conceptual analog of backend `SimulatorDataSource.start/stop`.
- [Phase 06]: 06-02: Repo-root `.gitignore` Python template's `lib/` line (at line 17, next to `build/` / `dist/` / `eggs/`) was silently ignoring `frontend/src/lib/` — Rule 3 auto-fix added `!frontend/src/lib/` and `!frontend/src/lib/**` negations so the Phase 06 contract directory tracks. Does not alter Python build-dir exclusion semantics.
- [Phase 06]: 06-02: Narrow try/catch at JSON.parse+ingest boundary only (D-19), `console.warn('sse parse failed', err, event.data)` with structured args (no template-literal interpolation, matching backend `%`-style logging pattern). No rethrow — EventSource stays alive after malformed frames and the browser's built-in `retry: 1000` auto-reconnect handles network drops.
- [Phase 06]: 06-03: Vitest 4.1.5 `.mts` config (jsdom env + plugin-react + tsconfig-paths + setupFiles) + 1-line `vitest.setup.ts` importing `@testing-library/jest-dom/vitest`. Handwritten `MockEventSource` class + `__setEventSource` DI is the test pattern — no global EventSource stub, no third-party `eventsourcemock`. 8 `it()` blocks mirror the Requirement -> Test Coverage table; full suite runs in 380ms (well under 5s Nyquist budget).
- [Phase 06]: 06-03: Rule 1 auto-fix — `MockEventSource.readyState` widened from the RESEARCH.md literal-union `0 | 1 | 2` to plain `number` to satisfy Next.js 16 strict tsc; the emit helpers mutate readyState via the static constants and the literal-union type rejected the assignment. One-line fix, zero behavioral change. RESEARCH.md section 13 template should be updated to `number` for future plans derived from it.
- [Phase 06]: 06-03: `/debug` App Router page uses `'use client'` + three Zustand selector subscriptions (prices / status / lastEventAt). UTC `HH:MM:SS.sss` formatter for backend Unix-seconds timestamp; ISO formatter for epoch-ms `lastEventAt`. No `dangerouslySetInnerHTML`, no interactions (UI-SPEC section 6). `/debug/index.html` lands in `frontend/out/` via `trailingSlash: true`.
- [Phase 06]: 06-03: Task 5 human-verify checkpoint resolved via user auto-approve under `/gsd-execute-phase --auto --no-transition`. All 4 ROADMAP Phase 6 success criteria have automated coverage (SC#1 CSS greps, SC#2 build gate, SC#3 MockEventSource idempotent + selector tests, SC#4 ingest against the RawPayload shape from backend/app/market/models.py:39-49). Live-wire browser check deferred — any discrepancy routed via `/gsd-plan-phase 06 --gaps`.
- [Phase 08]: 08-03: Heatmap.tsx exposes `buildTreeData(positions, ticks)` (pure data transform) and `handleHeatmapCellClick(node)` (store dispatcher) as named exports so unit tests assert directly against the data math + click semantics — Recharts SVG geometry is intentionally NOT exercised in jsdom. Treemap `onClick` wires straight to `handleHeatmapCellClick`, so the test code path is the production code path. Plans 08-04..08 should follow the same pure-function-extraction pattern; no `vi.mock('recharts')` was needed.
- [Phase 08]: 08-03: Rule 1 auto-fix — Heatmap's per-render selector returning a fresh `Record<string, number | undefined>` failed Zustand v5 + React 19's identity check and threw "Maximum update depth exceeded". Wrapped with `useShallow` from `zustand/react/shallow`. ALL future Phase 8 selectors that synthesize an object/array literal must use `useShallow`. Watch for the same trap in `PnLChart`, `ChatThread`, and `ActionCardList`.
- [Phase 08]: 08-03: Recharts 3.x `<Treemap>` props differ from the CONTEXT.md reference snippet (taken from a 2.x example): `strokeWidth` is not a valid Treemap prop, only `stroke`. `data` requires its element type to extend `TreemapDataType` (`{ [key: string]: any }`), so `TreeDatum` carries an explicit `[key: string]: string | number | boolean` index signature.
- [Phase 08]: 08-04: PnLChart uses Recharts `<LineChart>` over all `/api/portfolio/history` snapshots. Stroke = `var(--color-up)` when last `total_value >= 10000` else `var(--color-down)` (D-06, literal CSS-var strings flow into the `stroke=` SVG attribute — no Tailwind interpolation possible). `<ReferenceLine y={10000} strokeDasharray="4 4" strokeOpacity={0.4}>` is the dotted $10k anchor (D-05). Header summary template: `{formatMoney(total)} ({formatSignedMoney(delta)} vs $10k)`.
- [Phase 08]: 08-04: PnLTooltip is typed with a small local `PnLTooltipProps` interface (`active?: boolean; payload?: Array<{ payload?: { recorded_at: string; total_value: number } }>`) NOT Recharts' `TooltipContentProps<TValue, TName>`. RESEARCH.md flags the rename from `TooltipProps` (2.x) to `TooltipContentProps` (3.x); we deliberately stay on a local interface to keep the tooltip portable across 3.x patch versions. The runtime shape (`active`, `payload[].payload`) is stable and a 4-prop interface keeps the import surface minimal.
- [Phase 08]: 08-04: Rule 3 auto-fix — `PnLChart.test.tsx` includes a file-local `vi.mock('recharts', ...)` that overrides only `ResponsiveContainer` to a fixed-800x600 cloneElement shim. Without it, the global `ResizeObserver` stub from `vitest.setup.ts` lets the constructor succeed but never fires the callback, so `<ResponsiveContainer>` measures the parent at -1×-1 and Recharts skips rendering all `<path>` and `<line>` elements (Recharts logs *"The width(-1) and height(-1) of chart should be greater than 0"*). The mock keeps every other Recharts component real via `vi.importActual`. This is the standard escape hatch documented in 08-RESEARCH.md §Common Pitfall 5 and the recommended pattern for any future Phase 8 plan that needs to assert against rendered Recharts SVG.
- [Phase 08]: 08-05: TabBar dispatches `setSelectedTab` via `usePriceStore.getState().setSelectedTab(t.id)` rather than pulling the action through the selector subscription — matches the existing `setSelectedTicker` pattern in `PositionRow.tsx` (Phase 7). Avoids unnecessary re-renders from action-identity churn under React 19 / Zustand 5. Use `aria-pressed` (toggle-button semantic), NOT `aria-current="page"` (route semantic): tabs are toggle buttons over store state, not page navigation.
- [Phase 08]: 08-05: Terminal.tsx restructure leaves a `data-testid="chat-drawer-slot"` `<aside>` placeholder rather than mounting `<ChatDrawer />` preemptively. The placeholder uses `w-12 bg-surface-alt border-l border-border-muted flex flex-col` matching UI-SPEC §5.1's "drawer collapsed" width contract, so the visual layout already budgets for the drawer's eventual presence. Plan 06/07 will swap the entire `<aside>` for `<ChatDrawer />` (whose own root is also `<aside ...>`) and the outer `flex flex-row` wrapper plus workspace `flex-1` sibling stay untouched. This isolates 08-05's surface area (FE-05/06 tab switching) from 08-06/07's chat surface (FE-09).
- [Phase 08]: 08-06: ChatDrawer is intentionally a SHELL with `children?: ReactNode` rather than internally importing `<ChatThread />`. Plan 07 will mount `<ChatDrawer><ChatThread /></ChatDrawer>` inside Terminal.tsx, replacing the chat-drawer-slot placeholder. Decoupling lets the drawer ship and test independently of its eventual occupant — a children-slot pattern future drawer-style shells can reuse.
- [Phase 08]: 08-06: ChatMessage renders `{message.content}` as a JSX text node only (whitespace-pre-wrap preserves newlines). No `dangerouslySetInnerHTML`, no markdown→HTML conversion. Mitigates threat T-08-12 at the `/api/chat` → DOM trust boundary. `grep -r "dangerouslySetInnerHTML" frontend/src/components/chat/` returns 0. Plan 07 must add the XSS-payload assertion test (window.__pwned remains undefined for `<script>` injection in assistant content) per VALIDATION.md row.
- [Phase 08]: 08-06: ActionCard pulse is component-local: `useState(initial)` + `useEffect(() => setTimeout(() => setPulseClass(''), 800))` — clears after 800ms. Different lifetime semantics from the price-store `tradeFlash` slice (per-card mount vs. per-ticker debounced); not unified. STATUS_STYLE collapses `executed/added/removed` into one green visual treatment, `failed` into red, `exists/not_present` into muted gray (3 visual buckets across 6 statuses, per UI-SPEC §5.7).
- [Phase 08]: 08-06: ERROR_COPY in ActionCard reuses TradeBar.tsx ERROR_TEXT verbatim for 4 overlapping codes (`insufficient_cash`, `insufficient_shares`, `unknown_ticker`, `price_unavailable`) and adds 2 Phase 5 codes (`invalid_ticker`, `internal_error`) with the same DEFAULT_ERROR fallback. Single source of truth for trade-error wording — keep these in sync if either map is edited.
- [Phase 08]: 08-06: Test gotcha — `container.querySelectorAll('[data-testid^="action-card-"]')` matches BOTH the list wrapper (`data-testid="action-card-list"`) and the per-card testids (`data-testid="action-card-{status}"`). Filter results with `.filter((el) => el.dataset.testid !== 'action-card-list')` to exercise only the cards. Apply this pattern whenever a parent and children share a testid prefix.

### Pending Todos

None yet.

### Blockers/Concerns

From codebase analysis (`.planning/codebase/CONCERNS.md`) — carry into Phase 1 planning:

- `PriceCache` uses `threading.Lock` because `MassiveDataSource` writes via `asyncio.to_thread`. Must not be "simplified" to `asyncio.Lock` in the app-shell wiring.
- SSE generator polls at 500 ms and emits only on cache version change — no heartbeat. Watch for proxy-idle timeouts during demo.
- Daily-change baseline is session-relative; `session_start_price` must not be persisted to SQLite.
- Default seed tickers are duplicated across `seed_prices.py` and `market_data_demo.py`; Phase 2 DB seed must pick a single source of truth.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-26
Stopped at: Phase 8 — Plan 08-06 complete. Six chat primitives (ThinkingBubble, ChatHeader, ChatMessage, ActionCard, ActionCardList, ChatDrawer SHELL) + 8 Vitest tests landed sequentially on `finally-gsd` (commits `d56b701` feat:5-primitives, `54e41e6` feat:drawer-shell, `f0576b4` test:8-tests). Full suite 101/101 vitest (16 files; +3 test files, +8 tests over 08-05's 93). T-08-12 XSS mitigation in place: 0 dangerouslySetInnerHTML in `frontend/src/components/chat/`. Plan 08-07 next: ChatThread + ChatInput orchestration, Terminal.tsx mount of `<ChatDrawer><ChatThread /></ChatDrawer>` replacing the slot placeholder, plus the XSS-payload assertion test (window.__pwned). Wave 4: 08-08 (FE-11 polish + final build gate).

Resume file: `.planning/phases/08-portfolio-visualization-chat-ui/08-07-PLAN.md`
Next action: execute 08-07. Compose `<ChatThread />` against the freshly-landed primitives (ChatMessage + ThinkingBubble + ActionCardList) and create `<ChatInput />` mirroring TradeBar's form/onSuccess pattern. Replace the `<aside data-testid="chat-drawer-slot">` at lines 44-48 of `frontend/src/components/terminal/Terminal.tsx` with `<ChatDrawer><ChatThread /><ChatInput /></ChatDrawer>` (the drawer's root is itself an `<aside>`). Apply the `useShallow` rule (08-03) to any new selector that synthesizes an object literal. ActionCard's pulse prop (08-06) is the seam for D-12 fresh-card animation: ChatThread must pass `pulseActions={true}` only on locally-appended fresh assistant messages, not on history-query results. Add the XSS unit test asserting `window.__pwned` stays undefined for `<script>` payloads in `message.content` (Plan 07 must close the T-08-12 verification loop).
