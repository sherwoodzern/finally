# Phase 2: Database Foundation - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the SQLite persistence layer: define the 6-table schema from
`planning/PLAN.md` §7, lazily create it from the FastAPI `lifespan` startup on
first boot, seed the default `users_profile` row and the 10-ticker default
watchlist, and persist `db/finally.db` across container restarts via the
Docker named volume — all using stdlib `sqlite3` (no ORM, no migrations).

**In scope:**
- Schema creation for `users_profile`, `watchlist`, `positions`, `trades`,
  `portfolio_snapshots`, `chat_messages` (per PLAN.md §7, including `user_id`
  columns and unique constraints).
- Lazy init on startup: create tables and seed defaults if the DB is empty;
  no-op on re-start.
- SQLite connection lifecycle wired into the existing `backend/app/lifespan.py`.
- `DB_PATH` env var with default `db/finally.db`; parent dir auto-created.
- Lifespan ticker set switches from `SEED_PRICES.keys()` to the DB watchlist
  post-seed (replaces the Phase 1 stopgap flagged in its CONTEXT.md as
  "Planner to wire it so Phase 2's DB-backed watchlist can swap in without
  code churn").
- Refactor `backend/market_data_demo.py` to reuse `SEED_PRICES.keys()` —
  closes CONCERNS.md #9 drift risk.

**Out of scope (belongs to later phases):**
- Portfolio / trade endpoints and snapshot recording logic → Phase 3
- Watchlist CRUD endpoints and price-cache add/remove on mutation → Phase 4
- Chat message persistence logic (`chat_messages` writes) → Phase 5
- Dockerfile, volume mount wiring, `.env.example` → Phase 9

</domain>

<decisions>
## Implementation Decisions

### Connection Strategy

- **D-01:** One long-lived `sqlite3.Connection` is opened during the `lifespan`
  startup and attached to `app.state.db`. Closed in the `finally:` branch on
  shutdown. Mirrors the Phase 1 PriceCache pattern (D-02 from 01-CONTEXT.md).
  Opened with `check_same_thread=False` because FastAPI handlers may dispatch
  across threads; single-writer SQLite is safe under this flag for our
  single-user workload. Rejected: open-per-call helper (loses the `app.state`
  pattern) and FastAPI `Depends(get_db)` yield (extra ceremony without an ORM).

- **D-02:** `connection.row_factory = sqlite3.Row` so cursors return dict-like
  rows accessible by column name. Keeps downstream handlers (Phases 3–5)
  readable without a mapping layer. Dataclass row mappers are deferred —
  evaluate when portfolio/chat code lands.

- **D-03:** Default manual-commit mode (stdlib sqlite3's `isolation_level`
  stays at its default, NOT autocommit). Every write path calls
  `conn.commit()` explicitly. Preserves the option for Phase 3 trade +
  snapshot writes to share a transaction if needed.

### Default Seed — Single Source of Truth

- **D-04:** The DB seeder imports `SEED_PRICES` from
  `backend/app/market/seed_prices.py` and inserts `list(SEED_PRICES.keys())`
  into `watchlist` at init time. No new constants. `seed_prices.py` stays the
  single owner of "which tickers ship by default". Closes CONCERNS.md #9.

- **D-05:** After `init_database()` + `seed_defaults()` run, `lifespan`
  queries the `watchlist` table and passes that list to
  `source.start(tickers)`. Replaces Phase 1's temporary
  `list(SEED_PRICES.keys())` call at `backend/app/lifespan.py:39`. Aligns with
  PLAN.md §6: "the set of tickers tracked by the price cache is the union of
  all tickers in the watchlist table."

- **D-06:** `backend/market_data_demo.py` is refactored to reuse
  `list(SEED_PRICES.keys())` instead of its own `TICKERS` list. Completes the
  drift cleanup for CONCERNS.md #9. Cosmetic — demo is not runtime code —
  but trivial while we're in the area.

### DB Path Configuration

- **D-07:** Path resolution reads `os.environ.get("DB_PATH", "db/finally.db")`
  in `lifespan` startup. Matches Phase 1 pattern (python-dotenv loads `.env`
  in `main.py` before `FastAPI(lifespan=lifespan)` is constructed). Prod
  Docker sets `DB_PATH=/app/db/finally.db`; local dev uses the default; tests
  set `DB_PATH` to a `tmp_path`-derived value.

- **D-08:** `DB_PATH` is documented in the eventual `.env.example` (Phase 9
  OPS-04) with a commented default line. Keeps all runtime knobs in one place
  for future contributors.

- **D-09:** Before `sqlite3.connect(DB_PATH)`, `lifespan` ensures the parent
  directory exists via `Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)`.
  Idempotent, no-op when the dir is already there — covers first-run on an
  empty named volume and a fresh local clone where `db/` may not exist yet.

### Claude's Discretion

Planner may pick the conventional answer without re-asking.

- **DB module layout.** A single `backend/app/db/` sub-package (matches the
  `backend/app/market/` pattern) is the Recommended default — short files,
  relative imports, public surface re-exported via `__init__.py`. PLAN.md §4's
  alternate `backend/db/` + `backend/app/db/` split is acceptable if the
  schema is a raw `.sql` file; not preferred for stdlib-sqlite3 strings.

- **Schema definition style.** Python string constants in an `app/db/schema.py`
  module are the Recommended default (consistent with `seed_prices.py` style —
  module-level constants, inspectable at import). Raw `.sql` files are fine
  too; pick based on ergonomics during planning.

- **Idempotent DDL + seed.** `CREATE TABLE IF NOT EXISTS` for every table and
  `INSERT OR IGNORE` (or a pre-SELECT-COUNT guard) for the `users_profile` and
  `watchlist` seeds satisfies Success Criterion #3 ("restart is a no-op, no
  duplicate seed rows, no schema errors"). Planner picks the specific SQL.

- **PRAGMAs.** `PRAGMA foreign_keys = ON` if FKs are declared in the schema.
  WAL journal mode is a stretch (improves reader/writer concurrency but not
  required for a single-user app). Planner decides.

- **Test isolation.** Conftest fixture that sets `DB_PATH` to `tmp_path /
  "test.db"` (or a parameter on a `_build_app`-style helper like the Phase 1
  test pattern in `01-03-SUMMARY.md`). Planner writes the fixture.

- **Lifespan ordering.** Open DB → `init_database()` → `seed_defaults()` →
  construct `PriceCache` → query watchlist → `create_market_data_source` →
  `source.start(tickers)` → mount SSE router. Planner locks exact order
  alongside Phase 1's decisions in `01-CONTEXT.md` (D-04 SSE mount stays
  during startup).

- **Error handling.** Follow `CONVENTIONS.md`: narrow exception handling only
  where crossing boundaries. Don't wrap every DB call. A corrupt / unreadable
  DB file should fail loud, not get silently re-seeded.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification (THE source of truth)
- `planning/PLAN.md` §7 — Full schema for all 6 tables, column types, UNIQUE
  constraints, and default seed data (cash balance, 10 tickers).
- `planning/PLAN.md` §4 — Directory layout (mention of `backend/db/` +
  runtime volume at `db/`).
- `planning/PLAN.md` §5 — Environment variables (`.env` conventions Phase 1
  already follows; `DB_PATH` slots in alongside the three existing vars).
- `planning/PLAN.md` §6 — "Set of tickers tracked = union of watchlist
  rows" — the contract behind D-05.

### Project planning
- `.planning/REQUIREMENTS.md` — DB-01, DB-02, DB-03 (the three requirements
  this phase delivers).
- `.planning/ROADMAP.md` — Phase 2 "Success Criteria" (all four must evaluate
  TRUE: schema created, seed inserted, restart is no-op, data survives
  container restart on the volume).
- `.planning/PROJECT.md` — Constraints (stdlib `sqlite3`, no migrations,
  single-file DB at `db/finally.db`, no over-engineering).
- `.planning/phases/01-app-shell-config/01-CONTEXT.md` — Phase 1 decisions
  that Phase 2 builds on (two-file module split; `app.state` for shared
  objects; `load_dotenv()` before `app = FastAPI(...)`; lifespan ownership of
  startup/shutdown).

### Codebase intel
- `.planning/codebase/CONCERNS.md` §"Code-Level Concerns" item 9 — default
  seed tickers duplicated across `seed_prices.py` and `market_data_demo.py`;
  Phase 2 DB seed must not add a third copy (D-04, D-05, D-06 resolve this).
- `.planning/codebase/CONCERNS.md` §"Architectural Risks" items 6, 7 —
  `session_start_price` is session-relative and must NOT be persisted;
  SQLite + single process is fine for single-user.
- `.planning/codebase/CONVENTIONS.md` — Module docstrings,
  `from __future__ import annotations`, `%`-style logging, narrow exception
  handling, no emojis.
- `.planning/codebase/STRUCTURE.md` — Package layout conventions (sub-packages
  like `app/market/` with public re-exports in `__init__.py`).

### Reusable code touched by Phase 2
- `backend/app/lifespan.py` — Extend the existing startup: open DB before
  building PriceCache; replace the `list(SEED_PRICES.keys())` call at line 39
  with a watchlist query post-seed; close DB in the `finally:` branch.
- `backend/app/main.py` — No changes expected (`load_dotenv()` already runs
  at line 16 before `app = FastAPI(lifespan=lifespan)` at line 20; `DB_PATH`
  is picked up via the same env flow).
- `backend/app/market/seed_prices.py` — The canonical `SEED_PRICES` dict
  whose keys drive the DB seed (D-04).
- `backend/market_data_demo.py` — Refactored to import `SEED_PRICES` (D-06).
- `backend/CLAUDE.md` — Public `app.market` import surface — extend with an
  `app.db` surface after this phase lands.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`app.state` pattern from Phase 1** (`backend/app/lifespan.py:42-43`) —
  `app.state.price_cache = cache`, `app.state.market_source = source`.
  Phase 2 adds `app.state.db = conn` alongside them.
- **`python-dotenv` already wired** (`backend/app/main.py:7, 16`) — `DB_PATH`
  is read via `os.environ.get("DB_PATH", ...)` without any new deps.
- **`SEED_PRICES`** (`backend/app/market/seed_prices.py:4-15`) — the 10-ticker
  canonical list used by D-04 (DB seed) and D-06 (demo refactor).
- **Lifespan shutdown pattern** (`backend/app/lifespan.py:51-55`) —
  `try:/yield/finally:` with `await source.stop()`. Add `conn.close()` in the
  same `finally:`.

### Established Patterns
- Factory-closure for shared dependencies (`create_market_data_source(cache)`,
  `create_stream_router(cache)`). If the DB layer needs a closure-style
  builder, follow the same shape (`init_database(path) -> Connection`).
- Sub-packages expose public names via `__init__.py` (`backend/app/market/__init__.py`).
  `backend/app/db/__init__.py` should do the same.
- `from __future__ import annotations` at the top of every new module.
- `logger = logging.getLogger(__name__)` with `%`-style formatting in
  lifecycle log lines (e.g., `logger.info("DB initialized at %s", DB_PATH)`).
- Narrow exception handling only at boundaries — no defensive try/except
  around DB ops. A missing DB dir is handled by `mkdir(exist_ok=True)` (D-09),
  not `try/except FileNotFoundError`.

### Integration Points
- `backend/app/lifespan.py` is the one file that changes in Phase 2's runtime
  flow. DB init happens before `PriceCache()`; watchlist query happens before
  `source.start(tickers)`.
- `backend/app/__init__.py` is a one-line stub — `app/db/` slots in next to
  `app/market/`.
- Phase 1 test pattern (`_build_app` helper constructing a fresh
  `FastAPI(lifespan=lifespan)` per test, see 01-03 SSE tests) applies here
  too — test fixtures override `DB_PATH` to a `tmp_path` before building
  the app.

</code_context>

<specifics>
## Specific Ideas

- User accepted all three Recommended options for **Connection strategy**
  (long-lived on `app.state`, `sqlite3.Row`, explicit commit) — consistent
  with the Phase 1 "small, incremental, validate each step" pattern and
  stdlib-sqlite3 constraints.
- User deliberately chose to close the CONCERNS.md #9 drift risk now
  (D-04, D-05, D-06) rather than defer — "pick a single source of truth
  before the DB layer copies it a third time" from CONCERNS.md §"Highest-
  Leverage Next Moves" #3 is explicitly delivered here.
- User accepted lifespan startup reading watchlist from DB (D-05) — closes
  the "Planner to wire it so Phase 2's DB-backed watchlist can swap in
  without code churn" forward-reference left by Phase 1 CONTEXT.md.
- `.env.example` (Phase 9 / OPS-04) will include `DB_PATH` — user's call
  on keeping all runtime knobs documented in one place.

</specifics>

<deferred>
## Deferred Ideas

- **WAL journal mode.** Improves reader/writer concurrency; not needed for
  single-user workload. Revisit if/when multi-user AUTH-01 is ever planned.
- **Dataclass row mappers (`Position`, `Trade`, `WatchlistEntry`, etc.).**
  Cleaner typing for handler code in Phases 3–5; not required in Phase 2.
  Phase 3 can introduce them alongside the first real handler that benefits.
- **Schema migrations.** Project constraint explicitly says "no migrations".
  If v2 ever needs to evolve the schema, introduce migrations then —
  probably with `alembic` or a hand-rolled versioned-init pattern.
- **Full PRAGMA tuning pass (`foreign_keys`, `journal_mode`, `synchronous`,
  `cache_size`).** Performance not a Phase 2 concern; defer until a real
  workload reveals a hotspot.
- **`backend/db/` SQL file split (PLAN.md §4).** If schema grows complex
  enough to warrant raw `.sql` files, refactor then. Phase 2 uses Python
  string constants under `app/db/`.

</deferred>

---

*Phase: 02-database-foundation*
*Context gathered: 2026-04-20*
