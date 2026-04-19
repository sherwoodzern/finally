# Phase 1: App Shell & Config - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Mount a FastAPI application, wire the shared `PriceCache`, start a market data
source selected from `.env`, expose `/api/stream/prices` via the existing SSE
router, and expose a minimal `/api/health` — such that a real browser's
`EventSource` receives live price ticks on first connect.

**In scope:** FastAPI app instance, `lifespan` startup/shutdown, PriceCache
wiring, market-data source start/stop, SSE router mount, `/api/health`, `.env`
loading for the three project env vars.

**Out of scope (belongs to later phases):**
- SQLite schema / lazy init / seed data → Phase 2
- Static frontend mounting → Phase 8
- Portfolio / watchlist / chat endpoints → Phases 3–5
- Docker image and start/stop scripts → Phase 9

</domain>

<decisions>
## Implementation Decisions

### Module & Entrypoint Layout

- **D-01:** Split the shell across two files under `backend/app/`:
  - `main.py` — builds the FastAPI `app`, mounts routers, defines `/api/health`
    inline, wires the `lifespan` context manager.
  - `lifespan.py` — owns startup/shutdown: constructs the `PriceCache`, calls
    `create_market_data_source(cache)`, starts it with the initial ticker set,
    stops it cleanly on shutdown.
  Rejected: single-file layout (too cramped as later phases pile in) and
  three-file split with dedicated `config.py` (premature for 3 requirements).

- **D-02:** `PriceCache` is instantiated inside the `lifespan` context manager
  and attached to `app.state.price_cache`. Data source is started in lifespan
  and `await`-stopped on shutdown. No module-level singletons — stays test-
  friendly and matches the factory-closure pattern already used by
  `create_stream_router`.

- **D-03:** Uvicorn is invoked via CLI only:
  `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`.
  No `__main__` block in `main.py`. The same command line becomes the Docker
  `CMD` in Phase 9 — one canonical invocation for local dev, tests, and prod.

- **D-04:** Routers are wired inline in `main.py`. The SSE router is attached
  during lifespan startup via `app.include_router(create_stream_router(cache))`.
  `/api/health` is defined as an inline `@app.get("/api/health")` in `main.py`
  returning `{"status": "ok"}`. No separate `health.py` module.

### Claude's Discretion

The user elected to defer the following to standard practice during
research/planning. Planner may pick the conventional answer without re-asking.

- **Config / `.env` loading.** Choice of loader (python-dotenv vs
  pydantic-settings vs manual `os.environ`) and where `.env` lives (repo root
  vs `backend/`). Hard constraints: (a) missing values must not crash startup,
  (b) `MASSIVE_API_KEY` presence must drive `create_market_data_source`
  selection correctly, (c) `OPENROUTER_API_KEY` and `LLM_MOCK` are read but
  unused in Phase 1 — Phase 5 consumes them.

- **Startup ticker set.** What `source.start(tickers)` receives before the DB
  exists. `SEED_PRICES.keys()` in `backend/app/market/seed_prices.py` is the
  natural single source of truth (already flagged as a drift risk in
  `.planning/codebase/CONCERNS.md`). Planner to wire it so Phase 2's DB-backed
  watchlist can swap in without code churn.

- **SSE end-to-end verification.** How to prove APP-04's "real browser
  `EventSource` receives ticks". Likely minimum: a pytest fixture using
  `httpx.AsyncClient` that asserts at least one `data:` frame arrives, plus a
  manual curl smoke documented in the backend README. Full Playwright browser
  E2E is Phase 10 and not required here.

- **Health endpoint shape.** Baseline is `{"status": "ok"}`. Planner may enrich
  with `"source": "simulator" | "massive"` if trivial.

- **Missing-env policy.** If `MASSIVE_API_KEY` is absent/empty → simulator
  (already implemented in `factory.py`). If `OPENROUTER_API_KEY` is absent →
  startup proceeds, log a single warning; Phase 5 will fail fast when the chat
  endpoint is hit.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification
- `planning/PLAN.md` §3 — Architecture overview (single container, FastAPI +
  static export + SSE)
- `planning/PLAN.md` §5 — Environment variables and behavior
- `planning/PLAN.md` §6 — Market data, shared price cache, SSE contract
- `planning/PLAN.md` §8 — API endpoints table (confirms `/api/health`,
  `/api/stream/prices` for this phase)

### Project planning
- `.planning/REQUIREMENTS.md` — APP-01, APP-03, APP-04 (the three requirements
  this phase delivers)
- `.planning/ROADMAP.md` — Phase 1 "Success Criteria" (all four criteria must
  evaluate TRUE)
- `.planning/PROJECT.md` — Constraints (backend tech stack, code-style rules)

### Codebase intel
- `.planning/codebase/ARCHITECTURE.md` — "Missing architectural pieces" table;
  "Entry Points" section (confirms no `app/main.py` exists today)
- `.planning/codebase/CONVENTIONS.md` — FastAPI idioms (factory routers, no
  globals), logging patterns (`%`-style, no f-strings)
- `.planning/codebase/CONCERNS.md` — Implementation gap table;
  §"Architectural risks" items 4 & 5 (SSE reconnection semantics, version-gated
  SSE with no heartbeat — acknowledged, not mitigated in Phase 1)
- `backend/CLAUDE.md` — Public `app.market` import surface

### Reusable code
- `backend/app/market/stream.py` — `create_stream_router(cache)`; note
  `request.is_disconnected()` + 500 ms sleep cleanup path and version-gated
  emissions
- `backend/app/market/factory.py` — `create_market_data_source(cache)` reads
  `MASSIVE_API_KEY` at construction time
- `backend/app/market/cache.py` — `PriceCache` API and thread-safety contract
- `backend/app/market/seed_prices.py` — `SEED_PRICES` dict (candidate single
  source of truth for the startup ticker set)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PriceCache`** — thread-safe, monotonic-version-counter-driven; built once
  in lifespan, attached to `app.state.price_cache`.
- **`create_market_data_source(cache)`** — factory selecting simulator vs
  Massive from `MASSIVE_API_KEY`. Called once in lifespan startup.
- **`create_stream_router(cache)`** — ready-to-mount SSE `APIRouter` factory.
  No changes needed — just `app.include_router(...)` it during startup.

### Established Patterns
- Factory-closure routers; no module-level globals for shared state.
- `from __future__ import annotations` at top of every module.
- `logger = logging.getLogger(__name__)`; `%`-style formatting — never
  f-strings in logging calls.
- Background tasks owned by the producer: single `asyncio.Task` created in
  `start()`, cancelled in `stop()`. Lifespan just calls those two methods.
- Narrow exception handling only where crossing boundaries (network, thread
  workers). Internal code trusts invariants.

### Integration Points
- `backend/app/__init__.py` is a one-line docstring stub — `main.py` and
  `lifespan.py` slot in alongside it.
- `app.state` carries shared objects; the existing `create_stream_router`
  closes over the cache, so passing `app.state.price_cache` into it is drift-
  free.
- The same `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` line will
  become Phase 9's Docker `CMD` and the body of the start scripts.

</code_context>

<specifics>
## Specific Ideas

- User elected the two-file split (`main.py` + `lifespan.py`) over single-file
  and three-file options — "short modules, split when they grow" fits the
  project's stated code-style rule.
- All three Recommended defaults accepted for cache lifetime, uvicorn entry,
  and router mount style.

</specifics>

<deferred>
## Deferred Ideas

- **`.env.example` committed at repo root.** Formally OPS-04 (Phase 9), but
  `README.md` already references it and local dev is broken without it (noted
  in `.planning/codebase/CONCERNS.md`). Planner may opportunistically include
  it in Phase 1 if trivial; otherwise Phase 9 covers it.
- **SSE heartbeat / keepalive frames.** Architectural risk #5 in
  `.planning/codebase/CONCERNS.md` — the stream goes silent when the cache
  version is unchanged, which can trip proxy idle timeouts. Out of scope for
  Phase 1 since the demo runs on localhost; revisit if cloud deploy ever
  becomes v1.
- **Source-type health signal.** Exposing `{"source": "simulator" | "massive"}`
  from `/api/health` could help ops visibility, but is tangential to the phase
  goal. Captured under Claude's Discretion above — planner decides.

</deferred>

---

*Phase: 01-app-shell-config*
*Context gathered: 2026-04-19*
