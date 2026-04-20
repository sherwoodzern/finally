---
phase: 02-database-foundation
verified: 2026-04-20T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 2: Database Foundation Verification Report

**Phase Goal:** An empty Docker volume becomes a fully seeded SQLite database on first startup, and that database survives container restarts.
**Verified:** 2026-04-20
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | On a fresh startup with no `db/finally.db` file, the lifespan creates all six tables (`users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`) matching PLAN.md §7, including `user_id` columns and unique constraints. | VERIFIED | `backend/app/db/schema.py` defines all six DDL strings with `CREATE TABLE IF NOT EXISTS` (grep count = 6). Behavioral spot-check on fresh DB path confirmed tables created: `['chat_messages', 'portfolio_snapshots', 'positions', 'trades', 'users_profile', 'watchlist']`. `test_all_six_tables_created`, `test_user_id_defaults_to_default`, `test_watchlist_unique_constraint`, `test_positions_unique_constraint` pass. |
| 2 | After init, `users_profile` contains one row with `id='default'` and `cash_balance=10000.0`; `watchlist` contains the 10 default tickers. | VERIFIED | `seed_defaults` in `backend/app/db/seed.py` uses INSERT OR IGNORE for users_profile and iterates `SEED_PRICES` for watchlist. Behavioral spot-check: Users=1, Watchlist=10, Cash=10000.0, tickers match exactly `{AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX}`. Tests `test_fresh_db_gets_seeded`, `test_cash_balance_defaults_to_10000`, `test_watchlist_matches_seed_prices_keys`, `test_attaches_db_to_app_state`, `test_tickers_come_from_db_watchlist` pass. |
| 3 | Restarting the process against an already-seeded DB is a no-op — no duplicate seed rows, no schema errors. | VERIFIED | Seed idempotency: INSERT OR IGNORE on users_profile.id PK; `SELECT COUNT(*) = 0` guard on watchlist (`backend/app/db/seed.py:45-48`). Schema uses `CREATE TABLE IF NOT EXISTS`. Tests `test_reseed_is_noop`, `test_reseed_does_not_re_add_deleted_ticker`, `test_init_database_is_idempotent`, `test_reopen_after_seed_is_still_no_op`, `test_second_startup_is_no_op` pass. Behavioral spot-check: second lifespan startup against same path preserves user_count=1, watchlist still 10 (or 9 after a user deletion). |
| 4 | Running the process with `db/finally.db` on a mounted path persists data across restarts (stopping and restarting preserves `cash_balance` and `watchlist`). | VERIFIED | `conn.close()` is in the `finally:` branch of `app/lifespan.py:62-64` ensuring clean shutdown. Behavioral spot-check: mutated cash_balance to 9500.0 and deleted NFLX in first lifespan; re-opened lifespan with same DB_PATH → cash_balance=9500.0 preserved, NFLX remained deleted (COUNT guard honored), watchlist count=9. Tests `test_data_survives_reopen`, `test_parent_directory_created_on_first_open` prove the file-level persistence primitive. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `backend/app/db/__init__.py` | Public DB API re-exports | VERIFIED | Contains `from .connection import open_database` and re-exports all 6 names in `__all__`. Wired: imported by `app/lifespan.py` and by 4 test modules. |
| `backend/app/db/schema.py` | Six CREATE TABLE IF NOT EXISTS + SCHEMA_STATEMENTS tuple | VERIFIED | 6 DDL constants grouped into `SCHEMA_STATEMENTS: tuple[str, ...]`. Includes CHECK constraints on `trades.side` and `chat_messages.role` (low-cost hardening per RESEARCH A1). |
| `backend/app/db/connection.py` | `open_database(path)` with mkdir parent, `sqlite3.Row`, `check_same_thread=False` | VERIFIED | All three design lock-ins (D-01/D-02/D-09) present verbatim. `%`-style logging. No defensive try/except. |
| `backend/app/db/seed.py` | `init_database`, `seed_defaults`, `get_watchlist_tickers`, constants | VERIFIED | `SEED_PRICES` imported from `app.market.seed_prices` (D-04 single source of truth). Uses `datetime.now(UTC)` (not deprecated `utcnow`). COUNT(*)=0 guard on watchlist insert. |
| `backend/app/lifespan.py` | DB-aware startup: open → init → seed → read watchlist → start source; close on shutdown | VERIFIED | Import chain correct. Execution order: `open_database` → `init_database` → `seed_defaults` → `PriceCache()` → `create_market_data_source` → `get_watchlist_tickers(conn)` → `source.start(tickers)` → attach `app.state.db/price_cache/market_source` → mount SSE router. `conn.close()` in `finally:` branch alongside `await source.stop()`. Import of `SEED_PRICES` removed (docstring mention only). |
| `backend/tests/db/test_schema.py` | DB-01 unit tests | VERIFIED | `TestSchema` with 5 green tests covering all six tables + both UNIQUE constraints + user_id default + idempotent init. |
| `backend/tests/db/test_seed.py` | DB-02 unit tests | VERIFIED | `TestSeed` with 6 green tests including fresh seed counts, SEED_PRICES equivalence, re-seed no-op, deleted-ticker-stays-deleted, empty-query shape. |
| `backend/tests/db/test_persistence.py` | DB-03 unit-level proxy | VERIFIED | `TestPersistence` with 3 green tests: data survives reopen, parent dir auto-created, re-open + re-seed no-op. |
| `backend/tests/test_lifespan.py` | DB integration tests | VERIFIED | 10 green tests (7 retrofitted Phase 1 + 3 new DB integration: `test_attaches_db_to_app_state`, `test_tickers_come_from_db_watchlist`, `test_second_startup_is_no_op`). |
| `backend/tests/conftest.py` | `db_path` fixture for test isolation | VERIFIED | Fixture uses `tmp_path / 'finally.db'` with `monkeypatch.setenv`. Adopted across `test_lifespan.py` and `test_main.py`. |
| `backend/market_data_demo.py` | Demo derives TICKERS from SEED_PRICES | VERIFIED | Line 30: `TICKERS = list(SEED_PRICES.keys())`. No hardcoded ticker literal remains. |
| `backend/tests/db/test_demo_refactor.py` | Regression pin for demo tickers | VERIFIED | 1 green test asserts set+ordered equality between `market_data_demo.TICKERS` and `list(SEED_PRICES.keys())`. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `backend/app/db/seed.py` | `backend/app/market/seed_prices.py` | `from app.market.seed_prices import SEED_PRICES` | WIRED | D-04 single source of truth enforced. Import confirmed at `seed.py:11`. |
| `backend/app/db/seed.py` | `backend/app/db/schema.py` | `from app.db.schema import SCHEMA_STATEMENTS` | WIRED | `init_database` iterates SCHEMA_STATEMENTS. |
| `backend/app/db/__init__.py` | `backend/app/db/connection.py` | `from .connection import open_database` | WIRED | Public re-export verified. |
| `backend/app/lifespan.py` | `backend/app/db/__init__.py` | `from .db import get_watchlist_tickers, init_database, open_database, seed_defaults` | WIRED | All 4 names used in lifespan body. |
| `backend/app/lifespan.py` | `backend/app/db/seed.py` | `tickers = get_watchlist_tickers(conn)` replaces `list(SEED_PRICES.keys())` (D-05) | WIRED | Line 46. `source.start(tickers)` consumes the DB-sourced list. |
| `backend/tests/test_lifespan.py` | `backend/tests/conftest.py` | autouse-ish `db_path` fixture (method-scoped) injects isolated DB per test | WIRED | All 10 lifespan tests accept `db_path` parameter and inject `DB_PATH` into env via `patch.dict`. |
| `backend/market_data_demo.py` | `backend/app/market/seed_prices.py` | `TICKERS = list(SEED_PRICES.keys())` | WIRED | D-06 enforced. Regression test pins it. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `app.state.db` | `conn` | `open_database(db_path)` in lifespan | Yes — real sqlite3.Connection returning seeded rows | FLOWING |
| `app.state.market_source` tickers | `tickers` | `get_watchlist_tickers(conn)` (DB SELECT) | Yes — 10 tickers returned from watchlist table | FLOWING |
| `users_profile.cash_balance` | seeded value | `seed_defaults` INSERT OR IGNORE with 10000.0 | Yes — row present on fresh DB, preserved on restart | FLOWING |
| `watchlist` rows | 10 seed tickers | `seed_defaults` iterates `SEED_PRICES` | Yes — all 10 tickers present; gap-aware on restart via COUNT guard | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full test suite passes | `uv run --extra dev python -m pytest` | 101 passed (0 failed) in 2.03s | PASS |
| Fresh startup creates all six tables + seeds data (parent dir auto-created) | Python driver: set DB_PATH to non-existent nested path, enter lifespan, query `sqlite_master` + `users_profile` + `watchlist` | Tables = `['chat_messages','portfolio_snapshots','positions','trades','users_profile','watchlist']`; users=1, watchlist=10, cash=10000.0; all 10 SEED_PRICES tickers present | PASS |
| Persistence across restarts (cash_balance + watchlist survive) | Python driver: lifespan #1 mutates cash to 9500.0, deletes NFLX; lifespan #2 against same path | Second startup reports users=1, watchlist=9 (NFLX stays deleted — COUNT guard), cash_balance=9500.0 preserved | PASS |
| DB public API importable | `uv run python -c "from app.db import open_database, init_database, seed_defaults, get_watchlist_tickers, DEFAULT_CASH_BALANCE, DEFAULT_USER_ID"` | imports: ok | PASS |
| `conn.close()` in lifespan finally | `grep conn.close lifespan.py` | Line 64, inside `finally:` branch (line 62) alongside `await source.stop()` | PASS |
| No hardcoded ticker list besides SEED_PRICES | `grep "TICKERS = ["` in backend/ | No matches | PASS |
| SEED_PRICES not imported in lifespan | `grep SEED_PRICES app/lifespan.py` | Only 1 occurrence, in a docstring comment — no import, no runtime reference | PASS |

### Requirements Coverage

Phase requirements from PLAN frontmatter: DB-01, DB-02, DB-03.

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| DB-01 | 02-01, 02-02 | SQLite schema for six tables with `user_id` defaults and UNIQUE constraints per PLAN.md §7 | SATISFIED | `app/db/schema.py` defines all six tables with `CHECK` constraints on `trades.side` and `chat_messages.role`, `UNIQUE (user_id, ticker)` on `watchlist` and `positions`, `user_id TEXT NOT NULL DEFAULT 'default'` on every multi-user table. Covered by `TestSchema` (5 tests). |
| DB-02 | 02-01, 02-02, 02-03 | Lazy initialization on startup — tables created and default user (cash=10000.0) + 10 default watchlist tickers seeded when DB is empty | SATISFIED | `seed_defaults` + lifespan wiring. INSERT OR IGNORE for users_profile, COUNT=0 guard for watchlist. Covered by `TestSeed` (6 tests) + `test_attaches_db_to_app_state` + `test_tickers_come_from_db_watchlist`. Behavioral spot-check against fresh DB_PATH confirms 1 user + 10 tickers. |
| DB-03 | 02-01, 02-02 | SQLite file at `db/finally.db` persists across restarts via Docker named volume | SATISFIED | File-level primitive proven in `TestPersistence`; lifespan-level proven in `test_second_startup_is_no_op`. Behavioral spot-check confirms cash_balance (9500.0) and watchlist state (NFLX deleted stays deleted) preserved across two lifespan cycles against the same DB_PATH. Docker-volume integration is NOT in scope here — Phase 9 (OPS-02) proves the Docker container + `-v finally-data:/app/db` variant. The code-level guarantee (the file persists and the lifespan re-consumes it correctly) is fully satisfied. |

No orphaned requirements — all three IDs declared in all three plans' `requirements:` frontmatter (with 02-03 scoping to DB-02 only, consistent with its cosmetic-cleanup role).

### Anti-Patterns Found

None blocking. Anti-pattern scan across all files modified/created in this phase:

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| None | — | No TODO/FIXME/placeholder/XXX/HACK comments in any phase-2 file | — | — |
| None | — | No `return None`, `return {}`, `return []` placeholder bodies | — | — |
| None | — | No f-strings in logging calls (CONVENTIONS.md compliant — `%`-style throughout) | — | — |
| None | — | No emojis in code/logs | — | — |
| None | — | No `Optional[X]` (PEP 604 compliant) | — | — |
| None | — | No `datetime.utcnow()` (uses `datetime.now(UTC)`) | — | — |
| None | — | No defensive try/except (fail-loud per CONTEXT Claude's Discretion) | — | — |

Soft observation (Info only, not a gap):
- `backend/tests/conftest.py` `db_path` fixture is NOT declared `autouse=True` despite the plan's wording of "class-scoped autouse fixture". In practice every test in `TestLifespan` and `test_main.py` accepts it as a parameter explicitly, which is equivalent (pytest resolves by signature). The claim in `02-02-lifespan-wiring-SUMMARY.md` is therefore slightly inaccurate in the word "autouse" but the functional guarantee (no test writes to `./db/finally.db`) is satisfied — confirmed via `ls backend/db/finally.db` returning no such file after the full test run.

### Human Verification Required

None. All Phase 2 success criteria can be verified programmatically — this phase is pure backend persistence code with no UI, no real-time UX, and no external service integration. Docker-volume-level persistence (the full real-world variant of Criterion #4) is explicitly scoped to Phase 9 (OPS-02).

### Gaps Summary

No gaps. All 4 roadmap success criteria verified with supporting code, tests, and behavioral spot-checks:

1. Fresh startup creates all six tables with correct columns, defaults, and UNIQUE constraints — proven by schema tests + fresh-DB spot-check.
2. Seed produces `users_profile(id='default', cash_balance=10000.0)` + 10 default watchlist tickers — proven by seed tests + lifespan integration tests + spot-check.
3. Re-startup against seeded DB is a no-op — proven by idempotency tests + `test_second_startup_is_no_op` + spot-check.
4. Data persists across restarts (cash_balance + watchlist) — proven by file-level `test_data_survives_reopen` and behavioral spot-check where cash was mutated to 9500.0 and NFLX was deleted, both preserved across a second lifespan cycle.

The full backend test suite is green (101 passed). The Phase 1 test suite continues to pass because every lifespan test receives an isolated `DB_PATH` via the `db_path` fixture, so no test writes to `backend/db/finally.db`. Ruff is clean across `app/db/`, `tests/db/`, `lifespan.py`, `tests/conftest.py`, `tests/test_lifespan.py`, `market_data_demo.py`, and `tests/db/test_demo_refactor.py`.

Requirements DB-01, DB-02, DB-03 are fully satisfied at the code level. The Docker-volume end-to-end proof for DB-03 is explicitly out of scope here and tracked under Phase 9 (OPS-02), as per ROADMAP traceability.

---

*Verified: 2026-04-20*
*Verifier: Claude (gsd-verifier)*
