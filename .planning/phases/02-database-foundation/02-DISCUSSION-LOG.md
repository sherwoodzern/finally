# Phase 2: Database Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 02-database-foundation
**Areas discussed:** Connection strategy, Seed single source of truth, DB path configuration

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| DB layout & schema style | Package layout + schema style (.sql vs Python constants) | |
| Connection strategy | Connection lifetime, thread-safety, row access, commit model | ✓ |
| Seed single source of truth | Where the canonical 10-ticker list lives | ✓ |
| DB path configuration | Env var vs hardcoded vs injected; test isolation; parent-dir creation | ✓ |

**User's choice:** Connection strategy, Seed single source of truth, DB path configuration
**Notes:** Layout & schema style deferred to Claude's Discretion — conventional sub-package pattern (`backend/app/db/`) with Python string constants fits project norms.

---

## Connection Strategy

### Q1: How should the SQLite connection be managed across the app's lifetime?

| Option | Description | Selected |
|--------|-------------|----------|
| One long-lived conn on app.state (Recommended) | sqlite3.Connection opened at lifespan startup, attached to app.state.db, closed on shutdown. check_same_thread=False. | ✓ |
| Open-per-call helper | get_db() opens a fresh connection per call. Simpler, loses app.state pattern. | |
| FastAPI dependency (yield) | Depends(get_db) yields per-request connection. Extra ceremony for stdlib sqlite3 without ORM. | |

**User's choice:** One long-lived connection on `app.state` (Recommended).
**Notes:** Matches Phase 1 PriceCache precedent.

### Q2: Row access style for DB reads?

| Option | Description | Selected |
|--------|-------------|----------|
| sqlite3.Row factory (Recommended) | row_factory = sqlite3.Row — dict-like access by column name. | ✓ |
| Raw tuples | Positional tuples, slightly faster, brittle across callers. | |
| Dataclass mapping layer | Per-table dataclasses; more code; deferrable to Phase 3/4. | |

**User's choice:** sqlite3.Row factory (Recommended).
**Notes:** Dataclass mappers deferred.

### Q3: How should DB writes be committed?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit conn.commit() after each op (Recommended) | Default isolation_level, manual commits. Keeps transactional grouping possible for Phase 3. | ✓ |
| Autocommit mode | isolation_level=None, every execute commits. Simpler, loses batch option. | |

**User's choice:** Explicit conn.commit() after each op (Recommended).

---

## Seed Single Source of Truth

### Q1: Where should the canonical list of 10 default tickers live for the DB seed?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse SEED_PRICES.keys() (Recommended) | DB seeder imports SEED_PRICES from app/market/seed_prices.py; list(SEED_PRICES.keys()) is canonical. | ✓ |
| Extract new DEFAULT_WATCHLIST constant | Plain list separate from SEED_PRICES; one more constant, decouples "watched" from "simulator-tuned". | |
| Hardcode in DB seed module | Accept three copies (CONCERNS.md #9 drift risk). | |

**User's choice:** Reuse SEED_PRICES.keys() (Recommended).

### Q2: Should this phase also update lifespan startup to drive ticker set from the DB?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — lifespan reads watchlist from DB after init (Recommended) | Closes Phase 1 forward-reference; aligns with PLAN.md §6 "tracked = union of watchlist rows". | ✓ |
| No — keep lifespan reading SEED_PRICES.keys() | Integration deferred to Phase 4. | |

**User's choice:** Yes — lifespan reads watchlist from DB after init (Recommended).

### Q3: What about market_data_demo.py's duplicate TICKERS list?

| Option | Description | Selected |
|--------|-------------|----------|
| Refactor demo to reuse canonical source (Recommended) | Demo imports list(SEED_PRICES.keys()); fully closes CONCERNS.md #9. | ✓ |
| Leave demo alone | Dev-only script; low drift impact. | |

**User's choice:** Refactor demo to reuse canonical source (Recommended).

---

## DB Path Configuration

### Q1: How should the SQLite file path be resolved at runtime?

| Option | Description | Selected |
|--------|-------------|----------|
| Env var DB_PATH with default 'db/finally.db' (Recommended) | Consistent with Phase 1 env-var pattern; prod Docker sets /app/db/finally.db; tests set tmp_path. | ✓ |
| Hardcoded 'db/finally.db' + test monkeypatch | No env var; couples prod path to Docker CMD/WORKDIR. | |
| Path passed into init_database(path) factory | Function parameter; more decoupled, more ceremony. | |

**User's choice:** Env var DB_PATH with default 'db/finally.db' (Recommended).

### Q2: Should DB_PATH appear in the loaded .env schema?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add to .env.example when it lands (Recommended) | All runtime knobs documented in one place (Phase 9 OPS-04). | ✓ |
| No — Docker-only env var | Not surfaced in .env.example. | |

**User's choice:** Yes — add to .env.example when it lands (Recommended).

### Q3: How should lifespan ensure the directory for DB_PATH exists?

| Option | Description | Selected |
|--------|-------------|----------|
| Create parent dir with mkdir(parents=True, exist_ok=True) (Recommended) | Idempotent; handles empty named volume + fresh local checkout. | ✓ |
| Assume dir exists; crash if missing | Forces caller to pre-create; breaks canonical docker run story. | |

**User's choice:** Create parent dir with mkdir(parents=True, exist_ok=True) (Recommended).

---

## Claude's Discretion

- DB module layout (single `backend/app/db/` sub-package recommended).
- Schema definition style (Python string constants recommended).
- Idempotent DDL + seed (`CREATE TABLE IF NOT EXISTS` + `INSERT OR IGNORE` or SELECT-COUNT guard).
- PRAGMAs (`foreign_keys=ON` if FKs declared; WAL mode deferred).
- Test-isolation fixture (conftest sets `DB_PATH` to `tmp_path`).
- Lifespan ordering (DB → PriceCache → watchlist query → source.start → SSE router).

## Deferred Ideas

- WAL journal mode.
- Dataclass row mappers (Phase 3+).
- Schema migrations (v2 concern if ever).
- Full PRAGMA tuning.
- `backend/db/` SQL-file split (PLAN.md §4 variant).

---

*Discussion: 2026-04-20*
