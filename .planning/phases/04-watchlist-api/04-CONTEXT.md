# Phase 4: Watchlist API - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the watchlist HTTP layer against the seeded SQLite database and wire
each mutation into the already-live `MarketDataSource`:
`GET /api/watchlist` (current rows joined with live prices from the in-memory
cache), `POST /api/watchlist` (persist a new ticker, then onboard it to the
market source on the next tick), `DELETE /api/watchlist/{ticker}` (remove the
row, stop tracking in the cache, drop it from subsequent SSE emissions).
Mutations that are no-ops return idempotent success responses — never 500s.

**In scope:**
- `app/watchlist/` sub-package mirroring `app/portfolio/` and `app/market/`:
  `routes.py`, `service.py`, `models.py`, `__init__.py` with explicit
  `__all__`.
- Pydantic v2 request/response models (`WatchlistAddRequest`,
  `WatchlistItem`, `WatchlistResponse`, `WatchlistMutationResponse`) with
  strict `extra="forbid"` on requests.
- Pure-function DB-only service layer on `sqlite3.Connection` reusable by
  Phase 5 chat auto-exec: `get_watchlist`, `add_ticker`, `remove_ticker`.
- Domain exceptions for the narrow set of edge cases the service can
  legitimately reject (invalid ticker shape after normalization — though
  Pydantic catches this at the edge, the service defence mirrors Phase 3
  Trade validation hygiene).
- Route-level orchestration of DB mutation **then** `source.add_ticker` /
  `source.remove_ticker` — keeps service sync and FastAPI-agnostic (Phase 3
  D-02).
- Lifespan wiring: `app.include_router(create_watchlist_router(conn, cache,
  source))` after the portfolio router (no new `app.state` fields; market
  source is already attached by Phase 1).

**Out of scope (belongs to later phases):**
- `/api/chat` and LLM auto-exec of watchlist_changes → Phase 5 (service
  reused; wiring lands there).
- Frontend watchlist panel, add/remove UI → Phase 7 (FE-03).
- Dockerfile, `.env.example` changes → Phase 9.
- Playwright E2E for watchlist add/remove → Phase 10 (TEST-04).
- Watchlist seed logic (Phase 2 already owns the 10-ticker seed in
  `app/db/seed.py`; Phase 4 does not re-seed).
- Refactoring `get_watchlist_tickers` out of `app/db/seed.py` — the lifespan
  call site from Phase 2 stays stable.

</domain>

<decisions>
## Implementation Decisions

### Module & Service Layout

- **D-01:** Watchlist code lives in `backend/app/watchlist/` sub-package
  mirroring `app/portfolio/` (Phase 3 D-01) and `app/db/` (Phase 2):
  - `routes.py` — FastAPI router factory
    `create_watchlist_router(db, cache, source)`, thin handlers that parse
    Pydantic bodies, call the service, orchestrate source mutations.
  - `service.py` — pure DB-only functions on `(sqlite3.Connection, ...)`:
    `get_watchlist(conn) -> list[WatchlistRow]`,
    `add_ticker(conn, ticker) -> AddResult`,
    `remove_ticker(conn, ticker) -> RemoveResult`.
    No FastAPI imports, no market-source imports — reusable from Phase 5.
  - `models.py` — Pydantic v2 `BaseModel`s for request/response schemas.
  - `__init__.py` — explicit `__all__` re-exporting the router factory,
    service functions, and response models (matches `app/portfolio/` and
    `app/market/` conventions).

- **D-02:** Service functions do NOT take `MarketDataSource`. The route
  orchestrates DB mutation first, then awaits `source.add_ticker` /
  `source.remove_ticker`. Rationale:
  (a) keeps service sync + FastAPI-agnostic (Phase 3 D-02 parity),
  (b) Phase 5 chat auto-exec already runs inside an async handler and can
      call the same service then await the source itself,
  (c) DB is the canonical set per PLAN.md §6 — the source is a cache to
      eventually-reconcile, not the source of truth.
  Rejected: service that awaits the source (forces async service,
  complicates Phase 5 reuse); background reconciler polling the DB
  (over-engineered for a single-user app).

- **D-03:** Pydantic v2 `BaseModel` for every request and response.
  `WatchlistAddRequest` uses `extra="forbid"` so typos like
  `{"Ticker": "AAPL"}` produce a 422 at the edge (Phase 3 D-03 parity).
  Response models use the default lenient config. FastAPI auto-generates
  OpenAPI from these.

### Ticker Normalization & Validation

- **D-04:** Ticker normalization happens at the Pydantic edge, not in the
  service. A `field_validator` on `WatchlistAddRequest.ticker` strips
  whitespace and uppercases the value, then enforces the regex
  `^[A-Z][A-Z0-9.]{0,9}$` (1-10 chars, must start with a letter, allows
  dots for symbols like `BRK.B`). On mismatch FastAPI returns 422 before
  the handler runs. The service trusts its input — no second regex check.
  Path parameter `{ticker}` on DELETE goes through a shared
  `normalize_ticker(value: str) -> str` helper that applies the same
  transform and raises `HTTPException(422)` on mismatch; handler calls it
  first, service trusts.

- **D-05:** No whitelist / "known ticker" check. PLAN.md §6 says the
  simulator onboards unknown tickers with a `SEED_PRICES.get(ticker, random
  50-300)` fallback, and `MassiveDataSource` polls whatever is in its
  ticker list and logs on per-ticker parse errors. Accepting any
  regex-valid ticker matches existing behavior and avoids a Phase 4
  whitelist that Phase 5's LLM would have to learn.

### Idempotency & Response Contract

- **D-06:** Mutation endpoints always return `200 OK` with a
  `WatchlistMutationResponse { ticker: str, status: Literal["added",
  "exists", "removed", "not_present"] }`. No 201, no 204. Rationale:
  success criterion #4 calls for "an idempotent no-op with a sensible
  response — not a 500"; a uniform 200 + explicit `status` discriminator
  lets the frontend and Phase 5 LLM both branch on `status` without
  inspecting HTTP codes.
  - `POST /api/watchlist` — `status="added"` when the row was inserted,
    `status="exists"` when the unique constraint on `(user_id, ticker)`
    already held (no second INSERT).
  - `DELETE /api/watchlist/{ticker}` — `status="removed"` when a row was
    deleted, `status="not_present"` when none existed.

- **D-07:** `GET /api/watchlist` returns
  `WatchlistResponse { items: list[WatchlistItem] }`. Each item:
  `{ticker: str, added_at: str, price: float | None, previous_price:
  float | None, change_percent: float | None, direction:
  Literal["up","down","flat"] | None, timestamp: float | None}`. Cache-
  derived fields fall back to `None` (not `0`, not an error) when
  `cache.get(ticker)` returns `None`. Same graceful-fallback rule as
  Phase 3 D-01 `/api/portfolio` (avg_cost fallback) — never a 500 just
  because the cache is cold.
  Rejected: `0.0` placeholders (lies to the frontend about a real price),
  omitting the field (forces frontend to branch on `"price" in item`).

- **D-08:** Ordering for `GET /api/watchlist` is `added_at ASC, ticker
  ASC` — the same order `get_watchlist_tickers` already uses in
  `backend/app/db/seed.py:69`. Seed rows share an `added_at`, so `ticker`
  is the stable tiebreaker; later manual adds sort after. Frontend can
  re-order as it likes.

### Mutation Ordering & Failure Modes

- **D-09:** Write order on `POST /api/watchlist`:
  1. Pydantic validates + normalizes the ticker (422 on bad shape).
  2. Service `add_ticker(conn, ticker)` tries INSERT; on a unique-
     constraint conflict it reports `status="exists"` without raising.
  3. If `status="added"`, the route awaits
     `source.add_ticker(ticker)` — idempotent on both implementations
     (`SimulatorDataSource.add_ticker` and `MassiveDataSource.add_ticker`
     are both early-return-on-present, per their existing code).
  4. Route returns `WatchlistMutationResponse`.
  If `status="exists"`, the route skips step 3 — the ticker is already
  in the source's active set (PLAN.md §6 invariant maintained).

- **D-10:** Write order on `DELETE /api/watchlist/{ticker}`:
  1. Normalize ticker (422 on bad shape — handler calls
     `normalize_ticker` helper).
  2. Service `remove_ticker(conn, ticker)` runs `DELETE ... RETURNING`
     (or a SELECT-then-DELETE) and reports `status="removed"` /
     `status="not_present"`.
  3. If `status="removed"`, the route awaits
     `source.remove_ticker(ticker)` — idempotent on both
     implementations; `SimulatorDataSource.remove_ticker` also calls
     `cache.remove(ticker)` (`massive_client.py:77`), so the cache
     purge is handled by the source, not by the route.
  4. Route returns `WatchlistMutationResponse`.

- **D-11:** No atomic DB+source rollback. If `source.add_ticker` were to
  raise after the DB INSERT committed (unlikely — both implementations
  catch their own errors), the next iteration of the tick/poll loop
  would still pick up the union of watchlist rows as the intended set.
  The DB is the reconciliation anchor, and the lifespan already reads
  `get_watchlist_tickers(conn)` on startup (`lifespan.py:57`) — an
  orphan DB row becomes an active ticker on the next restart at worst.
  Match the CONVENTIONS.md "narrow error handling at boundaries" style:
  the route logs an `exc_info=True` warning if an awaited source call
  raises after a successful commit, then returns the
  `WatchlistMutationResponse` as if it had succeeded (the DB state is
  consistent; the source will reconcile).

- **D-12:** DB uniqueness is enforced by the existing schema: `watchlist`
  already has `UNIQUE(user_id, ticker)` (PLAN.md §7, `app/db/schema.py`).
  The service leverages `INSERT ... ON CONFLICT(user_id, ticker) DO
  NOTHING` and inspects `cursor.rowcount` to distinguish added-vs-exists
  without a pre-SELECT. `DELETE` inspects `cursor.rowcount` to
  distinguish removed-vs-not_present. One query per mutation.

### Lifespan Integration

- **D-13:** `lifespan` mounts the watchlist router after the portfolio
  router (Phase 3 wiring at `backend/app/lifespan.py:66`):
  `app.include_router(create_watchlist_router(conn, cache, source))`.
  No new `app.state` fields — `market_source` is already attached by
  Phase 1 (`lifespan.py:62`). The tick-observer registration (Phase 3
  D-05) is untouched — watchlist mutations do not record portfolio
  snapshots.

### Claude's Discretion

Planner may pick the conventional answer without re-asking.

- **Exact SQL.** `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING`
  (SQLite ≥3.24, ships with Python 3.12's stdlib) is preferred for D-12,
  but the equivalent `INSERT OR IGNORE` + `cursor.rowcount` read is
  acceptable. Planner picks.

- **`RETURNING` clauses.** SQLite supports them since 3.35. If the
  planner wants `DELETE ... WHERE ... RETURNING id` for D-10 instead of
  `cursor.rowcount`, fine. Either shape is idempotent.

- **Row `id` generation on INSERT.** Match Phase 2 seed code (`str(uuid.uuid4())`
  from `app/db/seed.py:55`). `added_at` uses `datetime.now(UTC).isoformat()`
  matching `app/db/seed.py:37` and `app/portfolio/service.py` timestamp style.

- **DB helper refactor.** `get_watchlist_tickers(conn)` currently lives in
  `app/db/seed.py` and returns `list[str]`. Phase 4 needs richer rows
  (ticker + added_at). Planner may either:
  (a) add a new `get_watchlist(conn)` in `app/watchlist/service.py`
      returning `list[sqlite3.Row]`, leaving `get_watchlist_tickers`
      alone, or
  (b) add the helper there and have `get_watchlist_tickers` call it.
  Option (a) is simpler and keeps the Phase 2 lifespan signature stable.

- **Response-model field naming.** `direction` values `"up"/"down"/"flat"`
  match `PriceUpdate.direction` verbatim — no translation. `timestamp`
  vs `updated_at` for the cache timestamp — either works; pick one and
  stay consistent.

- **Handler ordering inside `routes.py`.** `POST` before `DELETE` before
  `GET` or any order — the router factory emits one `APIRouter` either
  way. Keep `prefix="/api/watchlist"` and `tags=["watchlist"]` on the
  APIRouter itself, not on each handler (Phase 3 parity).

- **Test fixtures.** Extend `backend/tests/conftest.py` the same way
  Phase 3 extended `_build_app` for a warm cache. A watchlist test
  fixture that starts a real `SimulatorDataSource` + one `await
  asyncio.sleep(0)` pass to warm the cache is expected; mocked-source
  fixtures are fine for testing mutation ordering without timing.

- **Idempotent-add log level.** `status="exists"` and
  `status="not_present"` log at `INFO` (they are routine); actual
  mutations log at `INFO` with ticker and user_id. Match `seed_defaults`
  log style in `app/db/seed.py:57`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification (the source of truth)
- `planning/PLAN.md` §6 — "The set of tickers tracked by the price cache
  is the union of all tickers in the watchlist table" + dynamic ticker
  lifecycle (idempotent add/remove, seed fallback for unknown tickers).
  Backs D-05, D-09, D-10, D-11.
- `planning/PLAN.md` §7 — `watchlist` schema: `id`, `user_id`, `ticker`,
  `added_at`, `UNIQUE(user_id, ticker)`. Already live in
  `backend/app/db/schema.py`. Backs D-12.
- `planning/PLAN.md` §8 — API endpoint table for `GET /api/watchlist`,
  `POST /api/watchlist`, `DELETE /api/watchlist/{ticker}` (including
  "returns current watchlist tickers with latest prices"). Backs D-07.
- `planning/PLAN.md` §9 — LLM structured-output schema for
  `watchlist_changes` (relevant because Phase 4 service is the reuse
  target for Phase 5 auto-exec of `{ticker, action: "add"|"remove"}`).

### Project planning
- `.planning/REQUIREMENTS.md` — WATCH-01, WATCH-02, WATCH-03 (the three
  requirements this phase delivers).
- `.planning/ROADMAP.md` — Phase 4 "Success Criteria" (all four must
  evaluate TRUE, especially #4 idempotent no-ops).
- `.planning/PROJECT.md` — Constraints: no over-engineering, no defensive
  programming, short modules, latest APIs, `%`-style logging, no emojis.
- `.planning/phases/01-app-shell-config/01-CONTEXT.md` — `app.state`
  pattern (D-02), factory-closure routers mounted in lifespan (D-04).
  Backs D-13.
- `.planning/phases/02-database-foundation/02-CONTEXT.md` — one
  long-lived `sqlite3.Connection` on `app.state.db` (D-01),
  `sqlite3.Row` row factory (D-02), manual commit (D-03). Backs D-12.
- `.planning/phases/03-portfolio-trading-api/03-CONTEXT.md` —
  sub-package mirror + pure-function service + pydantic v2 + factory
  router + error-contract shape (D-01 through D-03, D-10). Backs D-01,
  D-02, D-03, D-06.

### Codebase intel
- `.planning/codebase/CONVENTIONS.md` — module docstring, `from __future__
  import annotations`, `%`-style logging, narrow exception handling, no
  emojis, factory routers over globals.
- `.planning/codebase/ARCHITECTURE.md` — strategy pattern for market
  data, producer/consumer decoupling via PriceCache, dynamic ticker
  lifecycle.
- `.planning/codebase/STRUCTURE.md` — `app/market/`, `app/db/`,
  `app/portfolio/` sub-package layouts that Phase 4 mirrors.
- `.planning/codebase/CONCERNS.md` — any open architectural risks that
  touch watchlist mutation (default ticker source-of-truth was closed by
  Phase 2 D-04/D-05/D-06).

### Reusable code touched by Phase 4
- `backend/app/lifespan.py` — mount the watchlist router after the
  portfolio router; no other changes.
- `backend/app/main.py` — unchanged (router mount happens in lifespan,
  matching Phase 1 D-04).
- `backend/app/db/schema.py` — `watchlist` table already defined with
  `UNIQUE(user_id, ticker)`; no schema change needed.
- `backend/app/db/seed.py` — `get_watchlist_tickers(conn)` still used by
  the lifespan on startup; keep stable (D-14 Claude's Discretion).
- `backend/app/market/__init__.py` — re-exports `PriceCache`,
  `MarketDataSource`; watchlist router factory signature consumes both.
- `backend/app/market/interface.py` — `add_ticker` / `remove_ticker`
  contract (idempotent, async). Unchanged.
- `backend/app/market/simulator.py:244-257` — `SimulatorDataSource.add_ticker`
  seeds the cache immediately; `remove_ticker` calls `cache.remove`.
  Phase 4 relies on both behaviors (D-09, D-10).
- `backend/app/market/massive_client.py:68-78` — `MassiveDataSource.add_ticker`
  is early-return-on-present; `remove_ticker` calls `cache.remove`.
  Phase 4 relies on both behaviors (D-09, D-10).
- `backend/app/market/cache.py` — `cache.get(ticker)` returns
  `PriceUpdate | None`; `cache.remove(ticker)` is idempotent. Unchanged.
- `backend/app/portfolio/routes.py` — template for
  `app/watchlist/routes.py` factory signature and error-mapping style.
- `backend/app/portfolio/service.py` — template for
  `app/watchlist/service.py` pure-function shape.
- `backend/app/portfolio/models.py` — template for Pydantic v2 request
  and response models with `extra="forbid"`.
- `backend/tests/conftest.py` — `_build_app` + `db_path` fixtures used
  by Phase 3 extend cleanly; add a watchlist-flavored fixture if the
  planner wants mutation tests against a mocked source.
- `backend/CLAUDE.md` — extend "Public imports" after this phase lands:
  `from app.watchlist import create_watchlist_router, add_ticker,
  remove_ticker, get_watchlist`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`app.state.db`, `app.state.price_cache`, `app.state.market_source`** —
  attached in `backend/app/lifespan.py` by Phase 1/2/3. Phase 4 adds no
  new state fields.
- **`PriceCache.get(ticker) -> PriceUpdate | None`** and `cache.remove(ticker)` —
  exact shapes Phase 4 needs for the GET response and DELETE flow.
- **`MarketDataSource.add_ticker(ticker)` / `remove_ticker(ticker)`** —
  both concrete implementations are already idempotent and already call
  `cache.update` (on add, via simulator seeding) and `cache.remove` (on
  remove). Phase 4 just awaits them after a successful DB mutation.
- **`get_watchlist_tickers(conn) -> list[str]`** in `backend/app/db/seed.py:69` —
  already used by the lifespan; stays stable.
- **Pydantic v2 request/response models with `extra="forbid"`** —
  template in `backend/app/portfolio/models.py`.
- **Factory-closure routers** — `create_portfolio_router(db, cache)` in
  `backend/app/portfolio/routes.py` is the direct template.
- **Domain exception → HTTP 400 mapping pattern** — in
  `backend/app/portfolio/routes.py:44-48`.

### Established Patterns
- Factory-closure routers; no module-level router objects (Phase 1 D-04).
- One long-lived `sqlite3.Connection` with `check_same_thread=False` and
  `sqlite3.Row` rows — do NOT open per-request connections.
- Explicit `conn.commit()` after each write path (Phase 2 D-03).
- `%`-style logging
  (`logger.info("Watchlist: added %s for user %s", ticker, user_id)`) —
  never f-strings in log calls.
- Narrow exception handling only at boundaries; observers / background
  callbacks wrap in `try/except Exception` + `logger.exception`.
- Free pure functions on `sqlite3.Connection` in service modules
  (Phase 2, Phase 3 D-02).
- Short modules: `app/portfolio/service.py` is ~200 lines; Phase 4
  target is `app/watchlist/service.py` ≤80 lines.

### Integration Points
- `backend/app/lifespan.py:66` — add one line after the portfolio router
  mount: `app.include_router(create_watchlist_router(conn, cache, source))`.
- `backend/app/main.py` is untouched.
- `backend/app/market/interface.py` is untouched (Phase 3 already added
  `register_tick_observer`; Phase 4 does not touch the ABC).
- `backend/app/db/schema.py` is untouched — `watchlist` already has the
  columns and constraint needed.
- `backend/tests/conftest.py` — `_build_app()` helper extends cleanly.
  A `watchlist_fixture` that pre-warms the cache with AAPL (so the GET
  response can assert `price is not None` for a seeded ticker) is
  expected.

</code_context>

<specifics>
## Specific Ideas

All gray areas were auto-selected under `--auto` and resolved with the
recommended decisions above. The choices reflect continuity with Phase 1,
Phase 2, and especially Phase 3 patterns (sub-package mirror, pydantic v2
models, pure-function DB-only service, factory-closure router mounted in
lifespan). No novel architectural moves; no new dependencies.

- The "DB first, source second" ordering (D-09, D-10, D-11) preserves
  PLAN.md §6's invariant (`cache set = watchlist set`) without a
  two-phase commit — the DB is the reconciliation anchor, the market
  source is an eventually-consistent cache that re-reads on restart.
- The uniform 200 + `status` discriminator (D-06) makes the Phase 5 LLM
  auto-exec path trivial: no HTTP-code sniffing; the assistant sees
  `status: "exists"` and narrates accordingly.
- The service stays completely FastAPI-agnostic and async-free so the
  chat handler in Phase 5 can call `add_ticker(conn, t)` on the same
  connection without ceremony, then await the source itself.

</specifics>

<deferred>
## Deferred Ideas

- **Real-time delivery of watchlist changes to other clients.** Single-user
  localhost demo — no other clients. If v2 ever adds multi-user, the SSE
  stream could emit a `watchlist_changed` control event.
- **Ticker existence validation against an external universe (e.g., a
  static list of valid NYSE/NASDAQ symbols or a Massive API call).**
  Out of scope — PLAN.md §6 explicitly supports unknown-ticker
  onboarding via seed fallback. Revisit only if the Phase 5 LLM starts
  hallucinating exotic symbols.
- **Bulk mutation endpoints** (`POST /api/watchlist/bulk`, etc.). Phase 5
  auto-exec will call the existing single-ticker endpoint in a loop if
  the LLM proposes multiple `watchlist_changes[]`. If atomicity across
  a chat-turn's multiple changes becomes a requirement, revisit as part
  of Phase 5's CONCERNS-item-8 work.
- **Soft-delete / archive semantics.** `DELETE` is a hard delete
  matching PLAN.md §8. No undo, no `deleted_at` column.
- **Per-user watchlists.** Schema already supports it (`user_id`
  column). `AUTH-01` in v2 requirements.
- **Ticker rename / ticker change (e.g., FB → META).** Out of scope —
  v1 treats ticker symbols as opaque user input.
- **History of watchlist mutations.** No audit log. If needed later, a
  `watchlist_changes` table could be added alongside the existing
  `trades` append-only log.

</deferred>

---

*Phase: 04-watchlist-api*
*Context gathered: 2026-04-21*
