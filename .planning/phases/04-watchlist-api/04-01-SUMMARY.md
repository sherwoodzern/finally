---
phase: 04-watchlist-api
plan: 01
subsystem: api
tags: [fastapi, pydantic-v2, sqlite3, watchlist, service, models]

# Dependency graph
requires:
  - phase: 02-database-foundation
    provides: watchlist table with UNIQUE(user_id, ticker), init_database, seed_defaults
  - phase: 01-app-shell-config
    provides: PriceCache, MarketDataSource (for downstream 04-02 only)
provides:
  - normalize_ticker helper + WatchlistAddRequest/Item/Response/MutationResponse Pydantic v2 schemas
  - Pure-function service: get_watchlist, add_ticker, remove_ticker with idempotent no-op semantics
  - AddResult/RemoveResult dataclass results with Literal status discriminator
  - Full package barrel app.watchlist (minus router; added in 04-02)
affects: [04-02-watchlist-routes, 05-chat-llm-auto-exec]

# Tech tracking
tech-stack:
  added: []  # No new dependencies; all already installed (pydantic 2.12.5, sqlite3 stdlib)
  patterns:
    - "normalize_ticker module-level helper reused by Pydantic field_validator + future DELETE path-param"
    - "INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING + cursor.rowcount for idempotent add"
    - "DELETE + cursor.rowcount for idempotent remove"
    - "status-literal response (added|exists|removed|not_present) instead of 4xx on no-op path"
    - "@dataclass(frozen=True, slots=True) AddResult/RemoveResult return types"

key-files:
  created:
    - backend/app/watchlist/__init__.py
    - backend/app/watchlist/models.py
    - backend/app/watchlist/service.py
    - backend/tests/watchlist/__init__.py
    - backend/tests/watchlist/conftest.py
    - backend/tests/watchlist/test_models.py
    - backend/tests/watchlist/test_service_get.py
    - backend/tests/watchlist/test_service_add.py
    - backend/tests/watchlist/test_service_remove.py
  modified: []

key-decisions:
  - "D-01: watchlist/ sub-package mirrors portfolio/ (models + service + __init__ in this plan; routes in 04-02)"
  - "D-02: Service takes sqlite3.Connection + PriceCache only — no MarketDataSource, no FastAPI imports — reusable by Phase 5 chat auto-exec"
  - "D-03: Pydantic v2 BaseModel everywhere; extra='forbid' on request bodies only"
  - "D-04: normalize_ticker at the Pydantic edge via field_validator(mode='before') with regex ^[A-Z][A-Z0-9.]{0,9}$; service trusts its input"
  - "D-05: Cache-cold GET falls back to None on every price field (never 0, never omitted)"
  - "D-06: Idempotent mutation returns AddResult(status='exists') / RemoveResult(status='not_present') — no exception, no 409/404"
  - "D-08: GET ordering ORDER BY added_at ASC, ticker ASC (same as get_watchlist_tickers)"
  - "D-09: add_ticker uses INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING + rowcount==1 discriminator; one query, atomic, race-free"
  - "D-12: UNIQUE(user_id, ticker) constraint already in place from Phase 2; no schema change needed"

patterns-established:
  - "Idempotent mutation without exceptions: cursor.rowcount == 1 → commit + status='added'/'removed'; rowcount == 0 → no-commit + status='exists'/'not_present'"
  - "Service-as-pure-functions-on-(conn, cache, *args): FastAPI-agnostic, reusable from any async handler"
  - "Unit test structure: TestClass per function with class-level fixtures (fresh_db, warmed_cache from conftest)"

requirements-completed: [WATCH-01, WATCH-02, WATCH-03]

# Metrics
duration: 4m 14s
completed: 2026-04-21
---

# Phase 4 Plan 1: Watchlist Models + Service Summary

**Pydantic v2 watchlist schemas + pure-function DB service using INSERT ... ON CONFLICT DO NOTHING + cursor.rowcount for idempotent add/remove (zero FastAPI imports, ready for Phase 5 chat reuse).**

## Performance

- **Duration:** 4m 14s
- **Started:** 2026-04-21T19:52:15Z
- **Completed:** 2026-04-21T19:56:29Z
- **Tasks:** 3 (all autonomous)
- **Files created:** 9

## Accomplishments

- `normalize_ticker(value: str) -> str` module-level helper: strip/upper/regex-validate with `^[A-Z][A-Z0-9.]{0,9}$` — ready to be shared by Pydantic `WatchlistAddRequest` (in place) and the Plan 04-02 DELETE path-param pre-check.
- `WatchlistAddRequest` with `ConfigDict(extra="forbid")` + `@field_validator("ticker", mode="before")` — malformed bodies produce 422 at the FastAPI edge without touching the service.
- `WatchlistItem`, `WatchlistResponse`, `WatchlistMutationResponse` (response models) — `direction` uses `Literal["up", "down", "flat"] | None` matching `PriceUpdate.direction` verbatim; `status` uses `Literal["added", "exists", "removed", "not_present"]` for the idempotent mutation discriminator.
- Pure-function service with three public entry points:
  - `get_watchlist(conn, cache)` — `ORDER BY added_at ASC, ticker ASC` (D-08); cold-cache tickers get `None` on every price field (D-05).
  - `add_ticker(conn, ticker)` — one `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING` + `cursor.rowcount` branch; returns `AddResult` with status `"added"` (rowcount==1, commit) or `"exists"` (rowcount==0, no commit).
  - `remove_ticker(conn, ticker)` — one `DELETE` + `cursor.rowcount` branch; returns `RemoveResult` with status `"removed"` or `"not_present"`. Never raises.
- Package barrel (`app.watchlist`) re-exports models + service with alphabetized `__all__`. Router intentionally excluded — Plan 04-02 adds it.
- 27 new unit tests (17 model, 4 get-service, 3 add-service, 3 remove-service) — all green. Full backend suite regression: 185/185 passing (was 158; +27 new, no regressions). Ruff clean.

## Task Commits

1. **Task 1: Wave 0 — test package scaffolding + fixtures** — `05ccc9f` (test)
2. **Task 2: models.py — normalize_ticker + Pydantic v2 schemas + unit tests** — `8617bf7` (feat)
3. **Task 3: service.py — get/add/remove pure functions + unit tests + package __init__** — `db9d709` (feat)

## Files Created/Modified

### Created

- `backend/app/watchlist/__init__.py` — package barrel re-exporting models + service (no router yet; alphabetized `__all__`).
- `backend/app/watchlist/models.py` — `normalize_ticker` helper, `_TICKER_RE` regex, `WatchlistAddRequest` (extra='forbid'), `WatchlistItem`, `WatchlistResponse`, `WatchlistMutationResponse`.
- `backend/app/watchlist/service.py` — `DEFAULT_USER_ID`, `AddResult`/`RemoveResult` frozen dataclasses, `get_watchlist`/`add_ticker`/`remove_ticker` functions.
- `backend/tests/watchlist/__init__.py` — test package marker.
- `backend/tests/watchlist/conftest.py` — `fresh_db` + `warmed_cache` fixtures (clone of tests/portfolio/conftest.py).
- `backend/tests/watchlist/test_models.py` — 17 tests: normalize_ticker (8), WatchlistAddRequest (4), WatchlistMutationResponse literals (5).
- `backend/tests/watchlist/test_service_get.py` — 4 tests: ordering, warm-cache enrichment, cold-cache None fallback, empty-watchlist empty items.
- `backend/tests/watchlist/test_service_add.py` — 3 tests: new ticker → added + row inserted, duplicate → exists (no error), second-add → exists.
- `backend/tests/watchlist/test_service_remove.py` — 3 tests: existing → removed + row gone, missing → not_present (no error), idempotent double-remove.

### Modified

- None. Plan 04-01 is greenfield additive — no edits to `lifespan.py`, `db/schema.py`, `portfolio/`, etc.

## Decisions Made

See frontmatter `key-decisions` for the full list. All decisions were locked in `04-CONTEXT.md` (D-01..D-13) during the discuss phase and applied verbatim here — no new decisions were made during execution.

## Deviations from Plan

None significant. One minor text edit for acceptance-criterion strictness:

### Adjustments

**1. [Acceptance-criterion strictness] Removed `create_watchlist_router` forward-reference from `__init__.py` docstring**

- **Found during:** Task 3 acceptance-criterion check
- **Issue:** Plan's initial docstring template included the line `Router: create_watchlist_router (added in Plan 04-02)`. The acceptance criterion "grep 'create_watchlist_router' backend/app/watchlist/__init__.py prints nothing" was intended to verify the symbol was not imported here, but the literal grep matched the docstring forward-reference.
- **Fix:** Replaced the docstring line "Router: create_watchlist_router (added in Plan 04-02)" with the paragraph header "Public API (Plan 04-01 — HTTP router lands in Plan 04-02):" so the file contains zero string matches for `create_watchlist_router`.
- **Files modified:** `backend/app/watchlist/__init__.py` (docstring only; imports + `__all__` unchanged)
- **Verification:** `grep -c "create_watchlist_router" backend/app/watchlist/__init__.py` → 0
- **Committed in:** `db9d709` (Task 3 commit; the final docstring text is what landed in the commit — no amend).

---

**Total deviations:** 1 minor text adjustment (neither correctness nor security; satisfies literal-grep acceptance criterion).
**Impact on plan:** Zero scope change. Router addition still lands in Plan 04-02 exactly as specified.

## Issues Encountered

None. All three tasks ran cleanly on the first verification pass.

## User Setup Required

None — no external service configuration required. All dependencies were already present in `backend/pyproject.toml` (pydantic 2.12.5, pytest, sqlite3 stdlib, etc.). No env-var changes. No Docker rebuild.

## Next Phase Readiness

**Plan 04-02 hand-off** (same phase, next plan):

- `create_watchlist_router(db, cache, source)` factory will import:
  - `from . import service` — get the three pure functions.
  - `from .models import WatchlistAddRequest, WatchlistMutationResponse, normalize_ticker` — request body model for POST, response model for POST + DELETE, helper for DELETE path-param 422 pre-check.
- The service's `AddResult.status == "added"` / `RemoveResult.status == "removed"` discriminator is what 04-02 branches on to decide whether to `await source.add_ticker(ticker)` / `await source.remove_ticker(ticker)` after the DB write (D-09, D-10).
- Plan 04-02 will edit `backend/app/watchlist/__init__.py` to add `create_watchlist_router` to the imports and `__all__` (preserving alphabetization). The docstring line "Public API (Plan 04-01 — HTTP router lands in Plan 04-02):" should be updated to reflect the complete public API at that point.
- Plan 04-02 will also edit `backend/app/lifespan.py` to mount the router: `app.include_router(create_watchlist_router(conn, cache, source))` after the portfolio router mount (D-13).

**Downstream Phase 5 (chat LLM auto-exec) hand-off:**

- Phase 5's chat handler imports `from app.watchlist import add_ticker, remove_ticker` directly — no FastAPI layer involved. The pure-function service design (D-02) is already validated here.

## Self-Check: PASSED

Files created (all found):
- FOUND: backend/app/watchlist/__init__.py
- FOUND: backend/app/watchlist/models.py
- FOUND: backend/app/watchlist/service.py
- FOUND: backend/tests/watchlist/__init__.py
- FOUND: backend/tests/watchlist/conftest.py
- FOUND: backend/tests/watchlist/test_models.py
- FOUND: backend/tests/watchlist/test_service_get.py
- FOUND: backend/tests/watchlist/test_service_add.py
- FOUND: backend/tests/watchlist/test_service_remove.py

Commits (all found via `git log --all`):
- FOUND: 05ccc9f (Task 1)
- FOUND: 8617bf7 (Task 2)
- FOUND: db9d709 (Task 3)

Test suite: 185/185 passing (was 158; +27 new). Ruff clean on `app/watchlist/` + `tests/watchlist/`. Barrel import confirmed: `from app.watchlist import add_ticker, remove_ticker, get_watchlist, WatchlistAddRequest, normalize_ticker, AddResult, RemoveResult, WatchlistMutationResponse, DEFAULT_USER_ID` → ok.

---
*Phase: 04-watchlist-api*
*Completed: 2026-04-21*
