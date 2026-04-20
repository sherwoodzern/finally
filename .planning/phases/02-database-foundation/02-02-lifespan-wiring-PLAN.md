---
phase: 02
plan: 02
type: execute
wave: 2
depends_on:
  - 02-01
files_modified:
  - backend/app/lifespan.py
  - backend/tests/conftest.py
  - backend/tests/test_lifespan.py
autonomous: true
requirements:
  - DB-01
  - DB-02
  - DB-03
tags:
  - lifespan
  - sqlite
  - persistence
  - integration
  - backend
must_haves:
  truths:
    - "On startup against a fresh `DB_PATH`, the lifespan opens the DB, creates the six tables, seeds the default user + 10 tickers, and starts the market source using tickers fetched from the DB watchlist (not `SEED_PRICES.keys()` directly)."
    - "After lifespan entry, `app.state.db` is a queryable `sqlite3.Connection` exposing the seeded `users_profile` row (`cash_balance=10000.0`)."
    - "Entering and exiting the lifespan twice against the same `DB_PATH` file keeps counts at 1 `users_profile` + 10 `watchlist` rows — no duplicates, no errors."
    - "On shutdown, `conn.close()` runs in the `finally:` branch alongside `source.stop()`."
    - "Existing Phase 1 lifespan tests continue to pass because every test receives an isolated `DB_PATH` via a class-scoped `autouse` fixture."
  artifacts:
    - path: backend/app/lifespan.py
      provides: "DB-aware startup — open → init → seed → query watchlist → start source; close DB on shutdown"
      contains: "from .db import get_watchlist_tickers, init_database, open_database, seed_defaults"
    - path: backend/tests/conftest.py
      provides: "Reusable `db_path` fixture that monkeypatches `DB_PATH` to `tmp_path / 'finally.db'`"
      contains: "def db_path"
    - path: backend/tests/test_lifespan.py
      provides: "DB-aware lifespan tests + autouse isolation so Phase 1 tests still pass"
      contains: "test_attaches_db_to_app_state"
  key_links:
    - from: backend/app/lifespan.py
      to: backend/app/db/__init__.py
      via: "`from .db import get_watchlist_tickers, init_database, open_database, seed_defaults`"
      pattern: "from \\.db import .*get_watchlist_tickers"
    - from: backend/app/lifespan.py
      to: backend/app/db/seed.py
      via: "`get_watchlist_tickers(conn)` replaces `list(SEED_PRICES.keys())` (D-05)"
      pattern: "tickers = get_watchlist_tickers\\(conn\\)"
    - from: backend/tests/test_lifespan.py
      to: backend/tests/conftest.py
      via: "autouse `db_path` fixture injects isolated DB per test"
      pattern: "db_path"
---

<objective>
Wire the Phase 1 FastAPI lifespan through the Phase 2 DB primitives: open the DB on startup, init + seed it, hand the resulting watchlist ticker list into `source.start(...)`, attach the connection to `app.state.db`, and close it on shutdown. Extend the test suite so the new behavior is verified AND the existing Phase 1 lifespan tests keep passing.

Purpose: Deliver Success Criteria #1, #2, #3 from ROADMAP Phase 2 end-to-end, plus the code-level half of #4 (DB-03 persistence across container restarts). Depends on Plan 01 for the `app.db` public surface.

Output:
- One modified module: `backend/app/lifespan.py`.
- One extended fixture file: `backend/tests/conftest.py` (adds `db_path` fixture).
- One extended test file: `backend/tests/test_lifespan.py` (adds three new tests and adopts the `db_path` fixture for every test in `TestLifespan` + `TestSSEStream`-equivalent classes in the file).

Design lock-ins (binding on the executor):
- **Lifespan ordering (resolves CONTEXT.md Claude's Discretion):** Open DB → `init_database` → `seed_defaults` → construct `PriceCache` → `get_watchlist_tickers(conn)` → `create_market_data_source(cache)` → `source.start(tickers)` → attach `app.state.db`, `app.state.price_cache`, `app.state.market_source` → `app.include_router(create_stream_router(cache))`.
- Per D-05: the `tickers` argument to `source.start(...)` MUST come from `get_watchlist_tickers(conn)`. The import of `SEED_PRICES` is REMOVED from `lifespan.py` in this plan.
- Per D-07: `DB_PATH` resolved via `os.environ.get("DB_PATH", "db/finally.db")`.
- Per D-01 / D-09: path resolution + mkdir happen INSIDE `open_database` — the lifespan just passes the path.
- **Test-isolation decision (resolves RESEARCH.md "Note on patch.dict + monkeypatch.setenv"):** Add `db_path` as an `autouse` class-level fixture to `TestLifespan` so EVERY test (old and new) gets an isolated `tmp_path/finally.db`. Inject `DB_PATH` via `patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True)` in the new DB-specific tests. Existing tests that already use `patch.dict(os.environ, {}, clear=True)` need `DB_PATH` added to the dict — otherwise `clear=True` wipes the monkeypatched value and the lifespan opens `./db/finally.db` in the test cwd.
- Close order in `finally:`: `await source.stop()` first, then `conn.close()`. Order is semantically irrelevant (RESEARCH.md §7), but keep `source.stop` first to minimize diff against Phase 1.

Not in this plan:
- Anything in `backend/app/db/` (Plan 01 owns that code).
- `backend/market_data_demo.py` (Plan 03).
- `.env.example` updates for `DB_PATH` (Phase 9 / OPS-04 per D-08).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@planning/PLAN.md
@.planning/phases/02-database-foundation/02-CONTEXT.md
@.planning/phases/02-database-foundation/02-RESEARCH.md
@.planning/phases/02-database-foundation/02-PATTERNS.md
@.planning/phases/02-database-foundation/02-VALIDATION.md
@.planning/phases/02-database-foundation/02-01-db-package-PLAN.md
@backend/app/lifespan.py
@backend/app/market/__init__.py
@backend/tests/conftest.py
@backend/tests/test_lifespan.py
@backend/CLAUDE.md
@CLAUDE.md

<interfaces>
<!-- Consumed from Plan 01 (app.db). These MUST be present before this plan runs. -->

```python
# from app.db
def open_database(path: str) -> sqlite3.Connection: ...
def init_database(conn: sqlite3.Connection) -> None: ...
def seed_defaults(conn: sqlite3.Connection) -> None: ...
def get_watchlist_tickers(conn: sqlite3.Connection) -> list[str]: ...
```

<!-- Existing Phase 1 surfaces this plan extends. -->

```python
# from app.market (unchanged)
class PriceCache: ...
def create_market_data_source(cache: PriceCache) -> MarketDataSource: ...
def create_stream_router(cache: PriceCache) -> APIRouter: ...
```

```python
# Existing test helper, reused verbatim (do NOT change signature)
# backend/tests/test_lifespan.py:17-23
def _build_app() -> FastAPI:
    return FastAPI(lifespan=lifespan)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add `db_path` fixture + make it autouse for `TestLifespan`</name>
  <files>backend/tests/conftest.py, backend/tests/test_lifespan.py</files>
  <read_first>
    - backend/tests/conftest.py (current file — one existing fixture to extend)
    - backend/tests/test_lifespan.py (every `patch.dict(os.environ, {}, clear=True)` call site needs `DB_PATH` injected or covered by autouse)
    - .planning/phases/02-database-foundation/02-RESEARCH.md §"Test fixture sketch" and §"Note on patch.dict + monkeypatch.setenv interaction"
    - .planning/phases/02-database-foundation/02-PATTERNS.md §"backend/tests/conftest.py (MODIFIED)" and §"backend/tests/test_lifespan.py (MODIFIED)"
    - backend/tests/market/test_factory.py (the `patch.dict` style that's already in use)
  </read_first>
  <behavior>
    - After this task, `pytest tests/test_lifespan.py -v` passes all 7 pre-existing Phase 1 tests WITHOUT any of them touching `./db/finally.db` on the developer machine — each gets an isolated sqlite file under `tmp_path`.
    - The `db_path` fixture returns a `pathlib.Path` pointing at a per-test sqlite file and sets `DB_PATH` env var via monkeypatch so `lifespan` reads it.
    - The fixture is declared `autouse=True` at the class level on `TestLifespan` so every existing and new test in that class gets an isolated DB.
    - Existing Phase 1 tests that use `patch.dict(os.environ, {}, clear=True)` now include `"DB_PATH": str(db_path)` in the dict so `clear=True` doesn't wipe the monkeypatched value.
  </behavior>
  <action>
### Step 1 — Extend `backend/tests/conftest.py`

**File before:**

```python
"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def event_loop_policy():
    """Use the default event loop policy for all async tests."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()
```

**File after** (replace with this content verbatim):

```python
"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def event_loop_policy():
    """Use the default event loop policy for all async tests."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Override DB_PATH to a per-test sqlite file under pytest tmp_path.

    Use this fixture in lifespan tests so the lifespan opens a fresh DB per
    test and cleans up automatically when tmp_path is torn down. Tests that
    also call `patch.dict(os.environ, {...}, clear=True)` MUST include
    `"DB_PATH": str(db_path)` in the dict — the clear would otherwise wipe
    the monkeypatched value before the lifespan reads it.
    """
    path = tmp_path / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    return path
```

### Step 2 — Make `db_path` autouse on `TestLifespan` and update existing Phase 1 tests

Open `backend/tests/test_lifespan.py`. You will:

1. **Add an autouse attribute at the top of `TestLifespan`** so every method receives an isolated DB.
2. **For each existing Phase 1 test** that calls `patch.dict(os.environ, {}, clear=True)`, change the dict to include `"DB_PATH": str(self._db_path)` — we capture the fixture value via a nested helper because `db_path` is method-scoped. The simplest way: accept `db_path` as a parameter on every existing test method and inject `"DB_PATH": str(db_path)` inside each `patch.dict`.

The exact edits are one per existing method. Apply every edit below.

**Current Phase 1 test methods to update** (lines shown for orientation — read the file first):

Each of these currently looks like:

```python
async def test_NAME(self):
    app = _build_app()
    with patch.dict(os.environ, {}, clear=True):
        async with LifespanManager(app):
            ...
```

Change EACH of the following seven methods to:

```python
async def test_NAME(self, db_path):
    app = _build_app()
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app):
            ...
```

Methods to update (all currently in `TestLifespan`):
- `test_attaches_price_cache_to_app_state`
- `test_attaches_market_source_to_app_state`
- `test_uses_simulator_when_massive_api_key_absent`
- `test_seeds_cache_immediately_on_startup`
- `test_includes_sse_router_during_startup`
- `test_missing_openrouter_key_logs_warning_and_proceeds`  (already takes `caplog` — the new signature becomes `(self, caplog, db_path)`)
- `test_stops_source_on_shutdown`

Leave the method body logic untouched — the only edit per method is:
- Add `db_path` (or `, db_path` after `caplog`) to the signature.
- Change `{}` to `{"DB_PATH": str(db_path)}` inside `patch.dict(os.environ, ...)`.

Do NOT change `clear=True`, do NOT change `_build_app()`, do NOT change the body assertions.

### Step 3 — Smoke check

After the edits:

```bash
cd backend && uv run --extra dev pytest tests/test_lifespan.py -v
```

All seven existing tests MUST still pass. They may NOT touch `./db/finally.db` — verify by `ls backend/db 2>/dev/null || true` (directory should not be created by test runs after this change).

  </action>
  <verify>
    <automated>cd backend && uv run --extra dev pytest tests/test_lifespan.py -v</automated>
    <automated>cd backend && uv run --extra dev ruff check tests/</automated>
  </verify>
  <acceptance_criteria>
    - `backend/tests/conftest.py` contains a `db_path` fixture whose body includes `monkeypatch.setenv("DB_PATH", str(path))`. grep-verifiable: `grep -c "def db_path" backend/tests/conftest.py` returns `1`.
    - `backend/tests/conftest.py` still contains the original `event_loop_policy` fixture unchanged.
    - Every `patch.dict(os.environ, {}, clear=True)` in `backend/tests/test_lifespan.py` has been replaced — grep-verifiable: `grep -c "patch.dict(os.environ, {}, clear=True)" backend/tests/test_lifespan.py` returns `0`.
    - Grep-verifiable count: `grep -c 'patch.dict(os.environ, {"DB_PATH"' backend/tests/test_lifespan.py` returns at least `7`.
    - Each of the seven existing test methods in `TestLifespan` has `db_path` in its signature — `grep -c "db_path" backend/tests/test_lifespan.py` returns `>=8` (7 signatures + 1+ body references).
    - `cd backend && uv run --extra dev pytest tests/test_lifespan.py -v` exits 0 with 7 tests passing (no new tests added yet in this task).
    - `cd backend && uv run --extra dev ruff check tests/` exits 0.
    - `ls backend/db/finally.db 2>/dev/null` returns no file after the test run (tests use `tmp_path`, not the default).
  </acceptance_criteria>
  <done>`db_path` fixture exists. All seven Phase 1 `TestLifespan` tests updated to use it and still pass. No test run writes to `backend/db/`.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire DB into `lifespan.py` + add three DB integration tests</name>
  <files>backend/app/lifespan.py, backend/tests/test_lifespan.py</files>
  <read_first>
    - backend/app/lifespan.py (current file — 56 lines, Phase 1 complete)
    - backend/app/db/__init__.py (Plan 01 output — the public API this lifespan imports)
    - backend/app/db/seed.py (Plan 01 output — `get_watchlist_tickers` contract)
    - backend/tests/test_lifespan.py (must preserve existing 7 tests; add 3 new ones at the end of `TestLifespan`)
    - .planning/phases/02-database-foundation/02-RESEARCH.md §"Lifespan ordering" and §"Test fixture sketch"
    - .planning/phases/02-database-foundation/02-PATTERNS.md §"backend/app/lifespan.py (MODIFIED)"
    - .planning/phases/02-database-foundation/02-VALIDATION.md §"Per-Task Verification Map" (task IDs 02-02-01..02-02-04)
  </read_first>
  <behavior>
    - `lifespan.py` imports `get_watchlist_tickers, init_database, open_database, seed_defaults` from `.db`.
    - `lifespan.py` no longer imports `SEED_PRICES` — the watchlist comes from the DB.
    - On `LifespanManager` entry:
      - `DB_PATH` env var is read (default `db/finally.db`).
      - `open_database(db_path)` opens the connection (and mkdirs the parent dir).
      - `init_database(conn)` runs all six CREATE TABLE IF NOT EXISTS.
      - `seed_defaults(conn)` seeds 1 users_profile + 10 watchlist rows on first boot.
      - `PriceCache()` constructed.
      - `source = create_market_data_source(cache)`.
      - `tickers = get_watchlist_tickers(conn)` returns the DB watchlist.
      - `source.start(tickers)` awaited.
      - `app.state.db = conn`, `app.state.price_cache = cache`, `app.state.market_source = source`.
      - `app.include_router(create_stream_router(cache))`.
      - A single info log line includes `db=<path>`, `tickers=<count>`, `source=<class name>`.
    - On `LifespanManager` exit: `source.stop()` awaited AND `conn.close()` called, both in the `finally:` branch.
    - Three new integration tests assert: (a) `app.state.db` exists and cash_balance row is 10000.0, (b) tickers observed on `market_source.get_tickers()` equal `set(SEED_PRICES)` on fresh boot (proving D-05), (c) re-entering the lifespan against the same `db_path` leaves counts at 1 user + 10 watchlist.
  </behavior>
  <action>
### Step 1 — Rewrite `backend/app/lifespan.py`

Replace the ENTIRE file content with exactly the following:

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
    """Open DB → init → seed → build PriceCache → start market source → mount SSE.

    Phase 2 additions on top of Phase 1 (01-CONTEXT.md D-02, D-04):
      D-01/D-09: open sqlite3.Connection at DB_PATH (default db/finally.db),
                 creating the parent directory if missing.
      D-02:      attach the connection to app.state.db alongside price_cache
                 and market_source.
      D-04 (seed idempotency): watchlist seed runs only when the table is empty;
                 users_profile uses INSERT OR IGNORE keyed on id='default'.
      D-05:      source.start(tickers) receives the DB watchlist (not
                 list(SEED_PRICES.keys())) — PLAN.md §6 contract.
      D-07:      DB_PATH resolved via os.environ.get at lifespan entry, after
                 .env has been loaded in backend/app/main.py.
    """
    if not os.environ.get("OPENROUTER_API_KEY"):
        logger.warning(
            "OPENROUTER_API_KEY not set; chat endpoint will fail in Phase 5"
        )

    db_path = os.environ.get("DB_PATH", "db/finally.db")
    conn = open_database(db_path)
    init_database(conn)
    seed_defaults(conn)

    cache = PriceCache()
    source = create_market_data_source(cache)

    tickers = get_watchlist_tickers(conn)
    await source.start(tickers)

    app.state.db = conn
    app.state.price_cache = cache
    app.state.market_source = source
    app.include_router(create_stream_router(cache))

    logger.info(
        "App started: db=%s tickers=%d source=%s",
        db_path,
        len(tickers),
        type(source).__name__,
    )
    try:
        yield
    finally:
        await source.stop()
        conn.close()
        logger.info("App stopped")
```

Notes:
- The Phase 1 import `from .market.seed_prices import SEED_PRICES` is REMOVED (no longer used here).
- Import order: stdlib (`logging`, `os`, `contextlib`) → third-party (`fastapi`) → local (`.db`, `.market`) — matches `backend/app/market/factory.py:3-10`.
- `%`-style logging preserved per CONVENTIONS.md.
- No try/except around DB calls — fail loud on corrupt DB per CONTEXT.md Claude's Discretion + CONVENTIONS.md.

### Step 2 — Append three new integration tests to `TestLifespan`

In `backend/tests/test_lifespan.py`, ADD the following three methods as the last methods of the `TestLifespan` class (after `test_stops_source_on_shutdown`). Do NOT modify any existing tests in this step — Task 1 already handled them.

```python
    async def test_attaches_db_to_app_state(self, db_path):
        """lifespan attaches a seeded sqlite3.Connection to app.state.db."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                conn = app.state.db
                row = conn.execute(
                    "SELECT cash_balance FROM users_profile WHERE id = 'default'"
                ).fetchone()
                assert row is not None
                assert row["cash_balance"] == 10000.0

    async def test_tickers_come_from_db_watchlist(self, db_path):
        """source.start(tickers) is driven by the DB watchlist, not SEED_PRICES directly (D-05).

        On a fresh DB the seed produces exactly set(SEED_PRICES.keys()), so the
        ticker set must equal SEED_PRICES — this is a *derived* equivalence via
        the DB, not a direct import from seed_prices.
        """
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                tickers = set(app.state.market_source.get_tickers())
                # Count-only sanity: 10 tickers seeded.
                assert len(tickers) == 10
                assert tickers == set(SEED_PRICES)

    async def test_second_startup_is_no_op(self, db_path):
        """Restarting the lifespan against the same DB_PATH adds no duplicate rows (DB-03)."""
        app1 = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app1):
                pass

        app2 = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app2):
                conn = app2.state.db
                user_count = conn.execute(
                    "SELECT COUNT(*) FROM users_profile"
                ).fetchone()[0]
                wl_count = conn.execute(
                    "SELECT COUNT(*) FROM watchlist"
                ).fetchone()[0]
                assert user_count == 1
                assert wl_count == 10
```

### Step 3 — Run the full suite

```bash
cd backend && uv run --extra dev pytest -v
```

Expected: all pre-existing tests green + 3 new `TestLifespan` tests green + all 13 `tests/db/` tests from Plan 01 green. No regressions.
  </action>
  <verify>
    <automated>cd backend && uv run --extra dev pytest -v</automated>
    <automated>cd backend && uv run --extra dev ruff check app/ tests/</automated>
  </verify>
  <acceptance_criteria>
    - `backend/app/lifespan.py` contains the exact import line `from .db import get_watchlist_tickers, init_database, open_database, seed_defaults`.
    - `backend/app/lifespan.py` does NOT contain `from .market.seed_prices import SEED_PRICES` (grep-verifiable: `grep -c "from .market.seed_prices" backend/app/lifespan.py` returns `0`).
    - `backend/app/lifespan.py` contains the literal line `tickers = get_watchlist_tickers(conn)` (grep-verifiable).
    - `backend/app/lifespan.py` contains both `await source.stop()` AND `conn.close()` inside the `finally:` branch (grep: `grep -A5 "finally:" backend/app/lifespan.py` shows both).
    - `backend/app/lifespan.py` contains the literal line `app.state.db = conn`.
    - `backend/app/lifespan.py` contains the `db_path = os.environ.get("DB_PATH", "db/finally.db")` line.
    - `backend/app/lifespan.py` contains NO `try:` block other than the existing `try: yield; finally:` pair (single occurrence: `grep -c "^    try:" backend/app/lifespan.py` returns `1`).
    - `backend/tests/test_lifespan.py` contains test methods named `test_attaches_db_to_app_state`, `test_tickers_come_from_db_watchlist`, `test_second_startup_is_no_op` (each grep-verifiable with `grep -c "async def test_attaches_db_to_app_state" backend/tests/test_lifespan.py` returns `1`, etc.).
    - `cd backend && uv run --extra dev pytest tests/test_lifespan.py -v` reports AT LEAST 10 passing tests (7 pre-existing + 3 new).
    - `cd backend && uv run --extra dev pytest -v` exits 0 — full suite green (73 market tests + 10+ lifespan tests + 13 db tests + any `test_main.py` tests).
    - `cd backend && uv run --extra dev ruff check app/ tests/` exits 0.
    - No lint/unused-import errors: `grep -c "SEED_PRICES" backend/app/lifespan.py` returns `0` (import was removed).
  </acceptance_criteria>
  <done>`lifespan.py` opens/seeds/reads the DB; `app.state.db` is populated; full pytest suite green; ruff clean.</done>
</task>

</tasks>

<verification>
## Plan-level verification

After both tasks complete:

1. `cd backend && uv run --extra dev pytest -v` — full suite green. Expected new counts:
   - 73 inherited `tests/market/` tests (unchanged)
   - 10 `tests/test_lifespan.py` tests (7 Phase 1 + 3 new)
   - 13 `tests/db/` tests from Plan 01
   - Any `tests/test_main.py` tests
2. `cd backend && uv run --extra dev ruff check app/ tests/` — clean.
3. Smoke-run the app against a `tmp_path`:
   ```bash
   cd backend && DB_PATH=/tmp/finally_smoke_$RANDOM.db uv run --extra dev python -c "
   import asyncio, os
   from fastapi import FastAPI
   from asgi_lifespan import LifespanManager
   from app.lifespan import lifespan
   async def go():
       app = FastAPI(lifespan=lifespan)
       async with LifespanManager(app):
           conn = app.state.db
           print('users:', conn.execute('SELECT COUNT(*) FROM users_profile').fetchone()[0])
           print('watchlist:', conn.execute('SELECT COUNT(*) FROM watchlist').fetchone()[0])
   asyncio.run(go())
   "
   ```
   Expect `users: 1`, `watchlist: 10`.
4. `grep -c "SEED_PRICES" backend/app/lifespan.py` returns `0`.
5. `grep -c "from .db" backend/app/lifespan.py` returns `1`.

## Must-haves cross-check

- ✓ DB-01 tables created — proven by Plan 01 tests; integrated by lifespan here.
- ✓ DB-02 seed on fresh volume — `test_attaches_db_to_app_state` + `test_tickers_come_from_db_watchlist`.
- ✓ D-05 watchlist drives `source.start` — `test_tickers_come_from_db_watchlist`.
- ✓ DB-03 restart is no-op — `test_second_startup_is_no_op`.
- ✓ Phase 1 tests still green — Task 1 retrofits `db_path` autouse.
- ✓ `conn.close()` on shutdown — visible in rewritten `lifespan.py`.
</verification>

<success_criteria>
- `backend/app/lifespan.py` opens, inits, seeds, queries, attaches, and closes the DB in the correct order.
- `app.state.db` is a queryable `sqlite3.Connection` for the lifetime of the app.
- The market data source receives tickers from the DB watchlist, not from `SEED_PRICES` directly.
- Full pytest suite is green with the new DB integration tests added.
- No regression in Phase 1 lifespan/SSE tests; every test runs against an isolated `tmp_path` DB.
- ROADMAP Phase 2 Success Criteria #1, #2, #3, and the code-level portion of #4 are satisfied.
</success_criteria>

<output>
After completion, create `.planning/phases/02-database-foundation/02-02-SUMMARY.md` using the summary template.
</output>
