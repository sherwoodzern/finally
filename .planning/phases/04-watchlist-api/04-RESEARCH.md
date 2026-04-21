# Phase 4: Watchlist API - Research

**Researched:** 2026-04-21
**Domain:** FastAPI + sqlite3 + Pydantic v2 HTTP edge layer; idempotent mutation semantics; mirror of Phase 3 portfolio sub-package pattern
**Confidence:** HIGH

## Summary

Phase 4 stands up the `/api/watchlist` HTTP layer by mirroring Phase 3's `app/portfolio/` sub-package structure exactly: factory-closure router, pure-function DB-only service on a shared `sqlite3.Connection`, Pydantic v2 request/response models with `extra="forbid"`, and one mount line in `backend/app/lifespan.py`. Every piece of infrastructure the phase needs is already present in the codebase — the `watchlist` table with its `UNIQUE(user_id, ticker)` constraint (seeded by Phase 2), the idempotent `MarketDataSource.add_ticker` / `remove_ticker` contracts on both `SimulatorDataSource` and `MassiveDataSource`, the `PriceCache.get()` fallback-to-`None` semantics, and the `asgi_lifespan.LifespanManager + httpx.ASGITransport` test harness established in Phase 3 (`03-RESEARCH.md` canonical pattern).

The only novel design surface is the **idempotent mutation response contract**: a uniform `200 OK` with a `status: Literal["added","exists","removed","not_present"]` discriminator (CONTEXT D-06). Success criterion #4 ("idempotent no-op — NOT a 500") is satisfied by routing on `cursor.rowcount` from a single `INSERT ... ON CONFLICT DO NOTHING` (SQLite 3.24+, backend runs 3.50.4) or `DELETE` (with optional `RETURNING`). The service stays async-free and FastAPI-agnostic so the Phase 5 chat auto-exec can call `add_ticker(conn, t)` and `remove_ticker(conn, t)` directly, then await the source itself.

**Primary recommendation:** Clone the `app/portfolio/` shape file-for-file into `app/watchlist/`; use `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING` + `cursor.rowcount` for add and `DELETE ... WHERE ... RETURNING id` for remove; put ticker normalization in a single shared `normalize_ticker(value: str) -> str` helper in `models.py` that the Pydantic `field_validator` on `WatchlistAddRequest` and the DELETE path-param pre-check both call; log-and-continue on post-commit source failures (DB is the reconciliation anchor); mount the router with `app.include_router(create_watchlist_router(conn, cache, source))` after the portfolio mount at `backend/app/lifespan.py:66`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `backend/app/watchlist/` sub-package — `routes.py` (factory `create_watchlist_router(db, cache, source)`), `service.py` (pure DB-only functions), `models.py` (Pydantic v2 request/response schemas), `__init__.py` with explicit `__all__`. Mirrors `app/portfolio/` and `app/db/`.
- **D-02:** Service functions do NOT take `MarketDataSource`. Routes orchestrate DB mutation first, then await `source.add_ticker` / `source.remove_ticker`. Service stays sync + FastAPI-agnostic so Phase 5 chat auto-exec can reuse it.
- **D-03:** Pydantic v2 `BaseModel` for every request/response. `WatchlistAddRequest` uses `extra="forbid"`. Response models use default lenient config.
- **D-04:** Ticker normalization at the Pydantic edge. `field_validator` on `WatchlistAddRequest.ticker` strips whitespace, uppercases, enforces regex `^[A-Z][A-Z0-9.]{0,9}$`. DELETE path param goes through a shared `normalize_ticker(value: str) -> str` helper; bad shape → `HTTPException(422)`. Service trusts its input.
- **D-05:** No whitelist. Accept any regex-valid ticker. The simulator seeds unknown tickers via `SEED_PRICES.get(ticker, random 50-300)`; `MassiveDataSource` simply polls whatever is in its ticker list.
- **D-06:** Mutation endpoints always return `200 OK` with `WatchlistMutationResponse { ticker: str, status: Literal["added","exists","removed","not_present"] }`. No 201, no 204, no 409.
- **D-07:** `GET /api/watchlist` returns `WatchlistResponse { items: list[WatchlistItem] }`. Each item carries `ticker, added_at, price, previous_price, change_percent, direction, timestamp` — cache-derived fields fall back to `None` when the cache is cold (never `0`, never omitted, never a 500).
- **D-08:** GET ordering is `ORDER BY added_at ASC, ticker ASC` (same as existing `get_watchlist_tickers` at `app/db/seed.py:69-73`).
- **D-09:** POST write order: (1) Pydantic validate/normalize, (2) service `add_ticker(conn, ticker)` tries INSERT + reports `status="added"`/`"exists"` without raising, (3) if `status="added"` the route awaits `source.add_ticker(ticker)`, (4) return response. Skip source call on `"exists"`.
- **D-10:** DELETE write order: (1) normalize (422 on bad shape), (2) service `remove_ticker(conn, ticker)` reports `status="removed"`/`"not_present"`, (3) if `status="removed"` the route awaits `source.remove_ticker(ticker)` — the source itself calls `cache.remove(ticker)`, (4) return response.
- **D-11:** No atomic DB+source rollback. If a post-commit `source.add_ticker` / `source.remove_ticker` raises, route logs `exc_info=True` and still returns the `WatchlistMutationResponse`. DB is the reconciliation anchor; lifespan re-reads `get_watchlist_tickers(conn)` on startup.
- **D-12:** Use the existing `watchlist.UNIQUE(user_id, ticker)` constraint. Service uses `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING` + `cursor.rowcount` to distinguish added-vs-exists. DELETE uses `cursor.rowcount` (or `RETURNING`). One query per mutation.
- **D-13:** `lifespan.py` mounts the watchlist router after the portfolio router (`backend/app/lifespan.py:66`): `app.include_router(create_watchlist_router(conn, cache, source))`. No new `app.state` fields. Tick observer registration is untouched.

### Claude's Discretion

- **Exact SQL.** `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING` preferred; `INSERT OR IGNORE` equivalent is acceptable.
- **RETURNING clauses.** Planner may use `DELETE ... WHERE ... RETURNING id` instead of `cursor.rowcount` for D-10.
- **Row `id` generation on INSERT.** Match Phase 2 seed: `str(uuid.uuid4())`, `datetime.now(UTC).isoformat()`.
- **DB helper refactor.** Leave `get_watchlist_tickers` alone in `app/db/seed.py`; add new `get_watchlist(conn)` in `app/watchlist/service.py` (option a).
- **Response-model field naming.** `direction` values `"up"/"down"/"flat"` match `PriceUpdate.direction`. Pick one of `timestamp` or `updated_at`.
- **Handler ordering inside `routes.py`.** Any order — APIRouter `prefix="/api/watchlist"` and `tags=["watchlist"]` on the router, not per handler.
- **Test fixtures.** Extend `backend/tests/conftest.py` Phase 3 style (`_build_app` + `db_path`). Watchlist test fixture may pre-warm cache via `cache.update(...)`.
- **Idempotent-add log level.** INFO for both routine mutations and `status="exists"` / `"not_present"` no-ops. Match `seed_defaults` style (`app/db/seed.py:57`).

### Deferred Ideas (OUT OF SCOPE)

- Real-time delivery of watchlist changes to other clients (single-user localhost).
- Ticker existence validation against an external universe (PLAN.md §6 explicitly supports unknown onboarding).
- Bulk mutation endpoints — Phase 5 auto-exec calls the single endpoint in a loop.
- Soft-delete / archive semantics — DELETE is hard per PLAN.md §8.
- Per-user watchlists — schema supports it (`AUTH-01` v2).
- Ticker rename (FB → META) — treat ticker strings as opaque user input.
- History of watchlist mutations — no audit log.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WATCH-01 | `GET /api/watchlist` returns the user's watchlist with latest prices from the cache | "Module shape" (service `get_watchlist`), "SQL recipes" (SELECT), "Pydantic v2 model definitions" (`WatchlistResponse` + `WatchlistItem`), "Route handler choreography" (GET), "Validation Architecture" (criterion #1) |
| WATCH-02 | `POST /api/watchlist` adds a ticker; unknown symbols are onboarded into the market data source on the next tick | "Module shape" (service `add_ticker`), "SQL recipes" (INSERT ON CONFLICT), "Pydantic v2" (`WatchlistAddRequest` + `normalize_ticker`), "Route handler choreography" (POST with await source), "Risks" (simulator seeding of unknown tickers), "Validation Architecture" (criterion #2) |
| WATCH-03 | `DELETE /api/watchlist/{ticker}` removes a ticker and stops tracking it in the cache | "Module shape" (service `remove_ticker`), "SQL recipes" (DELETE), "Pydantic v2" (path-param normalization), "Route handler choreography" (DELETE with await source → source.remove cascades cache.remove), "Validation Architecture" (criterion #3) |

Also covers ROADMAP Success Criterion #4 ("idempotent no-op — NOT a 500") — traced separately in Validation Architecture.

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP endpoint parsing + status code emission | API / Backend (FastAPI router) | — | `routes.py` owns HTTP-shape concerns; consistent with Phase 1 D-04 (factory-closure routers in lifespan) and Phase 3 D-03 |
| Pydantic v2 edge validation + ticker normalization | API / Backend (models.py) | — | Normalizes at the edge per D-04 so the service trusts its input; same discipline as `TradeRequest` |
| Watchlist set-membership semantics (add/exists/remove/not_present) | Database / Storage (SQLite `watchlist` table) | — | DB is the canonical set per PLAN.md §6; `UNIQUE(user_id, ticker)` already enforces the invariant |
| Live-price lookup for GET response | In-memory `PriceCache` | API / Backend (WatchlistItem build) | Cache is the authoritative live-price store; service reads it and maps `None → None` fields |
| Dynamic ticker onboarding / offboarding on the tick loop | Market data source (`SimulatorDataSource` / `MassiveDataSource`) | API / Backend (routes await after DB commit) | Source owns its internal ticker set; it already calls `cache.update`/`cache.remove` on add/remove |
| Reconciliation of cache-set = watchlist-set invariant | Lifespan + market source (DB-driven bootstrap) | API / Backend (log-and-continue on post-commit source failures per D-11) | Lifespan reads `get_watchlist_tickers(conn)` on restart; any transient source/DB divergence heals on next boot |

## Standard Stack

### Core

| Library | Version (verified) | Purpose | Why Standard |
|---------|--------------------|---------|--------------|
| Python stdlib `sqlite3` | Python 3.14 / SQLite 3.50.4 [VERIFIED: `uv run python -c "import sqlite3; print(sqlite3.sqlite_version)"`] | DB access | Already the only DB layer in the project (Phase 2 D-01). Both `ON CONFLICT` (≥3.24) and `RETURNING` (≥3.35) are available. |
| `fastapi` | 0.128.7 [VERIFIED: `uv run python -c "import fastapi; print(fastapi.__version__)"`] | HTTP router + request body validation | Mounted app shell (Phase 1); `APIRouter(prefix=..., tags=[...])` and `HTTPException(status_code=..., detail=...)` are the same primitives Phase 3 uses. |
| `pydantic` | 2.12.5 [VERIFIED: `uv run python -c "import pydantic; print(pydantic.VERSION)"`] | Request/response schemas, field validation | v2 is already in use for `TradeRequest`; `ConfigDict(extra="forbid")`, `field_validator`, `Literal`, `Field` are the idiomatic toolset. |
| Python stdlib `uuid`, `datetime` | Python 3.14 [VERIFIED: standard library] | Row IDs, `added_at` timestamps | Seed code and Phase 3 both use `str(uuid.uuid4())` and `datetime.now(UTC).isoformat()` — match exactly. |

### Supporting (tests)

| Library | Version (verified) | Purpose | When to Use |
|---------|--------------------|---------|-------------|
| `pytest` + `pytest-asyncio` | pytest 8.3+, pytest-asyncio 0.24+ [VERIFIED: `backend/pyproject.toml:18-19`] | Test runner; `asyncio_mode = "auto"` | All tests — matches Phase 3 harness exactly. |
| `httpx` + `asgi-lifespan` | httpx 0.28+, asgi-lifespan 2.1+ [VERIFIED: `backend/pyproject.toml:22-23`] | In-process ASGI client for integration tests | `LifespanManager(app) + ASGITransport(app=app) + AsyncClient(transport=...)` is the canonical pattern established in Phase 3 (see `test_routes_portfolio.py:27-31`). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING` | `INSERT OR IGNORE` | Both set `cursor.rowcount = 0` on conflict and `1` on insert; `ON CONFLICT` is the modern, more explicit SQL:2003 dialect and is already widely used in Python 3.12+ codebases. CONTEXT explicitly allows either (Claude's Discretion). |
| `DELETE ... WHERE ... RETURNING id` | `cursor.rowcount` after plain `DELETE` | `RETURNING` is cleaner when you want the deleted row's id for logging; `rowcount` is one fewer column. Both correctly distinguish 0 from 1. CONTEXT allows either. |
| `response_model=WatchlistMutationResponse` on the route | Plain return of a Pydantic instance | FastAPI validates either way. `response_model=` is the Phase 3 style (`routes.py:34, 38, 55`); keep consistent. |
| `prefix="/api/watchlist"` on the APIRouter | Per-handler `@router.post("/api/watchlist")` | Prefix-on-router matches Phase 3 style. Keep it. |

**Installation:** None needed. All dependencies are already in `backend/pyproject.toml`.

**Version verification:**
- `sqlite3` via stdlib: 3.50.4 (supports `ON CONFLICT` since 3.24, `RETURNING` since 3.35) [VERIFIED: `uv run python -c 'import sqlite3; print(sqlite3.sqlite_version)'` → `3.50.4`]
- `fastapi` 0.128.7 [VERIFIED: `uv run python -c "import fastapi; print(fastapi.__version__)"` → `0.128.7`]
- `pydantic` 2.12.5 [VERIFIED: `uv run python -c "import pydantic; print(pydantic.VERSION)"` → `2.12.5`]

## Architecture Patterns

### System Architecture Diagram

```
                  HTTP client (browser / Phase 5 chat handler / pytest AsyncClient)
                                         │
                                         ▼
                          /api/watchlist  (GET | POST | DELETE/{ticker})
                                         │
                                         ▼
                  ┌────────────────────────────────────────┐
                  │  app/watchlist/routes.py               │
                  │  create_watchlist_router(db, cache,    │
                  │                           source)      │
                  │   (factory closure, one APIRouter)     │
                  └────────────────────────────────────────┘
                        │                │               │
             ┌──────────┘                │               └──────────┐
             │ (GET)                     │ (POST)                   │ (DELETE)
             ▼                           ▼                          ▼
   Pydantic response build     WatchlistAddRequest              normalize_ticker(path)
   from service return         (extra=forbid +                  (shared helper, 422 on bad shape)
                               field_validator:                         │
                               strip+upper+regex)                       ▼
             │                           │                     service.remove_ticker
             ▼                           ▼                       (conn, ticker) → RemoveResult
    service.get_watchlist         service.add_ticker                   │
    (conn)                        (conn, ticker)                       │
     → list[WatchlistRow]         → AddResult                          │
             │                    {ticker, status:                     │
             │                     "added"|"exists"}                   │
             │                           │                             │
             ▼                           ▼                             ▼
     ┌──────────────────────────────────────────────────────────────────────┐
     │  app/watchlist/service.py    (pure functions on sqlite3.Connection)  │
     │  SELECT | INSERT ... ON CONFLICT DO NOTHING | DELETE ... RETURNING   │
     │  conn.commit() after each mutation                                   │
     └──────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
                     sqlite3 (file db/finally.db, UNIQUE(user_id, ticker))
                                         │
              (route, post-commit, conditional on status="added"/"removed")
                                         ▼
                          MarketDataSource.add_ticker(ticker)
                          MarketDataSource.remove_ticker(ticker)
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
       SimulatorDataSource                       MassiveDataSource
       _sim.add_ticker → seeds cache             _tickers.append;
       _sim.remove_ticker; cache.remove          cache.remove on remove
                    │                                         │
                    └──────────────────┬──────────────────────┘
                                       ▼
                                  PriceCache
                                       │
                                       ▼
                       next tick / next poll loop pushes update
                                       │
                                       ▼
                         /api/stream/prices (already live; sends cache.get_all())
                         GET response reads cache for price/timestamp/direction
```

**Read path (GET):** `routes.get_watchlist` → `service.get_watchlist(conn) → list[Row(ticker, added_at)]` → for each row read `cache.get(ticker) → PriceUpdate | None` → build `WatchlistItem` with `None` fallback for cache-derived fields.

**Write path (POST):** Pydantic (422 on bad ticker/extra keys/missing body) → `service.add_ticker(conn, ticker) → AddResult` (one `INSERT ... ON CONFLICT DO NOTHING` + `cursor.rowcount` branch) → commit → if `added` await `source.add_ticker(ticker)` (simulator seeds cache immediately; massive appends to `_tickers` for next poll) → return `WatchlistMutationResponse`.

**Write path (DELETE):** `normalize_ticker(path)` (422 on bad shape) → `service.remove_ticker(conn, ticker) → RemoveResult` (one `DELETE ... WHERE ... RETURNING id` or plain DELETE + `cursor.rowcount`) → commit → if `removed` await `source.remove_ticker(ticker)` (the source itself calls `cache.remove(ticker)`) → return `WatchlistMutationResponse`.

### Recommended Project Structure

```
backend/app/watchlist/
├── __init__.py                # Explicit __all__: factory, service fns, models
├── models.py                  # Pydantic v2 schemas + normalize_ticker helper
├── routes.py                  # create_watchlist_router(db, cache, source)
└── service.py                 # get_watchlist, add_ticker, remove_ticker

backend/tests/watchlist/
├── __init__.py
├── conftest.py                # fresh_db + warmed_cache fixtures (mirror portfolio/conftest.py)
├── test_models.py             # normalize_ticker + WatchlistAddRequest validator
├── test_service_get.py        # get_watchlist ordering + empty set
├── test_service_add.py        # add_ticker added | exists + cursor.rowcount semantics
├── test_service_remove.py     # remove_ticker removed | not_present
├── test_routes_get.py         # GET /api/watchlist — shape + None fallback
├── test_routes_post.py        # POST /api/watchlist — 200 added | 200 exists | 422 on bad body
└── test_routes_delete.py      # DELETE /api/watchlist/{ticker} — 200 removed | 200 not_present | 422 on bad path
```

### Pattern 1: Factory-closure router (mirrors Phase 3)

**What:** A single function `create_watchlist_router(db, cache, source)` returns a fresh `APIRouter` per call, closing over its three dependencies. No module-level router object.

**When to use:** Every router in this codebase (Phase 1 D-04, Phase 3 D-03).

**Example (direct template — `backend/app/portfolio/routes.py:21-61`):**
```python
# Source: backend/app/portfolio/routes.py (Phase 3)
def create_portfolio_router(
    db: sqlite3.Connection,
    cache: PriceCache,
) -> APIRouter:
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("", response_model=PortfolioResponse)
    async def get_portfolio() -> PortfolioResponse:
        return service.get_portfolio(db, cache)

    @router.post("/trade", response_model=TradeResponse)
    async def post_trade(request: Request, req: TradeRequest) -> TradeResponse:
        try:
            response = service.execute_trade(...)
        except service.TradeValidationError as exc:
            raise HTTPException(status_code=400, detail={...}) from exc
        return response

    return router
```

### Pattern 2: Pure-function DB-only service (mirrors Phase 3)

**What:** Top-level functions taking `(conn: sqlite3.Connection, ...)` as their first positional arg. No class state. No FastAPI imports. Returns dataclasses / Pydantic models.

**When to use:** Every sub-package service in this codebase (Phase 2 `app/db/seed.py`, Phase 3 `app/portfolio/service.py`). Required for Phase 5 reuse (CONTEXT D-02).

**Example (direct template — `backend/app/portfolio/service.py`):**
```python
# Source: backend/app/portfolio/service.py
def execute_trade(
    conn: sqlite3.Connection,
    cache: PriceCache,
    ticker: str,
    side: Literal["buy", "sell"],
    quantity: float,
    user_id: str = DEFAULT_USER_ID,
) -> TradeResponse:
    """... one conn.commit() at the end."""
    ...
    conn.commit()
    return TradeResponse(...)
```

### Pattern 3: Pydantic v2 strict request body with `field_validator`

**What:** `ConfigDict(extra="forbid")` + `@field_validator(mode="before")` + regex check. Reject malformed input as 422 at the FastAPI edge.

**When to use:** Any POST/PUT/PATCH body. Path params use a shared helper (D-04).

**Example (verified locally against pydantic 2.12.5):**
```python
# Verified via uv run python -c "..." (see research notes)
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")


def normalize_ticker(value: str) -> str:
    """Strip + uppercase + regex-validate a ticker symbol. Raises ValueError on mismatch."""
    v = value.strip().upper()
    if not _TICKER_RE.fullmatch(v):
        raise ValueError(f"invalid ticker: {value!r}")
    return v


class WatchlistAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str = Field(min_length=1, max_length=10)

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_ticker(v)
```

### Pattern 4: Idempotent mutation response (novel to Phase 4)

**What:** One HTTP status (`200 OK`), one response shape (`WatchlistMutationResponse`), a `status: Literal[...]` discriminator. Callers branch on `status`, not on HTTP code.

**When to use:** Any endpoint where the distinction between "I made the change" and "it was already that way" is semantically meaningful but not an error.

**Example (Phase 4 new design per CONTEXT D-06):**
```python
# Response for POST /api/watchlist and DELETE /api/watchlist/{ticker}
class WatchlistMutationResponse(BaseModel):
    ticker: str
    status: Literal["added", "exists", "removed", "not_present"]
```

### Anti-Patterns to Avoid

- **Service taking `MarketDataSource`.** Rejected by D-02. Would force the service async and couple the DB layer to the market subsystem — breaks Phase 5 reuse.
- **Source-first, DB-second mutation ordering.** Rejected by D-09/D-10. A source-only ticker would not survive a restart (PLAN.md §6: cache-set is reconstructed from `get_watchlist_tickers(conn)` on every boot at `lifespan.py:57`).
- **Returning `0.0` placeholders when cache is cold.** Rejected by D-07. Lies about a real price and makes the frontend unable to distinguish "no data yet" from "price is literally zero."
- **`HTTPException(409)` on duplicate add.** Rejected by D-06. Success criterion #4 requires a "sensible response, NOT a 500/4xx." Uniform 200 + status is the contract.
- **Atomic DB-source two-phase commit.** Rejected by D-11. Over-engineered; both source implementations already swallow their own errors, and the lifespan restart heals any transient divergence.
- **`f`-strings in logging calls.** Project convention (CONVENTIONS.md "f-strings in logging calls (breaks lazy formatting)"). Use `%`-style placeholders.
- **Emojis in any output.** Global `~/.claude/CLAUDE.md` rule.
- **Relative imports like `from app.watchlist.service import ...` inside the sub-package.** Use `from . import service` / `from .service import add_ticker`, matching `app/portfolio/routes.py:12`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request body validation (extra keys, empty strings, non-string tickers) | A dict-based body parser with manual `if "ticker" not in body: raise HTTPException(...)` | `WatchlistAddRequest(BaseModel, ConfigDict(extra="forbid"))` + FastAPI auto-binding | FastAPI + Pydantic v2 already return 422 with a precise error structure. Hand-rolled validation misses edge cases (`null`, extra keys, wrong type). |
| Ticker normalization (uppercase / strip / regex) | Inline logic in each handler | Single `normalize_ticker(value) -> str` helper in `models.py` | D-04 explicitly mandates one shared helper for POST body + DELETE path; duplication drifts. |
| Duplicate-add detection (SELECT-then-INSERT) | `conn.execute("SELECT 1 ...").fetchone()` + branch + `INSERT` | `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING` + `cursor.rowcount` | One query instead of two, atomic at the DB level, race-free. The `UNIQUE(user_id, ticker)` constraint is already present in `backend/app/db/schema.py:21`. |
| Not-present-delete detection (SELECT-then-DELETE) | `conn.execute("SELECT 1 ...").fetchone()` + branch + `DELETE` | Plain `DELETE` + `cursor.rowcount`, or `DELETE ... RETURNING id` | Same reasoning — one query, race-free. Planner may pick either shape (CONTEXT Claude's Discretion). |
| Cache-cold fallback when building `WatchlistItem.price` | Try/except around `cache.get_price(ticker)` | `cache.get(ticker)` returns `PriceUpdate | None`; branch with `if upd is None:` and emit all cache-derived fields as `None` | `PriceCache.get` is already None-safe; no exception path to catch. Matches `get_portfolio` avg_cost fallback style (Phase 3). |
| Keeping the cache in sync on DELETE | `cache.remove(ticker)` from the route | `source.remove_ticker(ticker)` already calls `cache.remove` (simulator.py:256, massive_client.py:77) | The source owns its cache interactions. Calling `cache.remove` from the route would double-remove and duplicate the invariant location. |
| Lifespan-wide router refactor | Rework `create_market_data_source` / `open_database` / etc. | Single `app.include_router(create_watchlist_router(conn, cache, source))` line | One new line at `backend/app/lifespan.py:66`. Everything else is already wired (CONTEXT D-13). |
| Request ID generation | UUID factories per route | `str(uuid.uuid4())` inline, matching Phase 2 seed (`app/db/seed.py:55`) and Phase 3 trade inserts | Keep it consistent. No "request ID service." |

**Key insight:** The sqlite3 `UNIQUE` constraint + `ON CONFLICT DO NOTHING` + `cursor.rowcount` is the entire idempotency primitive. Everything else — HTTP status, response shape, source-call conditionality — flows from that one row count.

## Runtime State Inventory

Not applicable — Phase 4 is a greenfield additive phase (new sub-package + one mount line). No rename, refactor, migration, or string replacement is in scope. Phase 2 already seeded the 10 default tickers; Phase 4 does not reseed or re-key any existing state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no existing watchlist code to rename; schema/rows unchanged | None |
| Live service config | None — no external service registered under any old name | None |
| OS-registered state | None — no scheduled tasks / pm2 / systemd | None |
| Secrets / env vars | None — no new env var added (existing `MASSIVE_API_KEY` / `DB_PATH` untouched) | None |
| Build artifacts | None — no package rename, `pyproject.toml` unchanged | None |

## Common Pitfalls

### Pitfall 1: GET response shape diverges from PriceUpdate vocabulary

**What goes wrong:** `WatchlistItem.direction` uses `"increased"/"decreased"/"unchanged"` (or some other synonym) instead of `PriceUpdate.direction`'s `"up"/"down"/"flat"`. Frontend ends up branching on two string vocabularies.

**Why it happens:** Pydantic v2's `Literal` is easy to define inconsistently when the source-of-truth (`app/market/models.py:31-37`) lives in another sub-package.

**How to avoid:** Model `WatchlistItem.direction` as `Literal["up", "down", "flat"] | None` — copy the strings from `PriceUpdate.direction` verbatim (CONTEXT Claude's Discretion). When building a `WatchlistItem`, pass the raw `price_update.direction` string through; never translate.

**Warning signs:** Frontend devs asking "what values can direction be?"; test assertions duplicating the literal set.

### Pitfall 2: `source.add_ticker` awaited on `"exists"` duplicates work

**What goes wrong:** Route calls `await source.add_ticker(ticker)` unconditionally after `service.add_ticker`. The source's idempotent early-return (`simulator.py:122-124`, `massive_client.py:68-72`) absorbs the duplicate, but you pay a log line and a method call for no behavior change.

**Why it happens:** "Idempotent anyway, just call it" laziness.

**How to avoid:** Branch on `result.status`. `if result.status == "added": await source.add_ticker(ticker)`. Same pattern for DELETE. CONTEXT D-09/D-10 explicitly require this.

**Warning signs:** Tests seeing "added ticker X" INFO logs twice for a `status="exists"` response; noise in lifespan logs after the LLM spams `watchlist_changes`.

### Pitfall 3: Stale source state after lifespan restart — DB wins

**What goes wrong:** A watchlist ticker that was added via POST but never made it into the source (process crashed between DB commit and `await source.add_ticker`) is missing from the cache after restart.

**Why it happens:** No atomic DB+source commit (CONTEXT D-11 explicit tradeoff).

**How to avoid:** This is a designed-for behavior. The lifespan at `backend/app/lifespan.py:57` reads `get_watchlist_tickers(conn)` and passes the full list to `source.start(tickers)` — the source's active set is rebuilt from DB on every boot. The planner should NOT try to "fix" this with a reconciliation task in Phase 4.

**Warning signs:** Ticker in GET response with `price: None` forever (never getting a tick) — but this should self-heal on next restart, not require Phase 4 code.

### Pitfall 4: `cursor.rowcount` after `executemany` / CTE / pragma-affected statements

**What goes wrong:** Future refactor adds a pre-step (e.g., `PRAGMA foreign_keys = ON`) and `cursor.rowcount` silently reads the wrong value.

**Why it happens:** `cursor.rowcount` in Python's `sqlite3` reflects the last DML executed on that cursor — pragmas and other DDL can clobber it in unusual wrappers.

**How to avoid:** Call `conn.execute(sql, params)` (not a reused cursor) so each mutation gets a fresh cursor. Read `cur.rowcount` on the returned cursor immediately before `conn.commit()`. The single-INSERT / single-DELETE shapes in `app/portfolio/service.py` already follow this; mirror them.

**Warning signs:** Flaky test where `status == "exists"` appears for a fresh row.

### Pitfall 5: Fixture cache pre-warm not matching the simulator's seed

**What goes wrong:** Test pre-warms `PriceCache` with `AAPL → 100.0` but the simulator running in a real-lifespan test has already pushed `AAPL → 190.xx`. Assertions on `price` become brittle.

**Why it happens:** Two sources of truth for ticker prices in tests.

**How to avoid:** For service unit tests (`test_service_*.py`), use an in-memory sqlite3 connection plus a `warmed_cache` fixture mirroring Phase 3's `tests/portfolio/conftest.py:28-34` — the cache is completely test-controlled, no simulator involved. For route tests, use the full lifespan harness but read the cache snapshot back from the response rather than hardcoding prices (see Phase 3's `test_routes_portfolio.py:38-61` for the pattern).

**Warning signs:** Sporadic test failures only in CI (different simulator RNG timing).

### Pitfall 6: Pydantic v2 `field_validator` mode confusion

**What goes wrong:** `@field_validator("ticker")` without `mode="before"` runs AFTER Pydantic's type coercion, so `.strip().upper()` works but `Field(min_length=1)` has already fired on the pre-normalized string. A submitted `"  AAPL  "` might fail `min_length` — or not, depending on field ordering.

**Why it happens:** v2 split validators into `"before"` (pre-coercion) and `"after"` (default, post-coercion) — Phase 3's `TradeRequest` doesn't use validators at all so there's no in-codebase reference.

**How to avoid:** Use `@field_validator("ticker", mode="before")` (tested locally against pydantic 2.12.5 — confirmed strip+upper+regex in one call handles whitespace correctly). Drop `min_length=1` on the field and rely on the regex (`^[A-Z][A-Z0-9.]{0,9}$`) — `min_length` becomes redundant and potentially conflicting.

**Warning signs:** Test `test_accepts_lowercase_and_whitespace` fails with a 422 instead of normalizing.

### Pitfall 7: SSE stream does not self-filter — relies on cache

**What goes wrong:** Planner assumes SSE filters to `watchlist` tickers per request. It does NOT. `app/market/stream.py:83` reads `price_cache.get_all()` and emits everything in the cache.

**Why it happens:** The PLAN.md §6 text "filters to watchlist set" describes the cache invariant, not an SSE-level filter.

**How to avoid:** Understand that add/remove only affect the SSE because they mutate the cache (via `source.add_ticker → _cache.update` on add; via `source.remove_ticker → cache.remove` on remove). A Phase 4 test asserting "SSE no longer includes ticker X after DELETE" must (a) trigger a real tick after the DELETE (or poll `cache.get_all()` directly as a proxy for the SSE payload), not assert on SSE filtering logic that does not exist.

**Warning signs:** A test hangs waiting for the SSE to "stop emitting" a ticker. Instead, assert `cache.get_all()` shape, which is the actual invariant.

## Code Examples

Verified patterns from the existing codebase. Phase 4 should clone these shapes.

### Example 1: `INSERT ... ON CONFLICT DO NOTHING` with rowcount discrimination

```python
# New code for app/watchlist/service.py (pattern from standard sqlite3 docs + CONTEXT D-12)
def add_ticker(
    conn: sqlite3.Connection,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> AddResult:
    """Insert a watchlist row; return status='added' on insert, 'exists' on UNIQUE conflict.

    One query per mutation (D-12). Relies on UNIQUE(user_id, ticker) already defined in
    backend/app/db/schema.py line 21.
    """
    now = datetime.now(UTC).isoformat()
    cur = conn.execute(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, ticker) DO NOTHING",
        (str(uuid.uuid4()), user_id, ticker, now),
    )
    if cur.rowcount == 1:
        conn.commit()
        logger.info("Watchlist: added %s for user %s", ticker, user_id)
        return AddResult(ticker=ticker, status="added")

    logger.info("Watchlist: %s already present for user %s (no-op)", ticker, user_id)
    return AddResult(ticker=ticker, status="exists")
```

### Example 2: `DELETE ... RETURNING` for rowcount discrimination

```python
# New code for app/watchlist/service.py
def remove_ticker(
    conn: sqlite3.Connection,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> RemoveResult:
    """Delete a watchlist row; return status='removed' on DELETE, 'not_present' on no-op."""
    cur = conn.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ? RETURNING id",
        (user_id, ticker),
    )
    deleted = cur.fetchone()
    if deleted is not None:
        conn.commit()
        logger.info("Watchlist: removed %s for user %s", ticker, user_id)
        return RemoveResult(ticker=ticker, status="removed")

    logger.info("Watchlist: %s not present for user %s (no-op)", ticker, user_id)
    return RemoveResult(ticker=ticker, status="not_present")

# Planner may prefer cursor.rowcount (both shapes are accepted per CONTEXT):
#     cur = conn.execute("DELETE FROM watchlist WHERE ...", (user_id, ticker))
#     if cur.rowcount == 1:  # ...
```

### Example 3: GET with cache-cold fallback

```python
# New code for app/watchlist/service.py
def get_watchlist(
    conn: sqlite3.Connection,
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
) -> WatchlistResponse:
    """Return watchlist rows with live prices from cache; None fallback when cold (D-07)."""
    rows = conn.execute(
        "SELECT ticker, added_at FROM watchlist "
        "WHERE user_id = ? ORDER BY added_at ASC, ticker ASC",
        (user_id,),
    ).fetchall()

    items: list[WatchlistItem] = []
    for row in rows:
        ticker = row["ticker"]
        upd = cache.get(ticker)  # PriceUpdate | None
        if upd is None:
            items.append(WatchlistItem(
                ticker=ticker,
                added_at=row["added_at"],
                price=None,
                previous_price=None,
                change_percent=None,
                direction=None,
                timestamp=None,
            ))
        else:
            items.append(WatchlistItem(
                ticker=ticker,
                added_at=row["added_at"],
                price=upd.price,
                previous_price=upd.previous_price,
                change_percent=upd.change_percent,
                direction=upd.direction,  # Literal["up","down","flat"]
                timestamp=upd.timestamp,
            ))
    return WatchlistResponse(items=items)
```

### Example 4: Route choreography (DB first, source second, log-and-continue)

```python
# New code for app/watchlist/routes.py
@router.post("", response_model=WatchlistMutationResponse)
async def post_watchlist(req: WatchlistAddRequest) -> WatchlistMutationResponse:
    """Add a ticker to the watchlist; idempotent no-op on duplicate (D-06, D-09, D-11)."""
    result = service.add_ticker(db, req.ticker)

    if result.status == "added":
        try:
            await source.add_ticker(req.ticker)
        except Exception:
            # D-11: DB is the reconciliation anchor; next restart heals.
            logger.warning(
                "Watchlist: source.add_ticker(%s) raised after DB commit",
                req.ticker,
                exc_info=True,
            )

    return WatchlistMutationResponse(ticker=result.ticker, status=result.status)
```

### Example 5: Integration-test harness (direct clone from Phase 3)

```python
# backend/tests/watchlist/test_routes_post.py - mirrors tests/portfolio/test_routes_trade.py
from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.lifespan import lifespan


def _build_app() -> FastAPI:
    return FastAPI(lifespan=lifespan)


@pytest.mark.asyncio
class TestPostWatchlist:
    async def test_add_new_ticker_returns_added(self, db_path):
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post("/api/watchlist", json={"ticker": "PYPL"})
                    assert resp.status_code == 200, resp.text
                    body = resp.json()
                    assert body == {"ticker": "PYPL", "status": "added"}
                    assert "PYPL" in app.state.market_source.get_tickers()

    async def test_duplicate_returns_exists_not_409(self, db_path):
        # AAPL is in the seed watchlist; duplicate POST must NOT return 409/500.
        ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `@validator(pre=True)` | Pydantic v2 `@field_validator("field", mode="before")` + `@classmethod` | Pydantic 2.0 (June 2023); codebase is on 2.12.5 | Use v2 idioms; `min_length` lives on `Field(...)` not `@validator` |
| `class Config: extra = "forbid"` (v1 inner class) | `model_config = ConfigDict(extra="forbid")` (v2 class attr) | Pydantic 2.0 | Match `TradeRequest` in `app/portfolio/models.py:17` |
| `Optional[str]` / `Optional[float]` | `str | None` / `float | None` | PEP 604 (Python 3.10) + project `from __future__ import annotations` | CONVENTIONS.md explicit rule — never use `Optional[X]` |
| `SELECT ... + branch + INSERT` for dedup | `INSERT ... ON CONFLICT DO NOTHING` + `cursor.rowcount` | SQLite 3.24 (June 2018); stdlib supports since Python 3.8 | One atomic query instead of two; race-free |
| Per-handler router-object at module level | `create_*_router(...)` factory returning fresh `APIRouter` per call | Phase 1 D-04 (Plan 01-03 discovered the duplicate-route bug) | Required for test isolation — CONVENTIONS.md `FastAPI idioms` |

**Deprecated/outdated:**
- Pydantic v1 validator syntax — project is on v2.12.5; do not import `validator` or `root_validator`.
- `sqlite3.Row` being optional — already set globally in `open_database` (Phase 2 D-02); all `row["ticker"]` access works.

## Assumptions Log

All claims in the Standard Stack table are `[VERIFIED]` via direct `uv run` inspection of the installed versions and library APIs. All claims about existing codebase shapes are `[VERIFIED]` by `Read` of the referenced files. All claims about Pydantic v2 `field_validator(mode="before")` behavior are `[VERIFIED]` by running a small test script against `pydantic 2.12.5` in the project's virtual environment.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | (none) | — | — |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions

1. **Field naming: `timestamp` vs `updated_at` on `WatchlistItem`.**
   - What we know: `PriceUpdate.timestamp` (Unix float seconds, `app/market/models.py:16`) is the cache's live-price timestamp. `watchlist.added_at` (ISO string) is the DB row's creation time. These are two different fields that already coexist in the response.
   - What's unclear: Whether to call the cache timestamp `timestamp` (matching `PriceUpdate.timestamp`) or `updated_at` (matching `positions.updated_at` column naming).
   - Recommendation: Use `timestamp: float | None` — matches `PriceUpdate.to_dict()` verbatim (`app/market/models.py:44`), reduces frontend translation. `added_at` stays as the ISO-string column name per schema.

2. **Handler ordering inside `routes.py`.**
   - What we know: `prefix="/api/watchlist"` + `tags=["watchlist"]` on the router (Phase 3 D-03 parity).
   - What's unclear: GET → POST → DELETE or POST → DELETE → GET order.
   - Recommendation: GET → POST → DELETE (reader-friendly: read before write, add before remove). FastAPI doesn't care. Claude's Discretion per CONTEXT.

3. **`DELETE` SQL shape: `RETURNING id` vs `cursor.rowcount`.**
   - What we know: Both work (SQLite 3.35+ has `RETURNING`; project runs 3.50.4). Both are acceptable per CONTEXT Claude's Discretion.
   - What's unclear: Which is more idiomatic for this codebase.
   - Recommendation: Use `cursor.rowcount` — matches the add path's `cursor.rowcount` check, which is one consistent read pattern. `RETURNING` is fine if planner prefers the stronger "I got the row I deleted" signal, but it's an extra column for no behavior gain.

4. **Where should `normalize_ticker` live?**
   - What we know: D-04 mandates one shared helper called from both `WatchlistAddRequest.field_validator` and the DELETE path-param pre-check.
   - What's unclear: `models.py` vs a dedicated `validators.py` module.
   - Recommendation: `models.py` (top of the file, before the `BaseModel` classes). Keeps the Pydantic-facing code in one place. No need for a new module for one helper.

5. **Is `service.get_watchlist` allowed to depend on `PriceCache`?**
   - What we know: D-02 says "Service functions do NOT take `MarketDataSource`." It does NOT say "do not take `PriceCache`." Phase 3's `get_portfolio` takes both `conn` and `cache`.
   - What's unclear: Whether `get_watchlist(conn, cache)` violates the "pure DB-only" framing.
   - Recommendation: Take both. The "DB-only" framing in D-02 is about avoiding the async `MarketDataSource` surface, not about avoiding the synchronous in-process `PriceCache`. Phase 3 sets the precedent. Phase 5 chat auto-exec will not call `get_watchlist` from its handler (it will generate the snapshot for prompt context via a different path), so no reuse concern.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All backend code | ✓ | 3.14.2 [VERIFIED] | — |
| `uv` | Package manager | ✓ | Present (inherited from Phase 1-3) | — |
| stdlib `sqlite3` | Service DB access | ✓ | 3.50.4 (ON CONFLICT ≥3.24, RETURNING ≥3.35) [VERIFIED] | — |
| `fastapi` | Routers | ✓ | 0.128.7 [VERIFIED] | — |
| `pydantic` | Models + validators | ✓ | 2.12.5 [VERIFIED] | — |
| `pytest`, `pytest-asyncio`, `httpx`, `asgi-lifespan` | Tests | ✓ | Per `backend/pyproject.toml:18-24` [VERIFIED] | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

Phase 4 adds zero dependencies and zero dev dependencies. No `uv add` is required.

## Validation Architecture

Phase 4 honors Nyquist validation (`workflow.nyquist_validation: true` in `.planning/config.json`). Every success criterion maps to an automated pytest assertion.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` 8.3+ with `pytest-asyncio` 0.24+ (`asyncio_mode = "auto"`) [VERIFIED: `backend/pyproject.toml:33-39`] |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd backend && uv run --extra dev pytest tests/watchlist -v` |
| Full suite command | `cd backend && uv run --extra dev pytest -v` |

### Phase Requirements → Test Map

| Req ID / Criterion | Behavior | Test Type | Automated Command | File Exists? |
|--------------------|----------|-----------|-------------------|--------------|
| WATCH-01 / SC#1 | `GET /api/watchlist` returns all 10 seed tickers ordered `added_at ASC, ticker ASC` | integration | `pytest tests/watchlist/test_routes_get.py::TestGetWatchlist::test_returns_seeded_tickers -v` | ❌ Wave 0 |
| WATCH-01 / SC#1 | `GET` item includes `price` from `PriceCache` when tick is present | integration | `pytest tests/watchlist/test_routes_get.py::TestGetWatchlist::test_price_from_cache -v` | ❌ Wave 0 |
| WATCH-01 / SC#1 | `GET` item returns `None` for all cache-derived fields when cache is cold | unit | `pytest tests/watchlist/test_service_get.py::TestGetWatchlist::test_cold_cache_fallback -v` | ❌ Wave 0 |
| WATCH-02 / SC#2 | `POST /api/watchlist` with new ticker → 200, `status="added"`, DB row inserted | integration | `pytest tests/watchlist/test_routes_post.py::TestPost::test_add_new_ticker_returns_added -v` | ❌ Wave 0 |
| WATCH-02 / SC#2 | After POST, `source.get_tickers()` includes the new ticker | integration | `pytest tests/watchlist/test_routes_post.py::TestPost::test_add_onboards_to_source -v` | ❌ Wave 0 |
| WATCH-02 / SC#2 | After POST (simulator), `cache.get(ticker)` is non-None (simulator seeds immediately per `simulator.py:247-250`) | integration | `pytest tests/watchlist/test_routes_post.py::TestPost::test_add_warms_cache -v` | ❌ Wave 0 |
| WATCH-03 / SC#3 | `DELETE /api/watchlist/{ticker}` with existing ticker → 200, `status="removed"`, DB row deleted | integration | `pytest tests/watchlist/test_routes_delete.py::TestDelete::test_remove_existing_ticker -v` | ❌ Wave 0 |
| WATCH-03 / SC#3 | After DELETE, `source.get_tickers()` does not include the ticker | integration | `pytest tests/watchlist/test_routes_delete.py::TestDelete::test_remove_stops_source -v` | ❌ Wave 0 |
| WATCH-03 / SC#3 | After DELETE, `cache.get(ticker)` returns None | integration | `pytest tests/watchlist/test_routes_delete.py::TestDelete::test_remove_purges_cache -v` | ❌ Wave 0 |
| SC#4 | Duplicate POST → 200, `status="exists"`, **not 409, not 500**, DB row count unchanged | integration | `pytest tests/watchlist/test_routes_post.py::TestPost::test_duplicate_returns_exists_not_error -v` | ❌ Wave 0 |
| SC#4 | DELETE non-present ticker → 200, `status="not_present"`, **not 404, not 500** | integration | `pytest tests/watchlist/test_routes_delete.py::TestDelete::test_missing_returns_not_present_not_error -v` | ❌ Wave 0 |
| D-04 / D-06 | Malformed body (extra key, empty ticker, non-matching regex) → 422 | integration | `pytest tests/watchlist/test_routes_post.py::TestPostValidation -v` | ❌ Wave 0 |
| D-04 | Malformed path param on DELETE → 422 via `normalize_ticker` helper | integration | `pytest tests/watchlist/test_routes_delete.py::TestDeleteValidation::test_bad_path_422 -v` | ❌ Wave 0 |
| D-04 | `normalize_ticker("  aapl  ")` → `"AAPL"` | unit | `pytest tests/watchlist/test_models.py::TestNormalize -v` | ❌ Wave 0 |
| D-04 | `normalize_ticker("BRK.B")` accepted; `normalize_ticker("1X")` rejected | unit | `pytest tests/watchlist/test_models.py::TestNormalize -v` | ❌ Wave 0 |
| D-08 | GET returns items ordered `added_at ASC, ticker ASC` (10 seed tickers in insertion order) | integration | `pytest tests/watchlist/test_routes_get.py::TestGetWatchlist::test_ordering -v` | ❌ Wave 0 |
| D-09 | Service `add_ticker` on existing row returns `status="exists"` with no second INSERT | unit | `pytest tests/watchlist/test_service_add.py::TestAdd::test_duplicate_status_exists -v` | ❌ Wave 0 |
| D-10 | Service `remove_ticker` on missing row returns `status="not_present"` | unit | `pytest tests/watchlist/test_service_remove.py::TestRemove::test_missing_status_not_present -v` | ❌ Wave 0 |
| D-11 | Source.add_ticker raises → route still returns 200 with `status="added"` (DB committed); warning logged with `exc_info=True` | integration | `pytest tests/watchlist/test_routes_post.py::TestPost::test_source_failure_logs_but_returns_200 -v` | ❌ Wave 0 |
| D-13 | Lifespan mounts the watchlist router; `/api/watchlist` is reachable after app boot | integration | `pytest tests/test_lifespan.py::TestLifespan::test_watchlist_router_mounted -v` | ❌ Wave 0 (extend existing) |

### Sampling Rate

- **Per task commit:** `uv run --extra dev pytest tests/watchlist -v` (target: <10 seconds for the full watchlist subtree)
- **Per wave merge:** `uv run --extra dev pytest -v` (full backend suite — currently 158 tests, plus ~18 new = ~176)
- **Phase gate:** `uv run --extra dev pytest -v && uv run --extra dev ruff check app/ tests/` (both green before `/gsd-verify-work`)

### Wave 0 Gaps

All test files below are new for Phase 4. No framework install needed (harness is identical to Phase 3).

- [ ] `backend/tests/watchlist/__init__.py` — empty package marker (mirrors `tests/portfolio/__init__.py`)
- [ ] `backend/tests/watchlist/conftest.py` — `fresh_db` + `warmed_cache` fixtures (copy from `tests/portfolio/conftest.py:15-34`)
- [ ] `backend/tests/watchlist/test_models.py` — `normalize_ticker` helper + `WatchlistAddRequest.field_validator` unit tests
- [ ] `backend/tests/watchlist/test_service_get.py` — `get_watchlist` ordering + cold-cache fallback
- [ ] `backend/tests/watchlist/test_service_add.py` — `add_ticker` added vs exists paths + UNIQUE constraint
- [ ] `backend/tests/watchlist/test_service_remove.py` — `remove_ticker` removed vs not_present paths
- [ ] `backend/tests/watchlist/test_routes_get.py` — GET integration (fresh DB, 10 seed tickers, live prices)
- [ ] `backend/tests/watchlist/test_routes_post.py` — POST integration (200/added, 200/exists, 422 validation, source failure log-and-continue)
- [ ] `backend/tests/watchlist/test_routes_delete.py` — DELETE integration (200/removed, 200/not_present, 422 path validation)
- [ ] `backend/tests/test_lifespan.py` — extend existing file (not new) with one test asserting `/api/watchlist` is mounted

## Security Domain

Phase 4 is a single-user localhost demo (no auth, no session, no external ingress beyond the local Docker container). `security_enforcement` is not explicitly set in `.planning/config.json` — treat as enabled for completeness. The applicable surfaces are limited.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user by design (PLAN.md §2 "No login, no signup"). `AUTH-01` is explicit v2 deferral. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | All rows are keyed on `user_id = "default"`; single user. |
| V5 Input Validation | yes | **Pydantic v2 `extra="forbid"` + `field_validator(mode="before")` + regex `^[A-Z][A-Z0-9.]{0,9}$` on POST body; `normalize_ticker` helper + 422 on DELETE path param.** This is the core Phase 4 security control — it prevents SQL injection on the `watchlist.ticker` column and prevents storage of unbounded / ugly strings via the watchlist endpoint. |
| V6 Cryptography | no | No secrets handled in this phase. |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection on `ticker` column | Tampering | Parameterized queries (`?` placeholders) throughout service (Phase 2 D-03). The regex `^[A-Z][A-Z0-9.]{0,9}$` provides a second layer — even if the SQL layer were wrapped wrong, only `[A-Z0-9.]` strings reach it. |
| Denial-of-service via oversized body | DoS | `ConfigDict(extra="forbid")` + `Field(min_length=1, max_length=10)` + FastAPI's default body size limits. |
| Enumeration of watchlist across users | Info Disclosure | N/A — single-user, `user_id = "default"` hardcoded. v2 `AUTH-01` adds isolation. |
| Log forging via ticker containing `\n` | Tampering / Info Disclosure | Regex-validated input prevents newlines in `ticker`. Logged values are safe. |
| Race between DB commit and source-await | Integrity | CONTEXT D-11 accepts the tradeoff; reconciliation happens on next lifespan start. The source's idempotent add/remove makes repeated calls safe if a retry were ever introduced. |

## Sources

### Primary (HIGH confidence)

- `backend/app/portfolio/routes.py` — factory-closure router template (CONTEXT D-01, D-02, D-03 parity)
- `backend/app/portfolio/service.py` — pure-function service template + `execute_trade` validate/write/commit pattern
- `backend/app/portfolio/models.py` — Pydantic v2 `ConfigDict(extra="forbid")` + `Literal` + `Field` shape
- `backend/app/portfolio/__init__.py` — explicit `__all__` re-export pattern
- `backend/app/lifespan.py` — mount-point reference (line 66, after `create_portfolio_router`)
- `backend/app/db/schema.py:14-23` — `watchlist` table + `UNIQUE(user_id, ticker)`
- `backend/app/db/seed.py:62-73` — `get_watchlist_tickers` ordering + `DEFAULT_USER_ID` constant reuse
- `backend/app/market/interface.py` — `MarketDataSource` ABC: `add_ticker`/`remove_ticker` idempotency contract
- `backend/app/market/simulator.py:244-257` — `SimulatorDataSource.add_ticker` (seeds cache immediately) / `remove_ticker` (calls `cache.remove`)
- `backend/app/market/massive_client.py:68-78` — `MassiveDataSource.add_ticker` (early return on present) / `remove_ticker` (filters + cache.remove)
- `backend/app/market/cache.py` — `get(ticker) -> PriceUpdate | None` / `remove(ticker)` / thread-safe via `Lock`
- `backend/app/market/models.py:31-37` — `PriceUpdate.direction` = `"up" | "down" | "flat"` (vocabulary source)
- `backend/app/market/stream.py:83` — SSE reads `price_cache.get_all()`; does NOT filter by watchlist (Pitfall 7)
- `backend/tests/portfolio/conftest.py` — `fresh_db` + `warmed_cache` fixtures to clone
- `backend/tests/portfolio/test_routes_portfolio.py` — integration test harness (`_build_app` + `LifespanManager` + `ASGITransport` + `AsyncClient`)
- `backend/tests/portfolio/test_service_validation.py` — zero-DB-writes-on-rejection assertion pattern (mirror for idempotent-no-op assertions)
- `backend/pyproject.toml` — verified dependency versions
- Direct version verification: `uv run python -c "import pydantic; print(pydantic.VERSION)"` → `2.12.5`; `uv run python -c "import fastapi; print(fastapi.__version__)"` → `0.128.7`; `uv run python -c "import sqlite3; print(sqlite3.sqlite_version)"` → `3.50.4`
- Direct `field_validator(mode="before")` behavior verification via `uv run python -c "..."` — confirmed strip+upper+regex rejects `"1X"`, accepts `"BRK.B"`, normalizes `"  aapl  "` → `"AAPL"`
- `.planning/phases/04-watchlist-api/04-CONTEXT.md` — all locked decisions D-01 through D-13
- `.planning/phases/03-portfolio-trading-api/03-CONTEXT.md` — sibling pattern reference (D-01, D-02, D-03)
- `.planning/REQUIREMENTS.md` — WATCH-01, WATCH-02, WATCH-03
- `.planning/ROADMAP.md:74-82` — Phase 4 Success Criteria
- `.planning/codebase/CONVENTIONS.md` — `from __future__ import annotations`, `%`-style logging, factory routers, `Optional[X]` prohibition

### Secondary (MEDIUM confidence)

- Python 3.14 `sqlite3` module docs (stdlib) — `ON CONFLICT DO NOTHING`, `RETURNING`, `cursor.rowcount` semantics
- Pydantic 2.12 documentation — `field_validator` modes and `ConfigDict`

### Tertiary (LOW confidence)

None. All decisions are grounded in the existing codebase or in locally-verified library behavior.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dependency is already installed and in use in Phase 1-3.
- Architecture: HIGH — direct clone of Phase 3's `app/portfolio/` sub-package; every integration point (lifespan, source interface, cache) is unchanged from Phase 3.
- Pitfalls: HIGH — seven pitfalls identified, each traceable to either a specific codebase reference (e.g., `PriceUpdate.direction` vocabulary, `stream.py:83` cache-not-filter) or a locally-verified library behavior (Pydantic v2 `mode="before"`).
- Validation Architecture: HIGH — 19 test cases enumerated, each mapped to a specific requirement or design decision.

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (30 days — stable: FastAPI / Pydantic / SQLite / project conventions are unlikely to shift in this window; trigger re-research if Phase 3's `app/portfolio/` pattern is refactored or if Pydantic v3 ships)
