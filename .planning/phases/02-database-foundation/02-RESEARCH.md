# Phase 2: Database Foundation - Research

**Researched:** 2026-04-20
**Domain:** Python stdlib `sqlite3`, FastAPI `lifespan` persistence wiring, idempotent DDL + seed
**Confidence:** HIGH

## Summary

Phase 2 turns the Phase 1 app shell into a persistent application: the same `lifespan` that
already builds the `PriceCache` and starts the market data source will now, before doing any of
that, open a single long-lived `sqlite3.Connection`, create the six tables from `planning/PLAN.md`
§7 if they don't exist, seed the `users_profile` row and the 10-ticker `watchlist` from
`SEED_PRICES.keys()`, then query that `watchlist` and pass the ticker list into `source.start(...)`
in place of Phase 1's stopgap `list(SEED_PRICES.keys())` call at `backend/app/lifespan.py:39`.

CONTEXT.md locks virtually every load-bearing design decision (D-01..D-09). What the planner
actually needs is: the exact SQL DDL strings, the exact call order inside `lifespan.py`, the
exact signatures of the new `app.db` functions, a test-fixture pattern that plugs into the Phase
1 `_build_app()` helper, and a short list of landmines. This document is that -- not a tour of
sqlite3.

**Primary recommendation:** Create a small `backend/app/db/` sub-package mirroring `backend/app/market/`:
`schema.py` (module-level SQL string constants), `seed.py` (idempotent seed calls), `connection.py`
(`open_database(path) -> sqlite3.Connection`), and `__init__.py` re-exporting a small public
surface (`open_database`, `init_database`, `seed_defaults`). Extend `lifespan.py` to call the
three in that order before `PriceCache()`, and swap the `source.start()` ticker argument to come
from a new `get_watchlist_tickers(conn)` read. Everything else — transactions, row factories,
PRAGMAs — follows the CONTEXT.md defaults.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Connection strategy**
- **D-01:** One long-lived `sqlite3.Connection` opened during `lifespan` startup and attached
  to `app.state.db`. Closed in the `finally:` branch. Opened with `check_same_thread=False`.
  Rejected: open-per-call helper, FastAPI `Depends(get_db)` yield.
- **D-02:** `connection.row_factory = sqlite3.Row` for dict-like row access. Dataclass row
  mappers deferred.
- **D-03:** Default manual-commit mode (stdlib sqlite3 default `isolation_level`, NOT
  autocommit). Every write path calls `conn.commit()` explicitly.

**Default seed — single source of truth**
- **D-04:** DB seeder imports `SEED_PRICES` from `backend/app/market/seed_prices.py` and inserts
  `list(SEED_PRICES.keys())` into `watchlist`. No new constants.
- **D-05:** After `init_database()` + `seed_defaults()` run, `lifespan` queries `watchlist` and
  passes that list to `source.start(tickers)`. Replaces Phase 1 line 39.
- **D-06:** `backend/market_data_demo.py` is refactored to reuse `list(SEED_PRICES.keys())`
  instead of its own `TICKERS` list.

**DB path configuration**
- **D-07:** `os.environ.get("DB_PATH", "db/finally.db")` read in `lifespan` startup.
- **D-08:** `DB_PATH` is documented in the eventual `.env.example` (Phase 9 / OPS-04).
- **D-09:** Before `sqlite3.connect(DB_PATH)`, ensure parent dir exists via
  `Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)`.

### Claude's Discretion
- **DB module layout:** single `backend/app/db/` sub-package (matches `backend/app/market/`) —
  Recommended default.
- **Schema definition style:** Python string constants in `app/db/schema.py` — Recommended
  default, consistent with `seed_prices.py`.
- **Idempotent DDL + seed:** `CREATE TABLE IF NOT EXISTS` + either `INSERT OR IGNORE` or a
  pre-SELECT-COUNT guard — planner picks.
- **PRAGMAs:** `PRAGMA foreign_keys = ON` only if FKs are declared; WAL is a stretch.
- **Test isolation:** conftest fixture that sets `DB_PATH` to `tmp_path / "test.db"` or a
  parameter on a `_build_app`-style helper.
- **Lifespan ordering:** Open DB → `init_database()` → `seed_defaults()` → construct
  `PriceCache` → query watchlist → `create_market_data_source` → `source.start(tickers)` →
  mount SSE router.
- **Error handling:** CONVENTIONS.md narrow exception handling. Don't wrap every DB call. A
  corrupt DB file should fail loud, not get silently re-seeded.

### Deferred Ideas (OUT OF SCOPE)
- WAL journal mode (revisit for multi-user).
- Dataclass row mappers (`Position`, `Trade`, `WatchlistEntry`) — Phase 3+ introduces them.
- Schema migrations — project constraint explicitly forbids them.
- Full PRAGMA tuning pass (`journal_mode`, `synchronous`, `cache_size`).
- `backend/db/` SQL-file split from PLAN.md §4 — Phase 2 uses Python string constants.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | SQLite schema for `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages` with `user_id` defaulting to `"default"` and unique constraints per `planning/PLAN.md` §7 | §"Schema DDL" below — six exact `CREATE TABLE IF NOT EXISTS` statements, column types, `DEFAULT "default"`, `UNIQUE(user_id, ticker)` where required, `NULL`-able `actions` on `chat_messages`. |
| DB-02 | Lazy init on startup — creates tables and seeds default user (`cash_balance=10000.0`) plus the 10 default watchlist tickers when the DB is empty | §"Idempotent seed patterns" + §"Lifespan ordering" — `init_database(conn)` runs every startup (cheap, idempotent); `seed_defaults(conn)` uses `INSERT OR IGNORE` keyed on `users_profile.id` and `watchlist(user_id, ticker)` so re-starts are no-ops. |
| DB-03 | SQLite file at `db/finally.db` persists across container restarts via a Docker named volume | §"Persistence testing" — runtime behavior is governed by Docker volume mount (Phase 9); Phase 2 proves persistence at the code level via a `tmp_path`-based test that starts+stops the lifespan twice against the same file and verifies seed data survives. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

The three CLAUDE.md files in scope (`~/.claude/CLAUDE.md`, `./CLAUDE.md`, `backend/CLAUDE.md`)
produce the following directives the planner must honor in every plan:

- Stdlib `sqlite3` only. No ORM. No migrations. (Project `CLAUDE.md` + PLAN.md §7.)
- `uv` for Python: `uv run ...`, `uv add ...`. Never `python3 ...` or `pip install ...`.
- Short modules, short functions. `from __future__ import annotations` at top of every new
  module. `logger = logging.getLogger(__name__)`, `%`-style formatting, never f-strings in
  logging.
- Narrow exception handling only at boundaries. No defensive try/except around DB ops. Fail
  loud on corrupt DB.
- No emojis anywhere (code, logs, commits, docstrings).
- Public surface re-exported via `__init__.py` — consumers import `from app.db import ...`,
  not `from app.db.schema import ...`. Mirrors the `app.market` rule in `backend/CLAUDE.md`.
- "PROVE THE PROBLEM FIRST — don't guess." For Phase 2 this means tests assert observable
  facts (row counts, column values), not just that code ran without raising.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema DDL execution (idempotent) | Backend / app/db/ | — | Pure SQL; no HTTP, no async. |
| Seed data insertion | Backend / app/db/ | Backend / app/market/ | `seed.py` reads `SEED_PRICES` keys from `app/market/seed_prices.py` — D-04's single source of truth. |
| Connection lifecycle | Backend / app/lifespan.py | Backend / app/db/ | `lifespan` owns `open → init → seed → close`; `app/db/connection.py` provides the primitive. |
| DB path resolution | Backend / app/lifespan.py | — | Reads `DB_PATH` env var like Phase 1 reads `MASSIVE_API_KEY`. |
| Parent directory creation | Backend / app/lifespan.py | — | `Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)` before `sqlite3.connect`. |
| Watchlist read for ticker set | Backend / app/lifespan.py | Backend / app/db/ | `get_watchlist_tickers(conn)` returns `list[str]` consumed by `source.start(...)`. |
| DB accessor stored on `app.state.db` | Backend / app/lifespan.py | — | Mirrors `app.state.price_cache` and `app.state.market_source` from Phase 1 D-02. |
| Test isolation via `tmp_path` | Backend / tests/ | — | Conftest fixture overrides `DB_PATH`; `_build_app()` helper identical to Phase 1 pattern. |

Tier integrity check: this phase is entirely backend / persistence. No API tier, no frontend,
no external services. All file changes land in `backend/`.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` (stdlib) | Python 3.12 built-in (ships SQLite ≥ 3.37) | Schema creation, connection, queries | Project constraint (`planning/PLAN.md` §3): "SQLite over Postgres ... self-contained, zero config." No migration tool. No ORM. [VERIFIED: PLAN.md §3 + CONTEXT.md D-01] |
| `pathlib.Path` (stdlib) | built-in | Parent directory creation | `mkdir(parents=True, exist_ok=True)` is the idiomatic idempotent-mkdir on Python. [VERIFIED: CONTEXT.md D-09] |
| `os.environ` (stdlib) | built-in | `DB_PATH` env var read | Mirrors Phase 1's `MASSIVE_API_KEY` pattern. `python-dotenv` already loads `.env` at `backend/app/main.py:16` before `FastAPI(lifespan=lifespan)` is constructed. [VERIFIED: backend/app/main.py:7,16] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-asyncio` | `>=0.24.0` (already pinned) | Async lifespan tests | Already configured: `asyncio_mode = "auto"` in `pyproject.toml:38`. Same as Phase 1. |
| `asgi-lifespan` | `>=2.1.0` (already pinned) | Drive `lifespan` in tests without uvicorn | Already used by `tests/test_lifespan.py:8`. The `async with LifespanManager(app):` pattern directly exercises `init_database` + `seed_defaults` + watchlist read. |

### Installation

No new runtime dependencies. `sqlite3` is stdlib. The Phase 1 `dev` extras (`pytest`,
`pytest-asyncio`, `asgi-lifespan`, `httpx`) cover Phase 2 tests. Therefore:

```bash
# No uv add needed.
```

**Version verification:** stdlib `sqlite3` on the machine used during research reports
`sqlite_version = 3.50.4`, `threadsafety = 3` (SQLITE_THREADSAFE=1 serialized mode), confirmed
by `uv run --extra dev python -c "import sqlite3; print(sqlite3.sqlite_version, sqlite3.threadsafety)"`.
`threadsafety == 3` is load-bearing for D-01's `check_same_thread=False` — see §"Common Pitfalls".
[VERIFIED: local `uv run` 2026-04-20]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `sqlite3` | `aiosqlite` (async driver) | Rejected by project constraint ("stdlib `sqlite3` only"). stdlib is synchronous; but calls are O(ms) and do not block the event loop meaningfully at single-user scale. Revisit if/when hot-path handlers measurably block. |
| stdlib `sqlite3` | SQLAlchemy Core / ORM | Rejected — "no ORM" per project constraint. A six-table single-user schema does not earn the abstraction. |
| Python string DDL | Raw `.sql` files under `backend/db/` | PLAN.md §4 mentions `backend/db/`; CONTEXT.md Claude's Discretion picks the stdlib-style Python constants. Deferred — revisit if schema grows complex. |

## System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        FastAPI lifespan startup                              │
│                                                                              │
│  [env]                                                                       │
│  DB_PATH  ──►  Path(DB_PATH).parent.mkdir(exist_ok=True)   (D-09)            │
│                                                                              │
│  SEED_PRICES (app.market.seed_prices)                                        │
│     │                                                                        │
│     │                  ┌──────────────────────┐                              │
│     ▼                  │ app/db/connection.py │                              │
│     │              ◄──►│ open_database(path)  │  ────► sqlite3.Connection    │
│     │                  │  check_same_thread=  │           │                  │
│     │                  │     False            │           │                  │
│     │                  │  row_factory = Row   │           │                  │
│     │                  └──────────────────────┘           │                  │
│     │                                                     │                  │
│     │                  ┌──────────────────────┐           │                  │
│     │                  │ app/db/schema.py     │           ▼                  │
│     │                  │ SCHEMA_STATEMENTS[]  │   init_database(conn)        │
│     │                  └──────────────────────┘   (CREATE TABLE IF NOT       │
│     │                                              EXISTS x6)                │
│     │                                                     │                  │
│     │                  ┌──────────────────────┐           ▼                  │
│     └───────────────►  │ app/db/seed.py       │   seed_defaults(conn)        │
│                        │ seed_defaults(conn)  │   (INSERT OR IGNORE          │
│                        │  - users_profile row │    users_profile +           │
│                        │  - watchlist rows    │    SEED_PRICES.keys())       │
│                        └──────────────────────┘           │                  │
│                                                           ▼                  │
│                        get_watchlist_tickers(conn) ──► list[str]             │
│                                                           │                  │
│                                                           ▼                  │
│                        PriceCache()                                          │
│                        create_market_data_source(cache)                      │
│                        await source.start(tickers)   ◄── from DB, not        │
│                                                          SEED_PRICES (D-05)  │
│                        app.state.db = conn                                   │
│                        app.state.price_cache = cache                         │
│                        app.state.market_source = source                      │
│                        app.include_router(create_stream_router(cache))       │
│                                    │                                         │
│                                    ▼                                         │
│                                  yield                                       │
│                                    │                                         │
│                              (request cycle)                                 │
│                                    │                                         │
│                                    ▼                                         │
│                             finally:                                         │
│                               await source.stop()                            │
│                               conn.close()          ◄── NEW in Phase 2       │
└──────────────────────────────────────────────────────────────────────────────┘

[volume mount — Phase 9]
  host `db/`  ─────►  container `/app/db`  ─────►  `DB_PATH=/app/db/finally.db`
  Same file survives `docker stop` + `docker run` cycles.
```

## Recommended Project Structure

```
backend/
├── app/
│   ├── __init__.py          # Unchanged (one-line docstring).
│   ├── main.py              # Unchanged (no DB logic here; .env already loads).
│   ├── lifespan.py          # EDITED: open DB, init, seed, query watchlist, attach to app.state, close on exit.
│   ├── db/                  # NEW sub-package, mirrors app/market/ shape.
│   │   ├── __init__.py      # Public re-exports: open_database, init_database, seed_defaults, get_watchlist_tickers.
│   │   ├── connection.py    # open_database(path) -> sqlite3.Connection.
│   │   ├── schema.py        # SCHEMA_STATEMENTS: tuple[str, ...] with the six DDL strings.
│   │   └── seed.py          # seed_defaults(conn), get_watchlist_tickers(conn), DEFAULT_CASH_BALANCE constant.
│   └── market/              # Unchanged. seed_prices.py is the source of truth for watchlist tickers (D-04).
├── market_data_demo.py      # EDITED: TICKERS = list(SEED_PRICES.keys())  (D-06).
└── tests/
    ├── conftest.py          # EDITED: add db_path fixture (tmp_path + monkeypatch DB_PATH).
    ├── test_lifespan.py     # EDITED: add DB-related assertions inside async with LifespanManager.
    ├── test_main.py         # Unchanged.
    ├── market/              # Unchanged.
    └── db/                  # NEW test package.
        ├── __init__.py
        ├── test_schema.py   # init_database is idempotent, produces all 6 tables with correct columns/uniques.
        ├── test_seed.py     # seed_defaults produces 1 users_profile row + 10 watchlist rows; rerunning is no-op.
        └── test_persistence.py  # Open → seed → close → re-open same path → rows present (DB-03 proxy).
```

## Schema DDL (canonical translation from PLAN.md §7)

Place the six statements in `app/db/schema.py` as module-level constants and iterate over them
in `init_database(conn)`. Each is `CREATE TABLE IF NOT EXISTS` so every startup is safe.

```python
# backend/app/db/schema.py
"""SQLite schema for FinAlly — six tables per planning/PLAN.md §7."""

from __future__ import annotations

USERS_PROFILE = """
CREATE TABLE IF NOT EXISTS users_profile (
    id           TEXT PRIMARY KEY DEFAULT 'default',
    cash_balance REAL NOT NULL    DEFAULT 10000.0,
    created_at   TEXT NOT NULL
)
"""

WATCHLIST = """
CREATE TABLE IF NOT EXISTS watchlist (
    id       TEXT PRIMARY KEY,
    user_id  TEXT NOT NULL DEFAULT 'default',
    ticker   TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
)
"""

POSITIONS = """
CREATE TABLE IF NOT EXISTS positions (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    ticker     TEXT NOT NULL,
    quantity   REAL NOT NULL,
    avg_cost   REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
)
"""

TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL DEFAULT 'default',
    ticker      TEXT NOT NULL,
    side        TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity    REAL NOT NULL,
    price       REAL NOT NULL,
    executed_at TEXT NOT NULL
)
"""

PORTFOLIO_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
)
"""

CHAT_MESSAGES = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    actions    TEXT,           -- JSON string; NULL for user turns and action-less assistant turns
    created_at TEXT NOT NULL
)
"""

SCHEMA_STATEMENTS: tuple[str, ...] = (
    USERS_PROFILE,
    WATCHLIST,
    POSITIONS,
    TRADES,
    PORTFOLIO_SNAPSHOTS,
    CHAT_MESSAGES,
)
```

**Translation notes from PLAN.md §7:**

- `DEFAULT 'default'` on every `user_id` column is verbatim PLAN.md.
- Every `*_at` / `created_at` / `executed_at` / `added_at` / `updated_at` / `recorded_at` is
  `TEXT NOT NULL` holding ISO-8601. PLAN.md describes them as "ISO timestamp"; we commit to
  application-produced `datetime.now(UTC).isoformat()` in Phase 3 handlers. [CITED: PLAN.md §7]
- `CHECK (side IN ('buy', 'sell'))` is a low-cost integrity guard; PLAN.md describes the values
  but doesn't formally constrain them. Adding the CHECK costs nothing and closes a foot-gun.
  If the planner prefers strict PLAN.md fidelity, drop the CHECK — it's not a DB-01 requirement.
  [ASSUMED]
- Same for `CHECK (role IN ('user', 'assistant'))` on `chat_messages.role`.
- `chat_messages.actions` is nullable per PLAN.md §7 wording: "null for user messages and for
  assistant messages with no executed actions". [CITED: PLAN.md §7]
- **No foreign keys** are declared. PLAN.md does not specify any, and introducing them would
  force an insert-ordering contract on Phases 3–5. Therefore `PRAGMA foreign_keys = ON` is
  **not** required — recommend omitting it until a real FK constraint is added. [ASSUMED, but
  consistent with CONTEXT.md's Claude's Discretion PRAGMA note.]
- `users_profile.id` has a `DEFAULT 'default'` but the seeder still passes it explicitly for
  clarity — see §"Seed code" below.

## Connection module

```python
# backend/app/db/connection.py
"""SQLite connection lifecycle for FinAlly."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def open_database(path: str) -> sqlite3.Connection:
    """Open a long-lived SQLite connection at `path`.

    Creates parent directory if needed. Returns a connection with sqlite3.Row
    as the row factory and check_same_thread=False (D-01, D-02). Manual-commit
    isolation mode is left at the stdlib default (D-03).
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)  # D-09
    conn = sqlite3.connect(path, check_same_thread=False)  # D-01
    conn.row_factory = sqlite3.Row                          # D-02
    logger.info("DB opened at %s", path)
    return conn
```

## Seed code

```python
# backend/app/db/seed.py
"""Idempotent seed for users_profile + 10-ticker default watchlist."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import UTC, datetime

from app.db.schema import SCHEMA_STATEMENTS
from app.market.seed_prices import SEED_PRICES  # D-04: single source of truth

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0


def init_database(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist. Idempotent on every startup."""
    for ddl in SCHEMA_STATEMENTS:
        conn.execute(ddl)
    conn.commit()


def seed_defaults(conn: sqlite3.Connection) -> None:
    """Insert the default user row and 10-ticker watchlist if not already present.

    Uses INSERT OR IGNORE keyed on users_profile.id and watchlist(user_id, ticker)
    so a re-run after restart is a no-op — satisfies Success Criterion #3.
    """
    now = datetime.now(UTC).isoformat()

    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) "
        "VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )

    for ticker in SEED_PRICES:  # D-04: no second list of tickers anywhere
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) "
            "VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now),
        )

    conn.commit()


def get_watchlist_tickers(conn: sqlite3.Connection) -> list[str]:
    """Return watchlist tickers for the default user — used by lifespan to drive
    source.start(tickers). D-05."""
    rows = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, ticker",
        (DEFAULT_USER_ID,),
    ).fetchall()
    return [row["ticker"] for row in rows]
```

**Why `INSERT OR IGNORE` over a pre-`SELECT COUNT` guard:**
1. Atomic at the SQL layer — no TOCTOU between the guard and the insert.
2. Shorter code, no branch, no logging asymmetry.
3. Works cleanly for the watchlist case where some tickers may exist and others don't (e.g.,
   after Phase 4's add/remove ships, a restart should re-add any missing SEED_PRICES tickers
   without touching existing user edits — actually no, that's wrong: once Phase 4 is live, the
   watchlist is user-owned and we should NOT re-seed on subsequent boots. See §"Open Questions"
   item 1 — planner to confirm boundary.)

[VERIFIED: SQLite docs — `INSERT OR IGNORE` skips rows whose insertion would violate a
uniqueness constraint, leaves existing rows untouched. https://www.sqlite.org/lang_insert.html]

## Public surface — `app/db/__init__.py`

```python
# backend/app/db/__init__.py
"""SQLite persistence subsystem for FinAlly.

Public API:
    open_database           - Open a long-lived sqlite3.Connection.
    init_database           - Run CREATE TABLE IF NOT EXISTS for all six tables.
    seed_defaults           - Insert default user + 10-ticker watchlist (idempotent).
    get_watchlist_tickers   - Return the default user's watchlist ticker list.
"""

from .connection import open_database
from .seed import DEFAULT_CASH_BALANCE, DEFAULT_USER_ID, get_watchlist_tickers, init_database, seed_defaults

__all__ = [
    "open_database",
    "init_database",
    "seed_defaults",
    "get_watchlist_tickers",
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_USER_ID",
]
```

Downstream phases import with `from app.db import open_database, init_database, ...`.
Matches the `app.market` rule in `backend/CLAUDE.md`.

## Lifespan ordering — exact edits to `backend/app/lifespan.py`

Current state (verified at `backend/app/lifespan.py:1-56`):

```python
async def lifespan(app: FastAPI):
    if not os.environ.get("OPENROUTER_API_KEY"):
        logger.warning("OPENROUTER_API_KEY not set; chat endpoint will fail in Phase 5")

    cache = PriceCache()
    source = create_market_data_source(cache)

    tickers = list(SEED_PRICES.keys())       # LINE 39 — replace in Phase 2
    await source.start(tickers)

    app.state.price_cache = cache
    app.state.market_source = source
    app.include_router(create_stream_router(cache))

    logger.info("App started: %d tickers, source=%s", len(tickers), type(source).__name__)
    try:
        yield
    finally:
        await source.stop()                  # Phase 2 adds conn.close() alongside this
        logger.info("App stopped")
```

Target state (Phase 2):

```python
"""FastAPI lifespan: DB + PriceCache + market data source startup/shutdown."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import get_watchlist_tickers, init_database, open_database, seed_defaults
from .market import PriceCache, create_market_data_source, create_stream_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open DB → init → seed → build PriceCache → start market source → mount SSE."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        logger.warning("OPENROUTER_API_KEY not set; chat endpoint will fail in Phase 5")

    db_path = os.environ.get("DB_PATH", "db/finally.db")   # D-07
    conn = open_database(db_path)                          # D-01 / D-09
    init_database(conn)                                    # idempotent CREATE TABLE IF NOT EXISTS
    seed_defaults(conn)                                    # idempotent INSERT OR IGNORE

    cache = PriceCache()
    source = create_market_data_source(cache)

    tickers = get_watchlist_tickers(conn)                  # D-05 — replaces SEED_PRICES.keys()
    await source.start(tickers)

    app.state.db = conn                                    # NEW
    app.state.price_cache = cache
    app.state.market_source = source
    app.include_router(create_stream_router(cache))

    logger.info(
        "App started: db=%s tickers=%d source=%s",
        db_path, len(tickers), type(source).__name__,
    )
    try:
        yield
    finally:
        await source.stop()
        conn.close()                                       # NEW
        logger.info("App stopped")
```

**Ordering rationale (matches CONTEXT.md Claude's Discretion):**

1. **`OPENROUTER_API_KEY` warning first** — existing Phase 1 behavior, preserved.
2. **Open DB BEFORE PriceCache** — if DB open fails, fail loud immediately without the overhead
   of starting the simulator's asyncio task.
3. **`init_database` then `seed_defaults`** — seeding depends on tables existing.
4. **Construct `PriceCache` AFTER DB seeded** — no ordering dependency today, but keeps the
   shape "DB first, then app state, then background tasks" which reads cleanly.
5. **`get_watchlist_tickers(conn)` BEFORE `source.start(...)`** — this is the core D-05 swap.
   On fresh boot the query returns the 10 SEED_PRICES tickers (just seeded); on subsequent
   boots it returns whatever the user's edits produced.
6. **SSE router included LAST** — matches Phase 1 D-04 ("SSE router mounted during startup
   before `yield`"). Phase 2 doesn't change the router or the contract.
7. **`conn.close()` in `finally`** — alongside `source.stop()`. Order between them doesn't
   matter; neither awaits the other.

## Idempotent DDL + seed patterns

### Pattern 1: `CREATE TABLE IF NOT EXISTS` inside `init_database`

**What:** Execute every DDL statement in `SCHEMA_STATEMENTS` on every startup.
**When to use:** Always — the `IF NOT EXISTS` clause makes this a no-op after the first run.
**Example:** See `init_database` above.

**Why not guard with `SELECT name FROM sqlite_master WHERE type='table'`:** The DDL is already
idempotent at the SQL layer. A pre-check adds a round-trip and a branch with zero semantic
benefit.

[VERIFIED: https://www.sqlite.org/lang_createtable.html — "If a table with the same name
already exists... CREATE TABLE IF NOT EXISTS commands have no effect."]

### Pattern 2: `INSERT OR IGNORE` for seed rows

**What:** Seed rows with `INSERT OR IGNORE` so existing rows are left untouched.
**When to use:** For the `users_profile` row (keyed on `id = 'default'`) and each `watchlist`
ticker (keyed on the `UNIQUE(user_id, ticker)` constraint).
**Example:** See `seed_defaults` above.

**Why this and not a `SELECT COUNT(*) = 0` guard:** See rationale above — atomic, shorter,
no TOCTOU. The Claude's Discretion in CONTEXT.md explicitly leaves this choice open;
`INSERT OR IGNORE` is the conventional answer.

**Landmine — once Phase 4 ships:** See §"Open Questions" #1.

### Anti-Patterns to Avoid

- **Wrapping every DB call in try/except.** Violates CONVENTIONS.md. A failed `open_database`
  call should propagate — the process cannot serve requests without a DB, so uvicorn should
  exit with a stack trace, not log-and-swallow.
- **Implicit autocommit via `isolation_level=None`.** Breaks D-03. Leave `isolation_level` at
  the stdlib default (empty-string "deferred") and call `conn.commit()` from `init_database`
  and `seed_defaults`.
- **Sharing a Cursor across threads/handlers.** `sqlite3.threadsafety == 3` allows sharing the
  Connection, but each call site should use a fresh cursor (`conn.execute(...)` gives you one
  implicitly). Keeping cursors long-lived invites "cursor still in use" errors. [VERIFIED: Python
  docs https://docs.python.org/3/library/sqlite3.html#module-functions under "threadsafety"]
- **Persisting `session_start_price` anywhere.** See CONCERNS.md §"Architectural Risks" #6.
  The schema has no such column; Phase 2 must not add one.
- **Re-using the `users_profile.id = 'default'` row to identify a "schema initialized" marker.**
  PLAN.md §7 treats `users_profile` as user state, not metadata. Don't overload it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Does the DB need seeding?" | A custom `SELECT COUNT(*) FROM users_profile; if 0: ...` guard function with manual branching | `INSERT OR IGNORE` with a known primary key or unique constraint | Atomic at the SQL layer; no TOCTOU; no branching code to test. |
| Idempotent mkdir for the DB parent dir | `if not path.parent.exists(): path.parent.mkdir()` two-step | `Path(db_path).parent.mkdir(parents=True, exist_ok=True)` | One call, race-safe, zero branches. (D-09.) |
| Opening the DB lazily on first request | A `get_db()` dependency that caches a connection in a module-level dict keyed by event loop | One `open_database` call in `lifespan` startup, single `conn` on `app.state.db` | D-01 locks the long-lived-connection pattern. Lazy opening re-introduces the thread-affinity problem that `check_same_thread=False` is meant to avoid. |
| ISO timestamps | Manual `strftime` dance | `datetime.now(UTC).isoformat()` | One line, correct, timezone-aware (Python 3.12+ `UTC` alias). |
| UUIDs for row ids | Your own counter / hash | `str(uuid.uuid4())` | stdlib, unique across processes/volumes, no collision risk. |
| A migration framework | Alembic / yoyo / custom version table | Nothing — project constraint explicitly says "no migrations" in PLAN.md §7's lead-in wording and CONTEXT.md §Deferred | Schema changes in v1 ship by editing `SCHEMA_STATEMENTS` and re-running on fresh boots. v2 worries about v2. |

**Key insight:** At this scale every line of defensive code is a liability. `CREATE TABLE IF
NOT EXISTS` + `INSERT OR IGNORE` + `mkdir(exist_ok=True)` collapse three "does this exist?
if not, create" patterns into zero branches.

## Common Pitfalls

### Pitfall 1: `check_same_thread=False` used with threads that weren't expected
**What goes wrong:** Two threads share a connection, both start a transaction with implicit
`BEGIN`, and the second call gets `OperationalError: database is locked`.
**Why it happens:** stdlib sqlite3 uses a module-level serializer with `threadsafety == 3`, but
at the SQLite C layer each connection has one transaction slot. `check_same_thread=False`
disables Python's affinity check — it does NOT add any cross-thread transaction coordination.
**How to avoid:** For Phase 2 the ONLY writes are inside `init_database` and `seed_defaults`,
both called synchronously from the event-loop thread before any handler runs. There is no
concurrent writer yet. Phase 3 introduces trade writes — plan that serialization when it lands.
[CITED: https://docs.python.org/3/library/sqlite3.html#sqlite3.threadsafety]
**Warning signs:** `OperationalError: database is locked` under concurrency.

### Pitfall 2: UNIQUE constraint collisions on re-seed
**What goes wrong:** Plain `INSERT` after the first boot raises `IntegrityError: UNIQUE
constraint failed: watchlist.user_id, watchlist.ticker`, crashing the process.
**Why it happens:** The `users_profile` PRIMARY KEY and `watchlist(user_id, ticker)` UNIQUE
constraints fire on every duplicate seed attempt.
**How to avoid:** Use `INSERT OR IGNORE` (as shown in `seed_defaults` above). Confirm with a
test that re-runs `seed_defaults` twice and asserts row counts are unchanged.
**Warning signs:** First restart of a seeded DB raises `IntegrityError`.

### Pitfall 3: Parent-dir race on first boot
**What goes wrong:** `sqlite3.connect` fails with `OperationalError: unable to open database
file` because `db/` doesn't exist on a fresh clone or a freshly created named volume.
**Why it happens:** Docker named volumes mount as empty directories; a fresh `git clone` on a
developer machine has no `db/` dir.
**How to avoid:** D-09's `Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)` runs
BEFORE `sqlite3.connect`. Idempotent — no race against a dir that already exists.
**Warning signs:** "unable to open database file" on fresh clone or first container start.

### Pitfall 4: `sqlite3.Row` is not JSON-serializable
**What goes wrong:** A handler returns a `Row` object from a query and FastAPI raises a
serialization error.
**Why it happens:** `sqlite3.Row` is a tuple-like object, not a dict. FastAPI's default
`jsonable_encoder` doesn't know how to serialize it.
**How to avoid:** Convert at the handler boundary with `dict(row)` or an explicit
`{"ticker": row["ticker"], ...}`. Phase 2 doesn't add any handlers, but Phase 3/4 will — flag
this for their research. `get_watchlist_tickers` already does the right thing: it returns
`list[str]`, not `list[Row]`.
**Warning signs:** TypeError during `JSONResponse` construction in Phase 3+.

### Pitfall 5: Silent re-seed after a user edits the watchlist
**What goes wrong:** Once Phase 4 (Watchlist API) ships, a user deletes `NFLX` from the
watchlist; then the container restarts; on boot, `seed_defaults` re-inserts `NFLX` because
`INSERT OR IGNORE` only ignores existing rows, it doesn't know "the user deliberately removed
this".
**Why it happens:** The seed is a "make sure the 10 defaults are present" contract. Phase 4
changes the watchlist to "user-owned".
**How to avoid:** This is the Open Question below. Cleanest answer: in Phase 4 the seed logic
changes to "only seed if the watchlist table is EMPTY" — a single `SELECT COUNT(*) FROM
watchlist WHERE user_id = 'default'` guard. Phase 2 can either (a) ship with `INSERT OR IGNORE`
today and let Phase 4 plan the behavior change, or (b) ship with a COUNT-based guard today
so the contract is stable across Phase 4. **Recommendation: ship (b).** Zero cost today,
prevents silent re-seed regressions forever.
**Warning signs:** "Why did NFLX come back?" after Phase 4 ships.

### Pitfall 6: `isolation_level=None` accidentally set by copying stale docs
**What goes wrong:** Connection is in autocommit mode; D-03's "every write path calls
`conn.commit()` explicitly" still works but the commit is a no-op. Once Phase 3 writes trades
and snapshots as a unit, the autocommit makes the pair non-atomic.
**Why it happens:** Many Python sqlite3 examples on the web set `isolation_level=None` to
"avoid surprises". This is the wrong advice for our needs.
**How to avoid:** In `open_database`, DO NOT set `isolation_level`. The stdlib default
(`isolation_level=""`, deferred) is correct. [CITED:
https://docs.python.org/3/library/sqlite3.html#sqlite3-controlling-transactions]
**Warning signs:** Phase 3 discovers a half-completed trade after a crash.

### Pitfall 7: `PRAGMA foreign_keys = ON` forgotten on each connection
**What goes wrong:** FK constraints are declared but not enforced — the PRAGMA is per-connection
and defaults to OFF.
**Why it happens:** SQLite historical default.
**How to avoid:** **Not applicable to Phase 2** — no FKs are declared (see §"Schema DDL"
translation notes). If FKs are added later, set the PRAGMA inside `open_database` and add a
test that asserts `PRAGMA foreign_keys` returns 1.
[CITED: https://www.sqlite.org/foreignkeys.html §2]

### Pitfall 8: `sqlite3.Row` pickling for multiprocessing
**What goes wrong:** A `Row` can't be pickled in older Pythons; worker processes in a
multi-process server (gunicorn) crash.
**Why it happens:** `Row` is a C-implemented type bound to its originating cursor.
**How to avoid:** Not relevant to Phase 2 — the project runs a single uvicorn worker on port
8000. Flagged here because the question will come up if anyone ever adds `--workers 4` to the
uvicorn CMD. Each worker would need its own `open_database` call (i.e., `app.state.db` is
per-process), which is fine if our DB opens are idempotent.

## Code Examples

### Seeding once; restart is a no-op

```python
# First boot: inserts 1 user + 10 tickers.
conn = open_database("db/finally.db")
init_database(conn)
seed_defaults(conn)
assert conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0] == 1
assert conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0] == 10
conn.close()

# Second boot: no-op, same counts.
conn = open_database("db/finally.db")
init_database(conn)
seed_defaults(conn)
assert conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0] == 1
assert conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0] == 10
conn.close()
```

### Querying watchlist in lifespan

```python
tickers = get_watchlist_tickers(conn)   # ['AAPL', 'GOOGL', ..., 'NFLX']  — order deterministic
await source.start(tickers)             # replaces list(SEED_PRICES.keys())
```

[VERIFIED against current `backend/app/lifespan.py:39` — this is the one line that changes for D-05.]

## Runtime State Inventory

Phase 2 is net-new code (no rename/refactor), but it introduces a new piece of state the app
depends on. For traceability:

| Category | Items | Action Required |
|----------|-------|------------------|
| Stored data | `db/finally.db` (new SQLite file). On fresh volume: seeded with 1 `users_profile` + 10 `watchlist` rows. On existing volume: untouched by re-boot. | Phase 2 creates the schema + seed; Phases 3–5 read/write data. |
| Live service config | None — FinAlly is single-container single-process. | None. |
| OS-registered state | None in Phase 2. Phase 9 adds a Docker named volume `finally-data → /app/db`. | Handled in Phase 9 OPS-01/02. |
| Secrets/env vars | New env var: `DB_PATH` (default `db/finally.db`). No secrets. | Phase 9 OPS-04 adds `DB_PATH` to `.env.example` per D-08. |
| Build artifacts | None. No new binaries, no new installed packages (stdlib only). | None. |

**Nothing found in category:** Live service config, OS-registered state, secrets, build artifacts
— none added in Phase 2. Confirmed by inspection of PLAN.md §7, §11 and Phase 1 code.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` 8.3+ with `pytest-asyncio` 0.24+ (already pinned in `backend/pyproject.toml:17-23`) |
| Config file | `backend/pyproject.toml` — `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| Quick run command | `cd backend && uv run --extra dev pytest tests/db/ -v` |
| Full suite command | `cd backend && uv run --extra dev pytest -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | All six tables exist after `init_database` with correct column names | unit | `uv run --extra dev pytest tests/db/test_schema.py::TestSchema::test_all_six_tables_created -x` | Wave 0 |
| DB-01 | `UNIQUE (user_id, ticker)` on `watchlist` and `positions`; PK on `users_profile.id` | unit | `uv run --extra dev pytest tests/db/test_schema.py::TestSchema::test_unique_constraints_declared -x` | Wave 0 |
| DB-01 | `user_id` columns default to `'default'` when omitted | unit | `uv run --extra dev pytest tests/db/test_schema.py::TestSchema::test_user_id_defaults_to_default -x` | Wave 0 |
| DB-02 | Fresh DB → `init_database` + `seed_defaults` produces 1 `users_profile` (cash=10000.0) + 10 watchlist rows | unit | `uv run --extra dev pytest tests/db/test_seed.py::TestSeed::test_fresh_db_gets_seeded -x` | Wave 0 |
| DB-02 | Re-running `seed_defaults` is a no-op (counts unchanged, no IntegrityError) | unit | `uv run --extra dev pytest tests/db/test_seed.py::TestSeed::test_reseed_is_noop -x` | Wave 0 |
| DB-02 | `seed_defaults` inserts exactly `list(SEED_PRICES.keys())` — no extras, no missing | unit | `uv run --extra dev pytest tests/db/test_seed.py::TestSeed::test_watchlist_matches_seed_prices_keys -x` | Wave 0 |
| DB-03 | Opening → seeding → closing → re-opening the SAME file preserves seed rows | integration | `uv run --extra dev pytest tests/db/test_persistence.py::TestPersistence::test_data_survives_reopen -x` | Wave 0 |
| DB-03 | Two successive `async with LifespanManager(app):` blocks against one `tmp_path` preserve seed rows and do NOT duplicate them | integration | `uv run --extra dev pytest tests/test_lifespan.py::TestLifespan::test_second_startup_is_no_op -x` | Wave 0 (extend existing test_lifespan.py) |
| DB-01/02 | `lifespan` attaches `conn` to `app.state.db` and it is usable for queries | integration | `uv run --extra dev pytest tests/test_lifespan.py::TestLifespan::test_attaches_db_to_app_state -x` | Wave 0 |
| DB-05 implicit | `source.start(tickers)` receives tickers from the DB watchlist, not SEED_PRICES directly | integration | `uv run --extra dev pytest tests/test_lifespan.py::TestLifespan::test_tickers_come_from_db_watchlist -x` | Wave 0 |
| D-06 | `market_data_demo.py` uses `list(SEED_PRICES.keys())` — no local `TICKERS` constant | unit | `uv run --extra dev pytest tests/db/test_demo_refactor.py -x` (or a simple `grep`-style import-level assertion) | Wave 0 (can be a trivial import + attribute check) |

### Sampling Rate
- **Per task commit:** `cd backend && uv run --extra dev pytest tests/db/ -x` (runs the three new
  test files; < 2 seconds locally).
- **Per wave merge:** `cd backend && uv run --extra dev pytest -v` (full suite — 73 inherited
  market tests + 7 Phase 1 tests + new Phase 2 tests; < 15 seconds).
- **Phase gate:** Full suite green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `backend/tests/db/__init__.py` — empty file to mark the package.
- [ ] `backend/tests/db/test_schema.py` — covers DB-01 (tables exist, unique constraints, defaults).
- [ ] `backend/tests/db/test_seed.py` — covers DB-02 (seed content + idempotence).
- [ ] `backend/tests/db/test_persistence.py` — covers DB-03 (`tmp_path` open/close/re-open cycle).
- [ ] `backend/tests/db/test_demo_refactor.py` — covers D-06 (or roll into test_seed.py as a
      one-liner).
- [ ] Extend `backend/tests/conftest.py` with a `db_path` fixture (`monkeypatch.setenv("DB_PATH",
      str(tmp_path / "test.db"))`) reusable by lifespan tests.
- [ ] Extend `backend/tests/test_lifespan.py` with:
  - `test_attaches_db_to_app_state`
  - `test_tickers_come_from_db_watchlist`
  - `test_second_startup_is_no_op`
- Framework install: none needed — `uv sync --extra dev` already pulls `pytest-asyncio`,
  `asgi-lifespan`, `httpx`. Confirmed at `backend/pyproject.toml:17-23`.

### Test fixture sketch (planner reuses in plans)

```python
# backend/tests/conftest.py  — EXTEND, do not replace
import pytest


@pytest.fixture
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Override DB_PATH to a per-test sqlite file under pytest tmp_path.

    Use this fixture in lifespan tests so the lifespan opens a fresh DB
    per test and cleans up automatically when tmp_path is torn down.
    """
    path = tmp_path / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    return path
```

```python
# backend/tests/test_lifespan.py  — new test sketch
@pytest.mark.asyncio
class TestLifespan:
    ...

    async def test_attaches_db_to_app_state(self, db_path):
        app = _build_app()
        with patch.dict(os.environ, {}, clear=True):
            import os as _os
            _os.environ["DB_PATH"] = str(db_path)  # monkeypatch already applied
            async with LifespanManager(app):
                conn = app.state.db
                row = conn.execute(
                    "SELECT cash_balance FROM users_profile WHERE id = 'default'"
                ).fetchone()
                assert row["cash_balance"] == 10000.0

    async def test_tickers_come_from_db_watchlist(self, db_path):
        app = _build_app()
        async with LifespanManager(app):
            tickers = app.state.market_source.get_tickers()
        assert set(tickers) == set(SEED_PRICES)  # on fresh boot, identical

    async def test_second_startup_is_no_op(self, db_path):
        """Restarting the lifespan against the same DB_PATH adds no duplicate rows."""
        app1 = _build_app()
        async with LifespanManager(app1):
            pass
        app2 = _build_app()
        async with LifespanManager(app2):
            conn = app2.state.db
            user_count = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
            wl_count = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        assert user_count == 1
        assert wl_count == 10
```

**Note on `patch.dict` + `monkeypatch.setenv` interaction:** existing Phase 1 tests use
`patch.dict(os.environ, {}, clear=True)` to wipe env. If the planner uses the `db_path` fixture,
that fixture's `monkeypatch.setenv` runs AFTER the patch.dict context manager enters, so the
`DB_PATH` env var is present. Confirm with a trivial first-run before layering more tests on
top. The existing Phase 1 tests don't need `db_path` because they pre-date the DB — but they
WILL start trying to open `db/finally.db` (the hardcoded default) after Phase 2 lands. Planner
must pass `db_path` to all lifespan tests OR move the `os.environ.get("DB_PATH", ...)` default
to a `tmp_path` under pytest. **Recommendation:** add `db_path` as a class-level `autouse`
fixture on `TestLifespan` and `TestSSEStream` so every test gets a throwaway DB automatically.

## Persistence testing (DB-03)

Success Criterion #4 is "data survives container restart on the Docker named volume". We prove
this at two layers:

1. **Code-level (this phase):** `tests/db/test_persistence.py` opens a DB at
   `tmp_path / "finally.db"`, seeds it, closes the connection, opens a fresh connection at the
   same path, and asserts row counts unchanged. This is a faithful proxy for volume mount
   semantics — the volume is just "a path on disk that persists beyond the process lifetime".
2. **Infra-level (Phase 9):** `docker run -v finally-data:/app/db ... finally` followed by
   `docker stop` / `docker rm` / `docker run` again, then curl `/api/portfolio` — proven in
   Phase 10 E2E.

Phase 2 owns layer 1. Layer 2 is Phase 9/10's problem.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `isolation_level=None` "just use autocommit" | Default `isolation_level=""` with explicit `conn.commit()` | Python 3.12 PEP 249 alignment | D-03 — enables future multi-statement transactions (Phase 3). |
| Synchronous `sqlite3` inside `async def` — "needs aiosqlite" | Single-user workload makes sync `sqlite3` fine | N/A — always true at this scale | No change for Phase 2. Revisit when an endpoint measurably blocks. |
| Raw `.sql` file + `executescript` | Python string constants in `schema.py` | Stylistic choice; Claude's Discretion default | Keeps schema inspectable at import, greppable, and ruff-visible. |
| `datetime.utcnow()` | `datetime.now(UTC)` | Deprecated in Python 3.12 — `utcnow` gives a naive datetime | Use `datetime.now(UTC).isoformat()` throughout. [CITED: Python 3.12 changelog] |

**Deprecated/outdated:**
- `datetime.utcnow()` — deprecated in 3.12; use `datetime.now(UTC)`. [CITED:
  https://docs.python.org/3/library/datetime.html#datetime.datetime.utcnow]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Adding `CHECK (side IN ('buy', 'sell'))` / `CHECK (role IN ('user', 'assistant'))` is desirable low-cost hardening not in conflict with DB-01 | Schema DDL translation notes | If planner prefers strict PLAN.md fidelity, drop the CHECKs — no test asserts them. |
| A2 | `PRAGMA foreign_keys = ON` is not needed because no FKs are declared | Common Pitfalls #7 | If planner decides to declare FKs in the DDL (e.g., `positions.user_id REFERENCES users_profile(id)`), they must add the PRAGMA to `open_database`. |
| A3 | Ship with `INSERT OR IGNORE` seed (option a in Pitfall #5), OR a COUNT-based guard (option b). Recommendation is (b) for forward-compatibility, but (a) is also correct per CONTEXT.md's explicit Claude's Discretion wording | Common Pitfalls #5, Open Questions #1 | Once Phase 4 ships, (a) re-inserts user-deleted tickers on every restart. (b) gets the behavior right without any Phase 4 churn. |
| A4 | `datetime.now(UTC).isoformat()` is the right ISO timestamp format for every `*_at` column | Schema translation | PLAN.md only says "ISO timestamp" — any valid ISO 8601 string works. If Phase 3 needs microsecond precision for snapshot ordering, this still provides it. |
| A5 | Ordering the watchlist query `ORDER BY added_at, ticker` gives deterministic results. The seed inserts all 10 tickers with the same `now` timestamp (identical `added_at`), so the tiebreaker on `ticker` matters | get_watchlist_tickers | If ordering turns out to matter (e.g., UI wants stable row order), the tiebreaker is correct. If not, drop the ORDER BY entirely. |

## Open Questions

1. **Seed contract after Phase 4 ships the Watchlist API.**
   - What we know: Phase 2 seeds the 10 SEED_PRICES tickers. Phase 4 will let the user add/remove
     tickers. `INSERT OR IGNORE` on every boot re-seeds any missing defaults — fine at first boot,
     wrong after the user deletes NFLX.
   - What's unclear: Should Phase 2 ship with `INSERT OR IGNORE` (simple, consistent with CONTEXT.md)
     and let Phase 4 revise the seed logic? Or ship with a "seed only if the watchlist is empty"
     guard (forward-compatible, one extra query per boot)?
   - Recommendation: Ship with the COUNT-guard (option b). One `SELECT COUNT(*) FROM watchlist
     WHERE user_id = 'default'` per boot is cheap; the behavior is correct across both phases.
     Planner locks this in the plan. [SURFACE IN DISCUSS-PHASE IF USER CARES.]

2. **`market_data_demo.py` refactor (D-06) — where does the test live?**
   - What we know: D-06 is cosmetic. The demo script is not runtime code. The refactor is a one-line
     change in a non-runtime file.
   - What's unclear: Does the planner write a dedicated test for it, or just verify by inspection?
   - Recommendation: A trivial one-liner test in `tests/db/test_demo_refactor.py` that imports the
     demo's `TICKERS` (or whatever it's renamed to) and asserts `set(market_data_demo.TICKERS) ==
     set(SEED_PRICES)`. Cheap, prevents CONCERNS.md #9 drift from re-emerging. Alternatively, accept
     this as an inspection-level check and skip the test.

3. **`app.state.db` type hint in handlers.**
   - What we know: Phase 2 attaches `conn` to `app.state.db`. Phase 3/4/5 handlers will read it
     via `request.app.state.db`.
   - What's unclear: Should Phase 2 declare a `Protocol` or typed namespace for `app.state` now,
     or let Phase 3 introduce it when it needs `request.app.state.db: sqlite3.Connection`?
   - Recommendation: Defer to Phase 3. Phase 2 adds `app.state.db = conn` without any typing
     scaffolding — consistent with how Phase 1 attaches `price_cache` and `market_source`
     untyped. CONVENTIONS.md says "short modules, short functions" — premature typing scaffolding
     is over-engineering.

## Environment Availability

Phase 2 depends on stdlib only. No external CLIs, runtimes, or services beyond what Phase 1 uses.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | `sqlite3` stdlib, `Path`, `datetime.UTC` | ✓ (Phase 1 confirmed) | 3.12+ per `backend/pyproject.toml:6` | None — project hard constraint. |
| stdlib `sqlite3` | Everything | ✓ | SQLite 3.50.4 on dev machine (SQLite 3.37+ required — no version-specific features used) | None — project hard constraint. |
| `uv` | Run tests, manage deps | ✓ (Phase 1 confirmed) | per `CLAUDE.md` | None. |
| `pytest-asyncio` | Async lifespan tests | ✓ (dev extra) | `>=0.24.0` in `pyproject.toml:19` | None. |
| `asgi-lifespan` | Drive lifespan in tests | ✓ (dev extra) | `>=2.1.0` in `pyproject.toml:23` | None. |
| Write access to `db/finally.db` parent dir | Persistence | ✓ (tests use `tmp_path`; runtime creates with `mkdir`) | — | None. |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

[VERIFIED: `uv run --extra dev python -c "import sqlite3; print(sqlite3.sqlite_version, sqlite3.threadsafety)"`
on 2026-04-20 returned `3.50.4 3`.]

## Sources

### Primary (HIGH confidence)
- `planning/PLAN.md` §7 — Full schema: tables, columns, types, UNIQUE constraints, default seed.
  Canonical specification.
- `planning/PLAN.md` §5 — Environment variables (frames `DB_PATH` addition).
- `planning/PLAN.md` §6 — "Set of tickers tracked by the price cache is the union of all tickers
  in the `watchlist` table" — the D-05 contract.
- `.planning/phases/02-database-foundation/02-CONTEXT.md` — All locked decisions D-01..D-09.
- `.planning/phases/01-app-shell-config/01-CONTEXT.md` — Phase 1 decisions Phase 2 extends.
- `backend/app/lifespan.py:1-56` — Current state Phase 2 modifies.
- `backend/app/main.py:1-26` — `.env` loading at line 16 (unchanged by Phase 2).
- `backend/app/market/seed_prices.py:1-47` — `SEED_PRICES` dict (D-04 source of truth).
- `backend/tests/test_lifespan.py:1-99` — The `_build_app` + `LifespanManager` pattern Phase 2 extends.
- `backend/tests/conftest.py:1-11` — Fixture location.
- `backend/pyproject.toml:1-62` — Pinned deps + pytest config.
- Python stdlib docs: https://docs.python.org/3/library/sqlite3.html — `threadsafety`,
  `check_same_thread`, `isolation_level`, `Row`.
- SQLite docs: https://www.sqlite.org/lang_createtable.html (IF NOT EXISTS),
  https://www.sqlite.org/lang_insert.html (INSERT OR IGNORE),
  https://www.sqlite.org/foreignkeys.html (PRAGMA foreign_keys).

### Secondary (MEDIUM confidence)
- `.planning/codebase/CONVENTIONS.md` — Module structure, logging, async patterns — HIGH actually,
  but derived from the existing codebase, not PLAN.md.
- `.planning/codebase/CONCERNS.md` — §"Architectural Risks" #6 (session_start_price not persisted)
  and Code-Level #9 (drift risk — closed by D-04/D-05/D-06).
- Live verification: `uv run --extra dev python -c "import sqlite3; ..."` on 2026-04-20.

### Tertiary (LOW confidence)
- None. No WebSearch used — the domain is stdlib sqlite3 + a locked-decision CONTEXT.md, so
  the source hierarchy is Python docs + PLAN.md + CONTEXT.md end-to-end.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib-only, versions pinned in `pyproject.toml`, live-verified.
- Architecture: HIGH — CONTEXT.md locks every load-bearing decision; Phase 1 integration is
  literally visible in `backend/app/lifespan.py`.
- Pitfalls: HIGH — pulled from Python stdlib docs + SQLite docs + the code paths that will
  exercise them.
- Assumptions: 5 `[ASSUMED]` items surfaced in the Assumptions Log (CHECK constraints, FK PRAGMA,
  seed-contract strategy, timestamp format, watchlist ordering) — all low-risk, all actionable.
  None require user confirmation before planning.

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (30 days — stdlib sqlite3 doesn't change; only reconsider if the
`planning/PLAN.md` §7 schema changes or CONTEXT.md decisions are revised).
