---
phase: 02
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/db/__init__.py
  - backend/app/db/schema.py
  - backend/app/db/connection.py
  - backend/app/db/seed.py
  - backend/tests/db/__init__.py
  - backend/tests/db/test_schema.py
  - backend/tests/db/test_seed.py
  - backend/tests/db/test_persistence.py
autonomous: true
requirements:
  - DB-01
  - DB-02
  - DB-03
tags:
  - sqlite
  - persistence
  - schema
  - seed
  - backend
must_haves:
  truths:
    - "`init_database(conn)` creates all six PLAN.md §7 tables (`users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`) with the correct columns, types, defaults, and UNIQUE constraints."
    - "`seed_defaults(conn)` on a fresh DB inserts exactly one `users_profile` row (`id='default'`, `cash_balance=10000.0`) and exactly `len(SEED_PRICES)` = 10 `watchlist` rows whose tickers are `set(SEED_PRICES.keys())`."
    - "Calling `init_database` + `seed_defaults` twice produces the same counts as calling them once (no IntegrityError, no duplicates)."
    - "After closing and re-opening the SAME file path, the previously-seeded rows survive (file-based persistence works)."
    - "`get_watchlist_tickers(conn)` returns a `list[str]` of the current watchlist tickers for `user_id='default'`."
  artifacts:
    - path: backend/app/db/__init__.py
      provides: "Public DB API — `open_database`, `init_database`, `seed_defaults`, `get_watchlist_tickers`, `DEFAULT_CASH_BALANCE`, `DEFAULT_USER_ID`"
      contains: "from .connection import open_database"
    - path: backend/app/db/schema.py
      provides: "Six CREATE TABLE IF NOT EXISTS strings + `SCHEMA_STATEMENTS` tuple"
      contains: "SCHEMA_STATEMENTS"
    - path: backend/app/db/connection.py
      provides: "`open_database(path) -> sqlite3.Connection` (mkdir parent, row_factory, check_same_thread=False)"
      contains: "def open_database"
    - path: backend/app/db/seed.py
      provides: "`init_database`, `seed_defaults`, `get_watchlist_tickers`, `DEFAULT_USER_ID`, `DEFAULT_CASH_BALANCE`"
      contains: "def seed_defaults"
    - path: backend/tests/db/test_schema.py
      provides: "DB-01 unit tests — tables exist, UNIQUE constraints, user_id defaults"
      contains: "class TestSchema"
    - path: backend/tests/db/test_seed.py
      provides: "DB-02 unit tests — fresh seed produces expected counts, re-seed is no-op"
      contains: "class TestSeed"
    - path: backend/tests/db/test_persistence.py
      provides: "DB-03 unit-level proxy — open/seed/close/reopen preserves rows"
      contains: "class TestPersistence"
  key_links:
    - from: backend/app/db/seed.py
      to: backend/app/market/seed_prices.py
      via: "`from app.market.seed_prices import SEED_PRICES`"
      pattern: "from app\\.market\\.seed_prices import SEED_PRICES"
    - from: backend/app/db/seed.py
      to: backend/app/db/schema.py
      via: "`from app.db.schema import SCHEMA_STATEMENTS`"
      pattern: "from app\\.db\\.schema import SCHEMA_STATEMENTS"
    - from: backend/app/db/__init__.py
      to: backend/app/db/connection.py
      via: "re-export of `open_database`"
      pattern: "from \\.connection import open_database"
---

<objective>
Create the self-contained `backend/app/db/` sub-package that owns the SQLite schema, connection lifecycle, and idempotent seed. No lifespan wiring in this plan — that happens in Plan 02.

Purpose: Stand up DB-01/DB-02/DB-03 primitives as a unit that can be unit-tested in isolation with `sqlite3.connect(":memory:")` and `tmp_path`, mirroring the `backend/app/market/` pattern (module-level docstrings, re-exports via `__init__.py`, one behavior per test method).

Output:
- Four new modules under `backend/app/db/` with a tiny public surface (per `backend/CLAUDE.md` convention: `from app.db import ...`).
- Three new test modules under `backend/tests/db/` covering schema, seed, and file persistence.

Design lock-ins (binding on the executor):
- Per D-04: `SEED_PRICES` in `backend/app/market/seed_prices.py` is the SOLE source of truth for default watchlist tickers. No new ticker list anywhere in this plan.
- Per D-01/D-02: `open_database` opens with `check_same_thread=False` and `row_factory = sqlite3.Row`.
- Per D-03: do NOT set `isolation_level`. Manual commits via explicit `conn.commit()`.
- Per D-09: `Path(path).parent.mkdir(parents=True, exist_ok=True)` before `sqlite3.connect`.
- **Seed idempotency decision (resolves RESEARCH.md Open Question #1 — option (b)):**
  - `users_profile` seed uses `INSERT OR IGNORE` keyed on the primary key `id='default'`.
  - `watchlist` seed uses a **`COUNT(*)` guard** — only inserts the 10 default tickers when `SELECT COUNT(*) FROM watchlist WHERE user_id = 'default'` returns 0. This prevents silently re-inserting tickers the user has deleted once Phase 4 ships the watchlist API. Documented in the `seed_defaults` docstring.
- `CREATE TABLE IF NOT EXISTS` for every DDL (idempotent per CONTEXT.md Claude's Discretion).
- `PRAGMA foreign_keys = ON` is NOT set — no FKs are declared in PLAN.md §7 (verified in RESEARCH.md A2).
- `CHECK (side IN ('buy','sell'))` on `trades.side` and `CHECK (role IN ('user','assistant'))` on `chat_messages.role` — low-cost hardening per RESEARCH.md A1. Acceptance tests do NOT assert on these CHECKs; they're inside the DDL strings but not a DB-01 contract.

Not in this plan (Plan 02 owns):
- `backend/app/lifespan.py` edits.
- `app.state.db` wiring.
- The `db_path` conftest fixture and lifespan test updates.
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
@backend/app/market/__init__.py
@backend/app/market/seed_prices.py
@backend/app/market/cache.py
@backend/app/market/factory.py
@backend/tests/market/test_cache.py
@backend/tests/market/test_factory.py
@backend/CLAUDE.md
@CLAUDE.md

<interfaces>
<!-- Contracts this plan creates. Plan 02 imports these from `app.db`. -->

From backend/app/db/__init__.py (to be created):
```python
from .connection import open_database
from .seed import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    get_watchlist_tickers,
    init_database,
    seed_defaults,
)

__all__ = [
    "open_database",
    "init_database",
    "seed_defaults",
    "get_watchlist_tickers",
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_USER_ID",
]
```

From backend/app/db/connection.py (to be created):
```python
def open_database(path: str) -> sqlite3.Connection: ...
```

From backend/app/db/schema.py (to be created):
```python
SCHEMA_STATEMENTS: tuple[str, ...]  # six CREATE TABLE IF NOT EXISTS strings
```

From backend/app/db/seed.py (to be created):
```python
DEFAULT_USER_ID: str = "default"
DEFAULT_CASH_BALANCE: float = 10000.0

def init_database(conn: sqlite3.Connection) -> None: ...
def seed_defaults(conn: sqlite3.Connection) -> None: ...
def get_watchlist_tickers(conn: sqlite3.Connection) -> list[str]: ...
```

From backend/app/market/seed_prices.py (already exists, DO NOT MODIFY):
```python
SEED_PRICES: dict[str, float]  # 10 entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create app/db/ sub-package — schema.py + connection.py + seed.py + __init__.py</name>
  <files>backend/app/db/__init__.py, backend/app/db/schema.py, backend/app/db/connection.py, backend/app/db/seed.py</files>
  <read_first>
    - backend/app/market/__init__.py (public-surface re-export pattern to mirror verbatim)
    - backend/app/market/seed_prices.py (module-level constants style for schema.py)
    - backend/app/market/cache.py (short-module + from __future__ + logger pattern)
    - backend/app/market/factory.py (function-with-docstring + `%`-style logging + zero defensive try/except)
    - .planning/phases/02-database-foundation/02-RESEARCH.md §"Schema DDL", §"Connection module", §"Seed code", §"Public surface"
    - .planning/phases/02-database-foundation/02-PATTERNS.md §"Pattern Assignments" (all four new files)
    - .planning/phases/02-database-foundation/02-CONTEXT.md §"Implementation Decisions" (D-01..D-09)
    - planning/PLAN.md §7 (canonical schema — the DDL strings must be faithful to this)
    - backend/CLAUDE.md (public import surface rule)
  </read_first>
  <behavior>
    - `open_database(path)` creates parent dir if needed, opens sqlite3.Connection with check_same_thread=False, sets row_factory to sqlite3.Row, logs "DB opened at {path}".
    - `init_database(conn)` executes all six CREATE TABLE IF NOT EXISTS statements and commits. Runs cleanly on an empty :memory: connection; second call is a no-op.
    - `seed_defaults(conn)` on a fresh DB inserts 1 users_profile row (cash_balance=10000.0) + 10 watchlist rows matching `set(SEED_PRICES.keys())`.
    - Second call to `seed_defaults(conn)` leaves counts unchanged (no IntegrityError, no duplicates) — thanks to `INSERT OR IGNORE` on users_profile and a `COUNT(*)` guard on watchlist.
    - `get_watchlist_tickers(conn)` returns the watchlist tickers for `user_id='default'` as a `list[str]`, deterministically ordered by `added_at, ticker`.
    - Importing `from app.db import open_database, init_database, seed_defaults, get_watchlist_tickers` succeeds.
  </behavior>
  <action>
Create four new files. Use the exact content below.

---

**File: `backend/app/db/__init__.py`** (NEW)

```python
"""SQLite persistence subsystem for FinAlly.

Public API:
    open_database           - Open a long-lived sqlite3.Connection.
    init_database           - Run CREATE TABLE IF NOT EXISTS for all six tables.
    seed_defaults           - Insert default user + 10-ticker watchlist (idempotent).
    get_watchlist_tickers   - Return the default user's watchlist ticker list.
"""

from .connection import open_database
from .seed import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    get_watchlist_tickers,
    init_database,
    seed_defaults,
)

__all__ = [
    "open_database",
    "init_database",
    "seed_defaults",
    "get_watchlist_tickers",
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_USER_ID",
]
```

Notes: Mirrors `backend/app/market/__init__.py` verbatim — no `from __future__ import annotations` (matches the analog).

---

**File: `backend/app/db/schema.py`** (NEW)

```python
"""SQLite schema for FinAlly — six tables per planning/PLAN.md §7."""

# users_profile — single-user cash balance state
USERS_PROFILE = """
CREATE TABLE IF NOT EXISTS users_profile (
    id           TEXT PRIMARY KEY DEFAULT 'default',
    cash_balance REAL NOT NULL    DEFAULT 10000.0,
    created_at   TEXT NOT NULL
)
"""

# watchlist — tickers the user is watching
WATCHLIST = """
CREATE TABLE IF NOT EXISTS watchlist (
    id       TEXT PRIMARY KEY,
    user_id  TEXT NOT NULL DEFAULT 'default',
    ticker   TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
)
"""

# positions — current holdings (one row per ticker per user)
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

# trades — append-only trade history
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

# portfolio_snapshots — total-value time series for the P&L chart
PORTFOLIO_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
)
"""

# chat_messages — conversation history with the LLM
CHAT_MESSAGES = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    actions    TEXT,
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

Notes: Omit `from __future__ import annotations` to match `backend/app/market/seed_prices.py` style (the analog for pure-constants modules — PATTERNS.md §"schema.py" explicitly says to mirror this).

---

**File: `backend/app/db/connection.py`** (NEW)

```python
"""SQLite connection lifecycle for FinAlly."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def open_database(path: str) -> sqlite3.Connection:
    """Open a long-lived SQLite connection at `path`.

    Creates the parent directory if missing (D-09). Returns a connection with
    `sqlite3.Row` as the row factory (D-02) and `check_same_thread=False` (D-01).
    Manual-commit isolation mode is left at the stdlib default (D-03) — callers
    that write must call `conn.commit()` explicitly.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    logger.info("DB opened at %s", path)
    return conn
```

Notes: No try/except — per CONVENTIONS.md "narrow exception handling only at boundaries" and CONTEXT.md Claude's Discretion "corrupt DB should fail loud".

---

**File: `backend/app/db/seed.py`** (NEW)

```python
"""Idempotent seed for users_profile + 10-ticker default watchlist."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import UTC, datetime

from app.db.schema import SCHEMA_STATEMENTS
from app.market.seed_prices import SEED_PRICES

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0


def init_database(conn: sqlite3.Connection) -> None:
    """Create all six PLAN.md §7 tables if they don't exist. Idempotent (DB-01)."""
    for ddl in SCHEMA_STATEMENTS:
        conn.execute(ddl)
    conn.commit()


def seed_defaults(conn: sqlite3.Connection) -> None:
    """Insert the default user row and 10-ticker watchlist when missing (DB-02).

    users_profile uses INSERT OR IGNORE keyed on the primary key `id='default'` —
    safe to call on every boot.

    watchlist uses a `COUNT(*) = 0` guard (not INSERT OR IGNORE) so that once
    Phase 4 ships the watchlist API, a user-deleted ticker is NOT silently
    re-inserted on the next restart. Fresh volumes get the 10 defaults; any
    non-empty watchlist is left untouched.
    """
    now = datetime.now(UTC).isoformat()

    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) "
        "VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )

    existing = conn.execute(
        "SELECT COUNT(*) FROM watchlist WHERE user_id = ?",
        (DEFAULT_USER_ID,),
    ).fetchone()[0]

    if existing == 0:
        for ticker in SEED_PRICES:
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) "
                "VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now),
            )

    conn.commit()


def get_watchlist_tickers(conn: sqlite3.Connection) -> list[str]:
    """Return watchlist tickers for the default user (D-05).

    Used by the lifespan to drive `source.start(tickers)` in place of
    `list(SEED_PRICES.keys())`. Ordered by `added_at, ticker` for determinism —
    seed rows all share one `added_at`, so `ticker` is the stable tiebreaker.
    """
    rows = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, ticker",
        (DEFAULT_USER_ID,),
    ).fetchall()
    return [row["ticker"] for row in rows]
```

Notes:
- The watchlist seed uses `INSERT` (not `INSERT OR IGNORE`) inside the guard because the guard already proves the table is empty — we deliberately want an IntegrityError if something else is racing us (it isn't, but fail-loud is cheaper than silent corruption).
- `datetime.now(UTC)` not `datetime.utcnow()` — the latter is deprecated in Python 3.12.

---

Run `cd backend && uv run --extra dev python -c "from app.db import open_database, init_database, seed_defaults, get_watchlist_tickers; print('ok')"` to smoke-test imports before moving on.
  </action>
  <verify>
    <automated>cd backend && uv run --extra dev python -c "from app.db import open_database, init_database, seed_defaults, get_watchlist_tickers, DEFAULT_CASH_BALANCE, DEFAULT_USER_ID; print('ok')"</automated>
    <automated>cd backend && uv run --extra dev ruff check app/db/</automated>
  </verify>
  <acceptance_criteria>
    - File `backend/app/db/__init__.py` exists and contains the literal line `from .connection import open_database`.
    - File `backend/app/db/__init__.py` contains `__all__` with exactly the six names: `open_database`, `init_database`, `seed_defaults`, `get_watchlist_tickers`, `DEFAULT_CASH_BALANCE`, `DEFAULT_USER_ID`.
    - File `backend/app/db/schema.py` contains six DDL strings, each beginning `CREATE TABLE IF NOT EXISTS` (grep: `grep -c "CREATE TABLE IF NOT EXISTS" backend/app/db/schema.py` returns exactly `6`).
    - File `backend/app/db/schema.py` declares `SCHEMA_STATEMENTS: tuple[str, ...] = (...)` with all six constants in the exact order `USERS_PROFILE, WATCHLIST, POSITIONS, TRADES, PORTFOLIO_SNAPSHOTS, CHAT_MESSAGES`.
    - File `backend/app/db/connection.py` contains `check_same_thread=False` and `conn.row_factory = sqlite3.Row` and `Path(path).parent.mkdir(parents=True, exist_ok=True)` — each appearing verbatim.
    - File `backend/app/db/connection.py` contains NO `try:` block anywhere.
    - File `backend/app/db/seed.py` contains the literal line `from app.market.seed_prices import SEED_PRICES` (D-04 single source of truth).
    - File `backend/app/db/seed.py` contains a `SELECT COUNT(*) FROM watchlist WHERE user_id = ?` guard before inserting the watchlist rows (grep-verifiable: `grep -c "SELECT COUNT" backend/app/db/seed.py` returns `>=1`).
    - File `backend/app/db/seed.py` uses `datetime.now(UTC)` (NOT `datetime.utcnow()`).
    - `grep -r "utcnow" backend/app/db/` returns no matches.
    - `cd backend && uv run --extra dev python -c "from app.db import open_database, init_database, seed_defaults, get_watchlist_tickers, DEFAULT_CASH_BALANCE, DEFAULT_USER_ID; print('ok')"` prints `ok`.
    - `cd backend && uv run --extra dev ruff check app/db/` exits 0.
  </acceptance_criteria>
  <done>Four new files exist under `backend/app/db/` with the exact content above. Public imports work. `ruff` is clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Unit tests for DB-01 + DB-02 + DB-03 — schema, seed idempotence, reopen persistence</name>
  <files>backend/tests/db/__init__.py, backend/tests/db/test_schema.py, backend/tests/db/test_seed.py, backend/tests/db/test_persistence.py</files>
  <read_first>
    - backend/tests/market/__init__.py (1-line test-package marker to mirror)
    - backend/tests/market/test_cache.py (class-grouped unit-test pattern, one behavior per method)
    - backend/tests/market/test_factory.py (env-patching pattern — not strictly needed here, reviewed for style)
    - backend/app/db/schema.py (the DDL strings — tests assert table/column names against these)
    - backend/app/db/seed.py (seed + get_watchlist_tickers behavior under test)
    - backend/app/market/seed_prices.py (tests compare against `set(SEED_PRICES.keys())`)
    - .planning/phases/02-database-foundation/02-VALIDATION.md §"Per-Task Verification Map" (task IDs 02-01-01..02-01-02 test names)
    - .planning/phases/02-database-foundation/02-RESEARCH.md §"Phase Requirements → Test Map"
    - .planning/phases/02-database-foundation/02-PATTERNS.md §"test_schema.py" / §"test_seed.py" / §"test_persistence.py"
  </read_first>
  <behavior>
    - `TestSchema.test_all_six_tables_created`: after `init_database(:memory:)`, `sqlite_master` contains the names `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`.
    - `TestSchema.test_unique_constraints_declared`: attempting a second `INSERT` with the same `(user_id, ticker)` into `watchlist` raises `sqlite3.IntegrityError`; same for `positions`.
    - `TestSchema.test_user_id_defaults_to_default`: inserting a `watchlist` row WITHOUT supplying `user_id` yields a row whose `user_id` column equals `'default'`.
    - `TestSchema.test_init_database_is_idempotent`: calling `init_database(conn)` twice does not raise.
    - `TestSeed.test_fresh_db_gets_seeded`: after `init_database` + `seed_defaults`, `SELECT COUNT(*) FROM users_profile` returns `1` and `SELECT COUNT(*) FROM watchlist` returns `10`.
    - `TestSeed.test_cash_balance_defaults_to_10000`: the seeded `users_profile` row has `cash_balance == 10000.0` and `id == 'default'`.
    - `TestSeed.test_watchlist_matches_seed_prices_keys`: `set(get_watchlist_tickers(conn))` equals `set(SEED_PRICES.keys())`.
    - `TestSeed.test_reseed_is_noop`: calling `seed_defaults(conn)` twice leaves counts unchanged (1 user, 10 watchlist rows) and raises no exception.
    - `TestSeed.test_reseed_does_not_re_add_deleted_ticker`: after seeding, delete one ticker, then call `seed_defaults` again — the deleted ticker stays deleted (validates the `COUNT(*)` guard decision).
    - `TestPersistence.test_data_survives_reopen`: open DB at a `tmp_path` file, init + seed, close, re-open same path, row counts match (1 user, 10 watchlist).
  </behavior>
  <action>
Create four new test files. Use the exact content below.

---

**File: `backend/tests/db/__init__.py`** (NEW)

```python
"""Tests for DB persistence subsystem."""
```

---

**File: `backend/tests/db/test_schema.py`** (NEW)

```python
"""Tests for SQLite schema DDL (DB-01)."""

import sqlite3

import pytest

from app.db import init_database


EXPECTED_TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


class TestSchema:
    """Unit tests for the six-table SQLite schema."""

    def _fresh(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_database(conn)
        return conn

    def test_all_six_tables_created(self):
        """init_database creates all six PLAN.md §7 tables."""
        conn = self._fresh()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        names = {row["name"] for row in rows}
        assert EXPECTED_TABLES.issubset(names), names

    def test_init_database_is_idempotent(self):
        """Running init_database twice does not raise."""
        conn = self._fresh()
        init_database(conn)  # second call — should be a no-op.
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        names = {row["name"] for row in rows}
        assert EXPECTED_TABLES.issubset(names)

    def test_user_id_defaults_to_default(self):
        """Inserting a watchlist row without user_id yields user_id='default'."""
        conn = self._fresh()
        conn.execute(
            "INSERT INTO watchlist (id, ticker, added_at) VALUES (?, ?, ?)",
            ("abc", "AAPL", "2026-04-20T00:00:00+00:00"),
        )
        row = conn.execute(
            "SELECT user_id FROM watchlist WHERE ticker = 'AAPL'"
        ).fetchone()
        assert row["user_id"] == "default"

    def test_watchlist_unique_constraint(self):
        """UNIQUE (user_id, ticker) rejects duplicate (default, AAPL) inserts."""
        conn = self._fresh()
        conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            ("1", "default", "AAPL", "2026-04-20T00:00:00+00:00"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                ("2", "default", "AAPL", "2026-04-20T00:00:00+00:00"),
            )

    def test_positions_unique_constraint(self):
        """UNIQUE (user_id, ticker) rejects duplicate positions rows."""
        conn = self._fresh()
        conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("1", "default", "AAPL", 1.0, 190.0, "2026-04-20T00:00:00+00:00"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("2", "default", "AAPL", 2.0, 195.0, "2026-04-20T00:00:00+00:00"),
            )
```

---

**File: `backend/tests/db/test_seed.py`** (NEW)

```python
"""Tests for default seed: users_profile + 10-ticker watchlist (DB-02)."""

import sqlite3

from app.db import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    get_watchlist_tickers,
    init_database,
    seed_defaults,
)
from app.market.seed_prices import SEED_PRICES


class TestSeed:
    """Unit tests for seed_defaults + get_watchlist_tickers."""

    def _fresh(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_database(conn)
        return conn

    def test_fresh_db_gets_seeded(self):
        """seed_defaults on an empty DB produces 1 users_profile + 10 watchlist rows."""
        conn = self._fresh()
        seed_defaults(conn)
        users = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        wl = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        assert users == 1
        assert wl == 10

    def test_cash_balance_defaults_to_10000(self):
        """Seeded users_profile row has id='default' and cash_balance=10000.0."""
        conn = self._fresh()
        seed_defaults(conn)
        row = conn.execute(
            "SELECT id, cash_balance FROM users_profile WHERE id = ?",
            (DEFAULT_USER_ID,),
        ).fetchone()
        assert row["id"] == "default"
        assert row["cash_balance"] == DEFAULT_CASH_BALANCE == 10000.0

    def test_watchlist_matches_seed_prices_keys(self):
        """Seeded watchlist tickers == set(SEED_PRICES.keys()) — D-04 single source of truth."""
        conn = self._fresh()
        seed_defaults(conn)
        tickers = get_watchlist_tickers(conn)
        assert set(tickers) == set(SEED_PRICES)
        assert len(tickers) == len(SEED_PRICES) == 10

    def test_reseed_is_noop(self):
        """Calling seed_defaults twice leaves counts unchanged and does not raise."""
        conn = self._fresh()
        seed_defaults(conn)
        seed_defaults(conn)  # Second call.
        users = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        wl = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        assert users == 1
        assert wl == 10

    def test_reseed_does_not_re_add_deleted_ticker(self):
        """COUNT(*) guard: if the user deletes a ticker, re-seed does NOT restore it.

        This is the forward-compatibility decision for when Phase 4 ships the
        watchlist API. The contract: seed only when the watchlist is fully empty.
        """
        conn = self._fresh()
        seed_defaults(conn)
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (DEFAULT_USER_ID, "NFLX"),
        )
        conn.commit()

        seed_defaults(conn)  # Should be a no-op on a non-empty watchlist.

        tickers = get_watchlist_tickers(conn)
        assert "NFLX" not in tickers
        assert len(tickers) == 9

    def test_get_watchlist_tickers_empty(self):
        """get_watchlist_tickers on an unseeded DB returns an empty list, not None."""
        conn = self._fresh()
        assert get_watchlist_tickers(conn) == []
```

---

**File: `backend/tests/db/test_persistence.py`** (NEW)

```python
"""Persistence: data survives close/re-open of the same file (DB-03 proxy)."""

from app.db import init_database, open_database, seed_defaults


class TestPersistence:
    """Integration tests for the file-level persistence contract.

    Phase 9 proves the Docker-volume variant; here we prove the primitive:
    the same file path opened twice in sequence retains its rows.
    """

    def test_data_survives_reopen(self, tmp_path):
        """Open → init+seed → close → re-open same path → rows present."""
        path = tmp_path / "finally.db"

        conn1 = open_database(str(path))
        init_database(conn1)
        seed_defaults(conn1)
        conn1.close()

        conn2 = open_database(str(path))
        users = conn2.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        wl = conn2.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        conn2.close()

        assert users == 1
        assert wl == 10

    def test_parent_directory_created_on_first_open(self, tmp_path):
        """open_database creates a missing parent dir (D-09)."""
        path = tmp_path / "nested" / "deeper" / "finally.db"
        assert not path.parent.exists()

        conn = open_database(str(path))
        conn.close()

        assert path.parent.is_dir()
        assert path.exists()

    def test_reopen_after_seed_is_still_no_op(self, tmp_path):
        """Re-opening and re-running seed_defaults is a no-op."""
        path = tmp_path / "finally.db"

        conn1 = open_database(str(path))
        init_database(conn1)
        seed_defaults(conn1)
        conn1.close()

        conn2 = open_database(str(path))
        init_database(conn2)  # idempotent DDL
        seed_defaults(conn2)  # COUNT guard: watchlist non-empty, users PK collides
        users = conn2.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        wl = conn2.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        conn2.close()

        assert users == 1
        assert wl == 10
```

---

Run tests after creation:

```bash
cd backend && uv run --extra dev pytest tests/db/ -v
```

All nine tests above MUST pass.
  </action>
  <verify>
    <automated>cd backend && uv run --extra dev pytest tests/db/ -v</automated>
    <automated>cd backend && uv run --extra dev ruff check tests/db/</automated>
  </verify>
  <acceptance_criteria>
    - Files `backend/tests/db/__init__.py`, `backend/tests/db/test_schema.py`, `backend/tests/db/test_seed.py`, `backend/tests/db/test_persistence.py` exist.
    - `cd backend && uv run --extra dev pytest tests/db/ -v` exits 0.
    - The test run reports a collection of AT LEAST these test ids (verified by `pytest -v --collect-only`):
      - `tests/db/test_schema.py::TestSchema::test_all_six_tables_created`
      - `tests/db/test_schema.py::TestSchema::test_init_database_is_idempotent`
      - `tests/db/test_schema.py::TestSchema::test_user_id_defaults_to_default`
      - `tests/db/test_schema.py::TestSchema::test_watchlist_unique_constraint`
      - `tests/db/test_schema.py::TestSchema::test_positions_unique_constraint`
      - `tests/db/test_seed.py::TestSeed::test_fresh_db_gets_seeded`
      - `tests/db/test_seed.py::TestSeed::test_cash_balance_defaults_to_10000`
      - `tests/db/test_seed.py::TestSeed::test_watchlist_matches_seed_prices_keys`
      - `tests/db/test_seed.py::TestSeed::test_reseed_is_noop`
      - `tests/db/test_seed.py::TestSeed::test_reseed_does_not_re_add_deleted_ticker`
      - `tests/db/test_persistence.py::TestPersistence::test_data_survives_reopen`
      - `tests/db/test_persistence.py::TestPersistence::test_parent_directory_created_on_first_open`
      - `tests/db/test_persistence.py::TestPersistence::test_reopen_after_seed_is_still_no_op`
    - `cd backend && uv run --extra dev ruff check tests/db/` exits 0.
    - `grep -rn "utcnow" backend/tests/db/` returns no matches.
  </acceptance_criteria>
  <done>All tests under `backend/tests/db/` pass. `ruff` is clean. DB-01, DB-02, and the file-level component of DB-03 are unit-proven.</done>
</task>

</tasks>

<verification>
## Plan-level verification

After both tasks complete:

1. `cd backend && uv run --extra dev pytest tests/db/ -v` — all 13 tests green.
2. `cd backend && uv run --extra dev ruff check app/db/ tests/db/` — clean.
3. `cd backend && uv run --extra dev pytest -v` — FULL suite still green (Phase 1 lifespan tests still work because Plan 01 does NOT touch `lifespan.py` — that's Plan 02).
4. `grep -rn "CREATE TABLE IF NOT EXISTS" backend/app/db/schema.py | wc -l` returns `6`.
5. `grep -n "from app.market.seed_prices import SEED_PRICES" backend/app/db/seed.py` returns a match (confirms D-04 single source of truth).

## Must-haves cross-check

- ✓ Six tables DDL — `test_all_six_tables_created`
- ✓ UNIQUE constraints — `test_watchlist_unique_constraint`, `test_positions_unique_constraint`
- ✓ `user_id` default `'default'` — `test_user_id_defaults_to_default`
- ✓ Fresh seed = 1 user + 10 tickers — `test_fresh_db_gets_seeded` + `test_cash_balance_defaults_to_10000`
- ✓ Watchlist = `SEED_PRICES.keys()` (D-04) — `test_watchlist_matches_seed_prices_keys`
- ✓ Re-seed is a no-op — `test_reseed_is_noop`
- ✓ Deleted ticker stays deleted — `test_reseed_does_not_re_add_deleted_ticker`
- ✓ File persists across close/reopen (DB-03 proxy) — `test_data_survives_reopen`
- ✓ Parent dir auto-created (D-09) — `test_parent_directory_created_on_first_open`
</verification>

<success_criteria>
- `backend/app/db/` sub-package exists with four modules, clean imports, and a public surface matching `__all__`.
- `backend/tests/db/` covers DB-01 / DB-02 / DB-03(file-level) with 13 green tests.
- No regressions in the Phase 1 suite (this plan does not touch lifespan or existing tests).
- Ruff is clean for both `app/db/` and `tests/db/`.
- D-04 single-source-of-truth is enforced: `seed.py` imports `SEED_PRICES` from `app.market.seed_prices` and no other ticker list exists in `app/db/` or `tests/db/`.
</success_criteria>

<output>
After completion, create `.planning/phases/02-database-foundation/02-01-SUMMARY.md` using the summary template.
</output>
