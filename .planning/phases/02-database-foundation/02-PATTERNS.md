# Phase 2: Database Foundation - Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 11 (7 created, 3 modified, 1 test package marker)
**Analogs found:** 11 / 11 (all files have an exact analog under `app/market/` or `tests/market/`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/db/__init__.py` | package-init (public surface) | re-export | `backend/app/market/__init__.py` | exact |
| `backend/app/db/connection.py` | utility (resource lifecycle) | file-I/O | `backend/app/market/factory.py` + `backend/app/market/cache.py` | role-match |
| `backend/app/db/schema.py` | config (module-level constants) | static data | `backend/app/market/seed_prices.py` | exact |
| `backend/app/db/seed.py` | utility (idempotent data init) | CRUD (insert-only) | `backend/app/market/cache.py` (state-init style) + `backend/app/market/seed_prices.py` (source data) | role-match |
| `backend/app/lifespan.py` (MODIFIED) | lifecycle (FastAPI lifespan) | event-driven (startup/shutdown) | **itself** — extend the existing Phase 1 pattern | exact (in-place extension) |
| `backend/market_data_demo.py` (MODIFIED, one line) | demo script | n/a (cosmetic refactor D-06) | **itself** — drop local `TICKERS`, use `list(SEED_PRICES.keys())` | exact (in-place) |
| `backend/tests/conftest.py` (MODIFIED) | test fixture | fixture provisioning | **itself** (existing `event_loop_policy` fixture) | exact (in-place extension) |
| `backend/tests/db/__init__.py` | test-package-init | marker | `backend/tests/market/__init__.py` | exact |
| `backend/tests/db/test_schema.py` | test (unit) | sync sqlite3 assertions | `backend/tests/market/test_cache.py` | role-match (class-grouped unit style) |
| `backend/tests/db/test_seed.py` | test (unit) | sync sqlite3 assertions | `backend/tests/market/test_cache.py` | role-match |
| `backend/tests/db/test_persistence.py` | test (integration) | file-I/O (open/close/re-open) | `backend/tests/market/test_factory.py` | role-match (uses `patch.dict(os.environ, ...)`) |
| `backend/tests/test_lifespan.py` (MODIFIED) | test (integration, async lifespan) | event-driven | **itself** — extend existing `TestLifespan` class | exact (in-place extension) |

---

## Pattern Assignments

### `backend/app/db/__init__.py` (package-init, re-export)

**Analog:** `backend/app/market/__init__.py` (full file, 24 lines)

**Docstring + re-export pattern** (`backend/app/market/__init__.py:1-23`):
```python
"""Market data subsystem for FinAlly.

Public API:
    PriceUpdate         - Immutable price snapshot dataclass
    PriceCache          - Thread-safe in-memory price store
    MarketDataSource    - Abstract interface for data providers
    create_market_data_source - Factory that selects simulator or Massive
    create_stream_router - FastAPI router factory for SSE endpoint
"""

from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import PriceUpdate
from .stream import create_stream_router

__all__ = [
    "PriceUpdate",
    "PriceCache",
    "MarketDataSource",
    "create_market_data_source",
    "create_stream_router",
]
```

**Copy this template verbatim.** For `app/db/__init__.py`:
- Module docstring: one-line summary + "Public API:" bulleted listing.
- Relative imports (`from .connection import open_database`, `from .seed import ...`).
- Explicit `__all__` list for downstream `from app.db import ...` ergonomics (matches `backend/CLAUDE.md` "Market Data API" surface rule).
- No `from __future__ import annotations` in `__init__.py` — the market one does not use it.

---

### `backend/app/db/connection.py` (utility, file-I/O)

**Analog:** `backend/app/market/factory.py` (full file, 32 lines) — same "module-level function that returns a constructed resource" shape.

**Imports + logger pattern** (`backend/app/market/factory.py:1-13`):
```python
"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)
```

**Copy:**
- Module one-line docstring.
- `from __future__ import annotations` as line 3.
- `logger = logging.getLogger(__name__)` at module level — every non-trivial module in the codebase does this (see CONVENTIONS.md "Logging" and `backend/app/market/cache.py`, `backend/app/market/factory.py`, `backend/app/market/simulator.py`).

**Factory function docstring + log pattern** (`backend/app/market/factory.py:16-31`):
```python
def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
```

**Adapt for `open_database(path: str) -> sqlite3.Connection`:**
- Same function shape: docstring explaining behavior + lifecycle.
- `%`-style log call at info level (`logger.info("DB opened at %s", path)`) — CONVENTIONS.md explicitly bans f-strings in logging.
- **No try/except** around `sqlite3.connect` or `mkdir` — CONVENTIONS.md "narrow exception handling" + CONTEXT.md Claude's Discretion "corrupt DB should fail loud". Same as `factory.py` which does zero defensive wrapping.

**Parent-dir + connect pattern (new, from RESEARCH.md §"Connection module"):**
```python
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

---

### `backend/app/db/schema.py` (config, static data)

**Analog:** `backend/app/market/seed_prices.py` (full file, 47 lines) — the canonical "module-level constants, inspectable at import" reference (CONTEXT.md Claude's Discretion explicitly calls this out as the style consistency target).

**Module docstring + typed constant pattern** (`backend/app/market/seed_prices.py:1-15`):
```python
"""Seed prices and per-ticker parameters for the market simulator."""

# Realistic starting prices for the default watchlist (as of project creation)
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
}
```

**Copy this shape for `schema.py`:**
- One-line module docstring at top.
- A short, purposeful inline comment above each constant (pattern `# Realistic starting prices...` maps to `# users_profile table` etc.).
- Module-level typed constants — `SEED_PRICES: dict[str, float]` → `USERS_PROFILE: str`, and the final tuple:
  ```python
  SCHEMA_STATEMENTS: tuple[str, ...] = (USERS_PROFILE, WATCHLIST, POSITIONS, TRADES, PORTFOLIO_SNAPSHOTS, CHAT_MESSAGES)
  ```
- **No `from __future__ import annotations`** is required for `str` / `tuple[str, ...]` at Python 3.12+, but `seed_prices.py` omits it too — keep it omitted for style consistency with its analog (this is the one module in `app/market/` that does NOT have the future import; schema.py will mirror that).

**Note:** RESEARCH.md §"Schema DDL" shows the exact SQL strings — copy those verbatim into this module.

---

### `backend/app/db/seed.py` (utility, insert-only CRUD)

**Analog:** `backend/app/market/cache.py` (for "small stateful utility with docstring + imports pattern") AND `backend/app/market/factory.py` (for env-reading + logging style). `seed.py` imports from `seed_prices.py` — same cross-module-constant pattern as `simulator.py → seed_prices`.

**Imports + docstring pattern** (`backend/app/market/cache.py:1-9`):
```python
"""Thread-safe in-memory price cache."""

from __future__ import annotations

import time
from threading import Lock

from .models import PriceUpdate
```

**Adapt for `seed.py`:**
- Module docstring: `"""Idempotent seed for users_profile + 10-ticker default watchlist."""`.
- `from __future__ import annotations`.
- Stdlib imports first (`import logging`, `import sqlite3`, `import uuid`, `from datetime import UTC, datetime`), then intra-package (`from app.db.schema import SCHEMA_STATEMENTS`), then cross-package (`from app.market.seed_prices import SEED_PRICES` — D-04 canonical source of truth).

**Logger pattern** — mirror `factory.py:13` (`logger = logging.getLogger(__name__)` at module scope).

**Function docstring + commit pattern** (from RESEARCH.md §"Seed code"):
```python
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

**No try/except around `conn.execute`** — matches CONVENTIONS.md "narrow exception handling only at boundaries" and the zero-defensive-code style of `cache.py` / `factory.py`.

---

### `backend/app/lifespan.py` (MODIFIED — in-place extension)

**Analog:** Itself — Phase 1's lifespan is the template. Phase 2 adds three blocks around the existing code.

**Existing imports block to extend** (`backend/app/lifespan.py:1-14`):
```python
"""FastAPI lifespan: PriceCache + market data source startup/shutdown."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .market import PriceCache, create_market_data_source, create_stream_router
from .market.seed_prices import SEED_PRICES

logger = logging.getLogger(__name__)
```

**Edits to make:**
1. Update module docstring → `"""FastAPI lifespan: DB + PriceCache + market data source startup/shutdown."""`.
2. Add new import line: `from .db import get_watchlist_tickers, init_database, open_database, seed_defaults`.
3. Remove `from .market.seed_prices import SEED_PRICES` (no longer needed — watchlist comes from DB now per D-05).

**Existing startup block — add DB init BEFORE `cache = PriceCache()`** (`backend/app/lifespan.py:31-40`):
```python
    if not os.environ.get("OPENROUTER_API_KEY"):
        logger.warning(
            "OPENROUTER_API_KEY not set; chat endpoint will fail in Phase 5"
        )

    cache = PriceCache()
    source = create_market_data_source(cache)

    tickers = list(SEED_PRICES.keys())   # LINE 39 — REPLACE in Phase 2
    await source.start(tickers)
```

**Replacement pattern (new, from RESEARCH.md §"Lifespan ordering"):**
```python
    db_path = os.environ.get("DB_PATH", "db/finally.db")   # D-07
    conn = open_database(db_path)                          # D-01 / D-09
    init_database(conn)                                    # idempotent CREATE TABLE IF NOT EXISTS
    seed_defaults(conn)                                    # idempotent INSERT OR IGNORE

    cache = PriceCache()
    source = create_market_data_source(cache)

    tickers = get_watchlist_tickers(conn)                  # D-05 — replaces SEED_PRICES.keys()
    await source.start(tickers)
```

**Existing `app.state` + router pattern — extend** (`backend/app/lifespan.py:42-44`):
```python
    app.state.price_cache = cache
    app.state.market_source = source
    app.include_router(create_stream_router(cache))
```

**Add one line ABOVE the existing block:**
```python
    app.state.db = conn                                    # NEW
    app.state.price_cache = cache
    app.state.market_source = source
    app.include_router(create_stream_router(cache))
```

**Existing log line to extend** (`backend/app/lifespan.py:46-50`):
```python
    logger.info(
        "App started: %d tickers, source=%s",
        len(tickers),
        type(source).__name__,
    )
```

**Extend with `db=...`:**
```python
    logger.info(
        "App started: db=%s tickers=%d source=%s",
        db_path, len(tickers), type(source).__name__,
    )
```

**Existing shutdown pattern — extend** (`backend/app/lifespan.py:51-55`):
```python
    try:
        yield
    finally:
        await source.stop()
        logger.info("App stopped")
```

**Add `conn.close()` in `finally`:**
```python
    try:
        yield
    finally:
        await source.stop()
        conn.close()                                       # NEW
        logger.info("App stopped")
```

**Ordering between `source.stop()` and `conn.close()`:** neither awaits the other; RESEARCH.md §"Ordering rationale" #7 confirms order does not matter. Keep `source.stop()` first to preserve the Phase 1 call position.

---

### `backend/market_data_demo.py` (MODIFIED, D-06 cosmetic refactor)

**Analog:** Itself — existing lines 22-30 are the target.

**Existing import + TICKERS constant to edit** (`backend/market_data_demo.py:22-30`):
```python
from app.market.cache import PriceCache
from app.market.seed_prices import SEED_PRICES
from app.market.simulator import SimulatorDataSource

# Sparkline characters, low to high
SPARK_CHARS = "▁▂▃▄▅▆▇█"

# Ordered ticker list matching the default watchlist
TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
```

**Replacement:**
```python
# Ordered ticker list matching the default watchlist (source of truth: SEED_PRICES)
TICKERS = list(SEED_PRICES.keys())
```

**Why this is safe:** `SEED_PRICES` is already imported at line 23. All downstream uses (`TICKERS` iterated at lines 75, 181, 213, 222, 243) operate on any `list[str]`. Python 3.7+ guarantees `dict` iteration order is insertion order, so `list(SEED_PRICES.keys())` produces the same ordered list.

---

### `backend/tests/conftest.py` (MODIFIED — add `db_path` fixture)

**Analog:** Itself. Existing fixture sets the template.

**Existing fixture pattern** (`backend/tests/conftest.py:1-11`):
```python
"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def event_loop_policy():
    """Use the default event loop policy for all async tests."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()
```

**Add (new, from RESEARCH.md §"Test fixture sketch"):**
```python
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

**Placement:** immediately after `event_loop_policy`. Copy the existing fixture's docstring conventions (one-line summary, second paragraph with usage hint).

---

### `backend/tests/db/__init__.py` (test-package marker)

**Analog:** `backend/tests/market/__init__.py` (1 line):
```python
"""Tests for market data subsystem."""
```

**Copy verbatim with domain swap:**
```python
"""Tests for DB persistence subsystem."""
```

---

### `backend/tests/db/test_schema.py` (test, unit)

**Analog:** `backend/tests/market/test_cache.py` (class-grouped unit tests, direct-use of target class, no fixtures, pure sync).

**Imports + class header pattern** (`backend/tests/market/test_cache.py:1-7`):
```python
"""Tests for PriceCache."""

from app.market.cache import PriceCache


class TestPriceCache:
    """Unit tests for the PriceCache."""

    def test_update_and_get(self):
        """Test updating and getting a price."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.ticker == "AAPL"
```

**Adapt for schema tests:**
- Module docstring: `"""Tests for SQLite schema DDL."""`.
- Imports: `import sqlite3`, then `from app.db import init_database`.
- **Class name `TestSchema`** with brief class docstring.
- Methods named per RESEARCH.md Test Map:
  - `test_all_six_tables_created`
  - `test_unique_constraints_declared`
  - `test_user_id_defaults_to_default`
- Each test: `conn = sqlite3.connect(":memory:")`, call `init_database(conn)`, assert on `sqlite_master` / `pragma_table_info` / insertion behavior.
- **No try/except, no fixtures** — mirror the `test_cache.py` "construct-assert" shape.

---

### `backend/tests/db/test_seed.py` (test, unit)

**Analog:** `backend/tests/market/test_cache.py` (same class-grouped style).

**Structure to copy:**
```python
"""Tests for default seed: users_profile + 10-ticker watchlist."""

import sqlite3

from app.db import init_database, seed_defaults
from app.market.seed_prices import SEED_PRICES


class TestSeed:
    """Unit tests for seed_defaults (DB-02)."""

    def test_fresh_db_gets_seeded(self):
        """Fresh DB + seed_defaults produces 1 users_profile + 10 watchlist rows."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_database(conn)
        seed_defaults(conn)
        assert conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0] == 10
```

**Class + method names to implement (from RESEARCH.md Test Map):**
- `TestSeed.test_fresh_db_gets_seeded`
- `TestSeed.test_reseed_is_noop` (call `seed_defaults` twice, assert counts unchanged)
- `TestSeed.test_watchlist_matches_seed_prices_keys` (`assert set(rows) == set(SEED_PRICES)`)
- `TestSeed.test_cash_balance_defaults_to_10000` (verify `users_profile.cash_balance == 10000.0`)

**Import pattern:** `from app.db import ...` (via public surface) — matches `backend/CLAUDE.md` "Use these imports" rule.

---

### `backend/tests/db/test_persistence.py` (test, integration)

**Analog:** `backend/tests/market/test_factory.py` (uses `patch.dict(os.environ, ...)`) + the `tmp_path` pattern introduced in the new `db_path` conftest fixture.

**Imports pattern** (`backend/tests/market/test_factory.py:1-9`):
```python
"""Tests for market data source factory."""

import os
from unittest.mock import patch

from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.massive_client import MassiveDataSource
from app.market.simulator import SimulatorDataSource
```

**Adapt for persistence:**
```python
"""Tests for persistence — data survives open/close/re-open (DB-03)."""

import sqlite3

from app.db import init_database, open_database, seed_defaults


class TestPersistence:
    """Integration tests for the DB-03 persistence contract."""

    def test_data_survives_reopen(self, tmp_path):
        """Open → seed → close → re-open same path → rows present."""
        path = tmp_path / "finally.db"

        conn1 = open_database(str(path))
        init_database(conn1)
        seed_defaults(conn1)
        conn1.close()

        conn2 = open_database(str(path))
        user_count = conn2.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        wl_count = conn2.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        conn2.close()

        assert user_count == 1
        assert wl_count == 10
```

**Uses `tmp_path` directly** (pytest built-in, not the new `db_path` fixture) because this test bypasses `lifespan` and env-var resolution — it exercises `open_database(str(path))` directly.

---

### `backend/tests/test_lifespan.py` (MODIFIED — add Phase 2 assertions)

**Analog:** Itself. Existing `TestLifespan` class at lines 27-98 is the template.

**Existing `_build_app` helper — reuse verbatim** (`backend/tests/test_lifespan.py:17-23`):
```python
def _build_app() -> FastAPI:
    """Build a fresh FastAPI app bound to the production lifespan.

    A fresh app per test ensures no state bleeds between cases (PriceCache,
    market source, included routers all live on app.state / app.router).
    """
    return FastAPI(lifespan=lifespan)
```

**No changes to the helper.** Every new test just calls it.

**Existing test pattern — copy this shape for new tests** (`backend/tests/test_lifespan.py:31-44`):
```python
async def test_attaches_price_cache_to_app_state(self):
    """Entering the lifespan attaches a PriceCache to app.state.price_cache."""
    app = _build_app()
    with patch.dict(os.environ, {}, clear=True):
        async with LifespanManager(app):
            assert isinstance(app.state.price_cache, PriceCache)

async def test_attaches_market_source_to_app_state(self):
    """Entering the lifespan attaches a started MarketDataSource to app.state."""
    app = _build_app()
    with patch.dict(os.environ, {}, clear=True):
        async with LifespanManager(app):
            assert isinstance(app.state.market_source, MarketDataSource)
            assert set(app.state.market_source.get_tickers()) == set(SEED_PRICES)
```

**Key observations for Phase 2 edits:**
1. Every test uses `with patch.dict(os.environ, {}, clear=True)` — this **wipes** `DB_PATH` too. Phase 2 tests MUST inject `DB_PATH` AFTER clearing. RESEARCH.md §"Note on `patch.dict` + `monkeypatch.setenv` interaction" flags this: `monkeypatch.setenv` runs inside the test function body but outside the `with patch.dict(...)` context — the clear wipes it. **Fix:** either inject `DB_PATH` explicitly inside the `patch.dict` dict, or make `db_path` a class-level `autouse` fixture that runs AFTER env clearing (needs careful ordering). RESEARCH.md recommendation: **add `db_path` as a class-level autouse fixture**.

2. **Existing Phase 1 tests will break** once Phase 2 lands (they call lifespan which now opens `db/finally.db`). All Phase 1 tests need the `db_path` fixture added. This is mentioned explicitly in RESEARCH.md §"Test fixture sketch" note.

**New tests to add (RESEARCH.md Test Map + §"Test fixture sketch"):**
```python
async def test_attaches_db_to_app_state(self, db_path):
    """lifespan attaches the sqlite3.Connection to app.state.db and it is queryable."""
    app = _build_app()
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app):
            conn = app.state.db
            row = conn.execute(
                "SELECT cash_balance FROM users_profile WHERE id = 'default'"
            ).fetchone()
            assert row["cash_balance"] == 10000.0

async def test_tickers_come_from_db_watchlist(self, db_path):
    """source.start(tickers) is driven by the DB watchlist, not SEED_PRICES directly (D-05)."""
    app = _build_app()
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app):
            tickers = app.state.market_source.get_tickers()
    assert set(tickers) == set(SEED_PRICES)

async def test_second_startup_is_no_op(self, db_path):
    """Restarting the lifespan against the same DB_PATH adds no duplicate rows."""
    app1 = _build_app()
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app1):
            pass
    app2 = _build_app()
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app2):
            conn = app2.state.db
            user_count = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
            wl_count = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
    assert user_count == 1
    assert wl_count == 10
```

**Note on the existing tests:** The cleanest approach (RESEARCH.md recommendation) is to convert `db_path` into an autouse fixture scoped to `TestLifespan` so every test — existing Phase 1 and new Phase 2 — gets a throwaway DB. Planner makes the final call.

---

## Shared Patterns

### Module-level `from __future__ import annotations`
**Source:** Applied in every `app/market/*.py` module except `seed_prices.py` and `__init__.py`.
**Apply to:** `backend/app/db/connection.py`, `backend/app/db/seed.py`.
**Skip:** `backend/app/db/__init__.py`, `backend/app/db/schema.py` (matches `app/market/seed_prices.py` — pure-constants module has no forward refs).

Reference: `backend/app/market/cache.py:3`, `backend/app/market/factory.py:3`, `backend/app/market/interface.py:3`.

### Logger pattern (`%`-style, no f-strings)
**Source:** `backend/app/market/factory.py:13, 27, 30`
**Apply to:** `backend/app/db/connection.py`, `backend/app/db/seed.py`, modified `backend/app/lifespan.py`.

```python
logger = logging.getLogger(__name__)
# ... later ...
logger.info("DB opened at %s", path)
```

CONVENTIONS.md explicitly bans f-strings in logging calls. CLAUDE.md "No emojis in code or in print statements or logging" applies too.

### No defensive try/except around DB ops
**Source:** `backend/app/market/factory.py` (zero try/except), `backend/app/market/cache.py` (zero try/except in CRUD).
**Apply to:** all of `app/db/*` and the lifespan edits.
**Exception:** None in Phase 2. CONTEXT.md Claude's Discretion: "A corrupt / unreadable DB file should fail loud, not get silently re-seeded."

Contrast reference: `backend/app/market/massive_client.py:94-121` DOES use narrow `try/except Exception` + log — but only because it crosses a network boundary. DB ops are local stdlib calls; no boundary to guard.

### Public surface via `__init__.py`
**Source:** `backend/app/market/__init__.py:11-23` (re-exports via relative imports + `__all__`).
**Apply to:** `backend/app/db/__init__.py` — re-export `open_database`, `init_database`, `seed_defaults`, `get_watchlist_tickers`, `DEFAULT_CASH_BALANCE`, `DEFAULT_USER_ID`.
**Enforced by:** `backend/CLAUDE.md` "Market Data API ... Use these imports" rule; planner extends same doc after Phase 2 lands.

### Test class grouping + method docstrings
**Source:** `backend/tests/market/test_cache.py:6-80`, `backend/tests/market/test_factory.py:12-80`, `backend/tests/test_lifespan.py:26-98`.
**Apply to:** `backend/tests/db/test_schema.py`, `backend/tests/db/test_seed.py`, `backend/tests/db/test_persistence.py`.

Shape:
```python
class TestSchema:
    """Unit tests for the SQLite schema DDL (DB-01)."""

    def test_all_six_tables_created(self):
        """init_database creates all six PLAN.md §7 tables."""
        # one behavior per method
```

### `patch.dict(os.environ, {...}, clear=True)` for env isolation
**Source:** Every test in `backend/tests/test_lifespan.py` and `backend/tests/market/test_factory.py`.
**Apply to:** any new lifespan test that reads `DB_PATH` or other env vars. Inject `DB_PATH` inside the dict (not via monkeypatch alone) because `clear=True` wipes everything:

```python
with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
    async with LifespanManager(app):
        ...
```

### Idempotent mkdir (`exist_ok=True`)
**Source:** Stdlib idiom; new pattern introduced in Phase 2 per D-09.
**Apply to:** `backend/app/db/connection.py::open_database`.
```python
Path(path).parent.mkdir(parents=True, exist_ok=True)
```
No `try/except FileExistsError`, no `if not exists` branch — one call, race-safe.

### Module docstrings: one-line summary
**Source:** Every module in `backend/app/market/` (`cache.py:1`, `factory.py:1`, `interface.py:1`, `models.py:1`, `stream.py:1`, `seed_prices.py:1`).
**Apply to:** every new module (`app/db/*`, `tests/db/*`).

One-liners observed:
- `"""Thread-safe in-memory price cache."""`
- `"""Factory for creating market data sources."""`
- `"""Abstract interface for market data sources."""`
- `"""Seed prices and per-ticker parameters for the market simulator."""`

Mirror for Phase 2:
- `"""SQLite schema for FinAlly — six tables per planning/PLAN.md §7."""`
- `"""SQLite connection lifecycle for FinAlly."""`
- `"""Idempotent seed for users_profile + 10-ticker default watchlist."""`

---

## No Analog Found

Every Phase 2 file has a strong analog. No items in this section.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| _(none)_ | | | |

---

## Metadata

**Analog search scope:**
- `backend/app/market/` — every `.py` reviewed (cache.py, factory.py, interface.py, seed_prices.py, __init__.py, simulator.py, massive_client.py, models.py, stream.py)
- `backend/app/lifespan.py` — full file (56 lines)
- `backend/market_data_demo.py` — full file (273 lines, focused on lines 22-30)
- `backend/tests/conftest.py` — full file (11 lines)
- `backend/tests/test_lifespan.py` — full file (99 lines)
- `backend/tests/market/` — `__init__.py`, `test_cache.py`, `test_factory.py` (class-grouped unit-test style)
- `backend/CLAUDE.md` — public-surface convention

**Files scanned:** 17
**Pattern extraction date:** 2026-04-20
