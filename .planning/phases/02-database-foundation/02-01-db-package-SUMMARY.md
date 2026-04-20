---
phase: 02-database-foundation
plan: 01
subsystem: database
tags: [sqlite, persistence, schema, seed, stdlib-sqlite3, backend, python]

# Dependency graph
requires:
  - phase: 01-app-shell-config
    provides: app package layout, app/market/seed_prices.py SEED_PRICES dict, CONVENTIONS.md module patterns
provides:
  - backend/app/db sub-package with public surface (open_database, init_database, seed_defaults, get_watchlist_tickers, DEFAULT_CASH_BALANCE, DEFAULT_USER_ID)
  - Six-table SQLite schema (users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages) via CREATE TABLE IF NOT EXISTS strings
  - Idempotent seed contract (INSERT OR IGNORE on users_profile PK, COUNT(*) guard on watchlist)
  - open_database primitive with parent-dir mkdir, sqlite3.Row, check_same_thread=False
  - 14 passing unit tests covering DB-01, DB-02, and file-level DB-03
affects: [02-02-lifespan-wiring, 03-portfolio, 04-watchlist, 05-chat, 09-docker-deployment]

# Tech tracking
tech-stack:
  added:
    - stdlib sqlite3 (already Python builtin)
    - stdlib uuid, datetime.UTC, pathlib.Path (already builtins, first usage in this plan)
  patterns:
    - Module-level SQL string constants + SCHEMA_STATEMENTS tuple (mirrors app/market/seed_prices.py style)
    - app/db/__init__.py public re-export surface (mirrors app/market/__init__.py)
    - Idempotent DDL via CREATE TABLE IF NOT EXISTS; no migrations framework
    - Idempotent seed via INSERT OR IGNORE for single-PK rows + COUNT(*) guard for collections
    - open_database primitive returns a long-lived sqlite3.Connection (to be attached to app.state.db in Plan 02-02)

key-files:
  created:
    - backend/app/db/__init__.py
    - backend/app/db/schema.py
    - backend/app/db/connection.py
    - backend/app/db/seed.py
    - backend/tests/db/__init__.py
    - backend/tests/db/test_schema.py
    - backend/tests/db/test_seed.py
    - backend/tests/db/test_persistence.py
  modified: []

key-decisions:
  - "Seed idempotency: INSERT OR IGNORE keyed on users_profile.id='default' for the single profile row; COUNT(*)=0 guard on watchlist so once Phase 4 ships the watchlist API, user-deleted tickers are not silently re-inserted on restart."
  - "CHECK constraints on trades.side IN ('buy','sell') and chat_messages.role IN ('user','assistant') added as low-cost hardening (A1). Not part of DB-01 acceptance contract, but present in DDL."
  - "No PRAGMA foreign_keys = ON because no FKs are declared (A2, RESEARCH.md). If FKs are added later, the PRAGMA must be set per-connection inside open_database."
  - "datetime.now(UTC).isoformat() used for every timestamp column (not deprecated utcnow())."
  - "D-04 single source of truth: seed.py imports SEED_PRICES from app.market.seed_prices; no second list of tickers in app/db/ or tests/db/."
  - "get_watchlist_tickers orders by (added_at, ticker) for deterministic ordering since all 10 seed rows share the same added_at timestamp."

patterns-established:
  - "Public-surface re-export via __init__.py with explicit __all__ listing, consumers import from app.db"
  - "Pure-constants module (schema.py) mirrors seed_prices.py style: no from __future__ import, no logger, only module-level constants + final grouping tuple"
  - "Lifecycle-primitive module (connection.py) uses from __future__ import annotations + logger + %-style logging + zero defensive try/except"
  - "Seed/CRUD module (seed.py) imports SCHEMA_STATEMENTS sibling + cross-package constants from app.market, uses stdlib uuid + datetime.UTC"
  - "Class-grouped unit tests (TestSchema, TestSeed, TestPersistence) with one behavior per test_* method, using :memory: for isolation and tmp_path for file-persistence"

requirements-completed: [DB-01, DB-02, DB-03]

# Metrics
duration: ~20min
completed: 2026-04-20
---

# Phase 02 Plan 01: DB Package Summary

**Self-contained backend/app/db sub-package with six-table SQLite schema, open_database primitive, and idempotent seed (INSERT OR IGNORE + COUNT guard) covered by 14 unit tests — no lifespan wiring yet (belongs to Plan 02-02).**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-20T17:14:00Z (approx.)
- **Completed:** 2026-04-20T17:33:34Z
- **Tasks:** 2
- **Files created:** 8 (4 app modules + 4 test modules)

## Accomplishments

- Stood up `backend/app/db/` as a self-contained sub-package mirroring `backend/app/market/` in shape and style (module docstrings, `from __future__ import annotations`, `%`-style logging, zero defensive try/except).
- Authored six faithful `CREATE TABLE IF NOT EXISTS` statements per PLAN.md §7, with `user_id TEXT NOT NULL DEFAULT 'default'` on every multi-user table and `UNIQUE (user_id, ticker)` on `watchlist` and `positions`.
- Implemented `seed_defaults()` with the forward-compatible split: `INSERT OR IGNORE` for the single `users_profile` PK row, `COUNT(*) = 0` guard for the 10-row watchlist so Phase 4's watchlist API will not see deleted tickers re-inserted on restart.
- Delivered 14 green unit tests proving DB-01 (schema/uniques/defaults), DB-02 (fresh-seed counts, cash balance, SEED_PRICES equality, re-seed no-op, deleted-ticker stays deleted, empty-query shape), and DB-03 at the file level (open → init → seed → close → re-open preserves rows; parent dir auto-created).
- Full Phase 1 suite (83 tests) still passes — this plan touches no lifespan code.

## Task Commits

1. **Task 1: Create app/db sub-package (schema, connection, seed, __init__)** — `2dd2663` (feat)
2. **Task 2: Unit tests for DB-01/DB-02/DB-03** — `73e2028` (test)

_Plan metadata commit for SUMMARY.md follows this file._

## Files Created

- `backend/app/db/__init__.py` — Public API re-export: `open_database`, `init_database`, `seed_defaults`, `get_watchlist_tickers`, `DEFAULT_CASH_BALANCE`, `DEFAULT_USER_ID`.
- `backend/app/db/schema.py` — Six `CREATE TABLE IF NOT EXISTS` string constants (`USERS_PROFILE`, `WATCHLIST`, `POSITIONS`, `TRADES`, `PORTFOLIO_SNAPSHOTS`, `CHAT_MESSAGES`) grouped into `SCHEMA_STATEMENTS: tuple[str, ...]`.
- `backend/app/db/connection.py` — `open_database(path) -> sqlite3.Connection` with parent-dir `mkdir(parents=True, exist_ok=True)`, `sqlite3.Row` factory, `check_same_thread=False`, `%`-style info log.
- `backend/app/db/seed.py` — `init_database`, `seed_defaults`, `get_watchlist_tickers` plus `DEFAULT_USER_ID` / `DEFAULT_CASH_BALANCE` constants. Imports `SEED_PRICES` from `app.market.seed_prices` (D-04).
- `backend/tests/db/__init__.py` — 1-line package marker.
- `backend/tests/db/test_schema.py` — `TestSchema` with 5 tests for DB-01 (six tables exist, idempotent init, `user_id` default, UNIQUE on `watchlist`, UNIQUE on `positions`).
- `backend/tests/db/test_seed.py` — `TestSeed` with 6 tests for DB-02 (fresh seed counts, cash balance, SEED_PRICES equality, re-seed no-op, deleted ticker stays deleted, empty query).
- `backend/tests/db/test_persistence.py` — `TestPersistence` with 3 tests for DB-03 file-level proxy (data survives reopen, parent dir auto-created, re-open + re-seed is no-op).

## Decisions Made

Followed plan design lock-ins exactly. All binding decisions (D-01..D-09) from `02-CONTEXT.md` honored:

- `open_database`: `check_same_thread=False` (D-01), `row_factory = sqlite3.Row` (D-02), no `isolation_level` override (D-03), parent-dir mkdir before connect (D-09).
- Seed: `SEED_PRICES` is the sole source of truth (D-04).
- Seed idempotency: option (b) from RESEARCH.md Open Question #1 — `INSERT OR IGNORE` on users_profile, `COUNT(*) = 0` guard on watchlist.
- DDL hardening: `CHECK (side IN ('buy','sell'))` and `CHECK (role IN ('user','assistant'))` kept per plan's RESEARCH.md A1 recommendation.
- No `PRAGMA foreign_keys = ON` because no FKs are declared (RESEARCH.md A2).
- Timestamps: `datetime.now(UTC).isoformat()`, not `datetime.utcnow()`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Fixed ruff I001 import ordering in test_schema.py**

- **Found during:** Task 2 post-write verification (`ruff check tests/db/`)
- **Issue:** Initial file placed `import sqlite3`, blank line, `import pytest`, blank line, `from app.db import init_database`. Ruff flagged I001: the blank line between `pytest` (third-party) and `app.db` (first-party) was missing after normalization; the double blank line after `from app.db ...` was also wrong.
- **Fix:** Applied `uv run --extra dev ruff check --fix tests/db/` to reorder imports into the correct three-group layout: stdlib / third-party / first-party, each group separated by one blank line (matches `tests/market/test_factory.py` analog).
- **Files modified:** `backend/tests/db/test_schema.py`
- **Verification:** `uv run --extra dev ruff check app/db/ tests/db/` reports "All checks passed!"; `uv run --extra dev pytest tests/db/ -v` continues to show 14/14 passing.
- **Committed in:** `73e2028` (rolled into the Task 2 commit before push).

---

**Total deviations:** 1 auto-fixed (1 lint bug in newly-written test file, fixed inline via ruff --fix).
**Impact on plan:** Cosmetic only; no logic change, no test outcome change. Plan executed exactly as specified otherwise.

## Issues Encountered

- **Worktree base commit was wrong at agent start.** `git merge-base` showed `b86573aa...` (main) instead of the expected feature-branch base `5200dc64...`. Corrected via `git reset --hard 5200dc64...` per the `<worktree_branch_check>` protocol before any other work. Verified post-reset HEAD. No data loss — the worktree branch had no prior commits.

## User Setup Required

None — this plan is purely internal Python code and tests. No new runtime dependencies (stdlib `sqlite3`, `uuid`, `datetime`, `pathlib` only). No environment variables read in this plan (lifespan wiring is Plan 02-02's concern).

## Next Phase Readiness

**Ready for Plan 02-02 (lifespan wiring):**

- `from app.db import open_database, init_database, seed_defaults, get_watchlist_tickers` succeeds.
- `backend/app/lifespan.py` can now be edited to add, in order: `open_database(DB_PATH)` → `init_database(conn)` → `seed_defaults(conn)` → `get_watchlist_tickers(conn)` → `source.start(tickers)`, plus `conn.close()` in the `finally:` branch and `app.state.db = conn` alongside the existing `price_cache` / `market_source` attachments.
- All `backend/tests/db/` tests are pure stdlib-sqlite3 and use `:memory:` or `tmp_path`, so they remain independent of the lifespan. Plan 02-02's lifespan-level tests will layer on top.
- `backend/market_data_demo.py` refactor (D-06) is NOT part of this plan — it belongs to Plan 02-02 per the CONTEXT.md scope split.

**Blockers / concerns:** None.

## Self-Check: PASSED

- FOUND: `backend/app/db/__init__.py`
- FOUND: `backend/app/db/schema.py`
- FOUND: `backend/app/db/connection.py`
- FOUND: `backend/app/db/seed.py`
- FOUND: `backend/tests/db/__init__.py`
- FOUND: `backend/tests/db/test_schema.py`
- FOUND: `backend/tests/db/test_seed.py`
- FOUND: `backend/tests/db/test_persistence.py`
- FOUND commit: `2dd2663` (Task 1 — feat: app/db sub-package)
- FOUND commit: `73e2028` (Task 2 — test: DB-01/DB-02/DB-03 unit tests)
- `ruff check app/db/ tests/db/` — PASSED
- `pytest tests/db/ -v` — 14/14 PASSED
- `pytest` full suite — 97/97 PASSED (83 pre-existing Phase 1 + 14 new Phase 2)

---
*Phase: 02-database-foundation*
*Completed: 2026-04-20*
