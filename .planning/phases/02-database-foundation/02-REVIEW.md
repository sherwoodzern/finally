---
phase: 02-database-foundation
reviewed: 2026-04-20T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - backend/app/db/__init__.py
  - backend/app/db/schema.py
  - backend/app/db/connection.py
  - backend/app/db/seed.py
  - backend/app/lifespan.py
  - backend/market_data_demo.py
  - backend/tests/conftest.py
  - backend/tests/db/__init__.py
  - backend/tests/db/test_schema.py
  - backend/tests/db/test_seed.py
  - backend/tests/db/test_persistence.py
  - backend/tests/db/test_demo_refactor.py
  - backend/tests/test_lifespan.py
  - backend/tests/test_main.py
findings:
  critical: 0
  warning: 0
  info: 5
  total: 5
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 2 delivers a small, focused SQLite foundation: a six-table schema (`schema.py`),
a minimal connection helper (`connection.py`), an idempotent seeder (`seed.py`), and
wiring into the FastAPI lifespan (`lifespan.py`). The demo was refactored to derive
its ticker list from `SEED_PRICES` (single source of truth). Tests cover DB-01 (schema),
DB-02 (seed), DB-03 (persistence), and the lifespan integration end-to-end.

No Critical or Warning issues found. Code adheres to project style rules:
`from __future__ import annotations` where annotations appear, `%`-style logger
calls, PEP 604/585 types, frozen/idempotent semantics, no emojis, and narrow error
handling. Seed logic correctly guards against re-inserting a user-deleted ticker by
using a `COUNT(*) = 0` check instead of `INSERT OR IGNORE` — a deliberate
forward-compatibility decision for Phase 4.

Five Info items are cosmetic / maintainability nits; none block the phase.

## Info

### IN-01: Unused `logger` in `seed.py`

**File:** `backend/app/db/seed.py:13`
**Issue:** `logger = logging.getLogger(__name__)` is declared but never invoked.
`init_database` and `seed_defaults` complete silently; a single `logger.info(
"Seeded default user + %d tickers", len(SEED_PRICES))` on first seed would be
consistent with `connection.py:23` (`"DB opened at %s"`) and the lifespan log line.
**Fix:**
```python
if existing == 0:
    for ticker in SEED_PRICES:
        conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) "
            "VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now),
        )
    logger.info("Seeded default watchlist with %d tickers", len(SEED_PRICES))
```
Either add a log call on the seed path or drop the unused `logger` binding.

### IN-02: Dead fallback in `print_summary` — `SEED_PRICES.get(ticker, 0)`

**File:** `backend/market_data_demo.py:182, 187`
**Issue:** `TICKERS = list(SEED_PRICES.keys())` at module load (line 30), so the
`.get(ticker, 0)` default and the `if seed else 0` branch at line 187 are
unreachable — every ticker iterated through `print_summary` is guaranteed to
exist in `SEED_PRICES`. This is the kind of defensive fallback CLAUDE.md warns
against ("Do not program defensively"). The reader has to reason about a `0`
seed case that cannot happen.
**Fix:**
```python
for ticker in TICKERS:
    seed = SEED_PRICES[ticker]
    update = cache.get(ticker)
    if update is None:
        continue
    final = update.price
    session_change = ((final - seed) / seed) * 100
```

### IN-03: Unused `elapsed` parameter in `build_table`

**File:** `backend/market_data_demo.py:54-58`
**Issue:** `build_table(cache, history, elapsed)` accepts `elapsed: float` but
never references it in the body. The caller at line 156 still passes it. This is
a latent signature drift from an earlier version where the table presumably
showed elapsed time.
**Fix:** Drop the parameter and update the single caller:
```python
def build_table(cache: PriceCache, history: dict[str, deque]) -> Table:
    ...

# caller
build_table(cache, history),
```

### IN-04: Missing `from __future__ import annotations` in two modules

**File:** `backend/app/db/__init__.py:1`, `backend/app/db/schema.py:1`
**Issue:** The project's observed convention (per `CLAUDE.md` "Every module
uses `from __future__ import annotations`") is applied consistently in
`connection.py`, `seed.py`, and `lifespan.py`, but omitted in `__init__.py` and
`schema.py`. Both modules function correctly today (no annotations need
forward-reference deferral), but adding the import now prevents surprises if
type hints are added later (e.g., to `SCHEMA_STATEMENTS`).
**Fix:** Add `from __future__ import annotations` as the first non-docstring
line in both files, matching the rest of the package.

### IN-05: Wide `except KeyboardInterrupt: pass` — consider narrowing or logging

**File:** `backend/market_data_demo.py:263-264`
**Issue:** The demo catches `KeyboardInterrupt` with a bare `pass`. This is the
intended clean-exit path (the user hits Ctrl+C to stop the 60-second demo
early), so this is not strictly an anti-pattern — but the project convention
(per `CLAUDE.md` "If you catch, log (and say why you caught in a comment)")
favors an inline rationale. Current code relies on the reader inferring intent
from context.
**Fix:** Add a one-line comment or trivial debug log:
```python
except KeyboardInterrupt:
    # User hit Ctrl+C - fall through to print_summary in the finally block.
    pass
```

---

## Notes — Strengths

- **Seed contract is correct and well-documented.** The `COUNT(*) = 0` guard in
  `seed.py:45-56` protects a user-deleted ticker from being silently re-inserted
  on restart — a subtle but important forward-compatibility decision, and the
  docstring spells out why. `test_reseed_does_not_re_add_deleted_ticker` pins it.
- **Single source of truth for tickers.** `SEED_PRICES` is the one canonical
  list; the DB seed iterates it, the demo derives its `TICKERS` from it, and
  `test_demo_refactor.py` pins the equivalence. Closes the drift risk that was
  called out in the project `CLAUDE.md` "Anti-patterns" section.
- **Lifespan ordering is correct.** `open_database -> init_database ->
  seed_defaults -> PriceCache -> create_market_data_source ->
  get_watchlist_tickers(conn) -> source.start(tickers)` — the market source
  receives its ticker list from the DB, not directly from `SEED_PRICES`. This is
  the D-05 contract from `02-CONTEXT.md`, and `test_tickers_come_from_db_watchlist`
  verifies it.
- **Shutdown is clean.** The `try: yield finally: await source.stop(); conn.close()`
  pattern in `lifespan.py:60-64` correctly orders task cancellation before DB close.
- **Test isolation is solid.** The `db_path` fixture in `conftest.py` combined
  with `patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True)` gives each
  lifespan test a fresh SQLite file and a clean environment. The docstring
  explicitly warns callers about the `clear=True` interaction — good defense
  against a subtle test bug.
- **Connection semantics are documented.** `connection.py:12-24` spells out
  `check_same_thread=False` (D-01), `sqlite3.Row` factory (D-02), and manual-commit
  isolation (D-03), which matches the architectural decisions in `02-CONTEXT.md`.

---

_Reviewed: 2026-04-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
