---
phase: 04-watchlist-api
verified: 2026-04-21T20:20:00Z
status: passed
score: 4/4 success criteria verified
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 4: Watchlist API Verification Report

**Phase Goal:** The user can add, remove, and list tickers, and the market data subsystem starts/stops tracking them immediately without restarts.

**Verified:** 2026-04-21T20:20:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria + Plan must_haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | GET /api/watchlist returns the current watchlist rows, each including the latest price from the in-memory cache | VERIFIED | `test_routes_get.py::TestGetWatchlist::test_returns_ten_seeded_tickers_with_prices` passes — asserts 10 seeded tickers returned with `price is not None` and `direction in ("up","down","flat")`. Service wiring `backend/app/watchlist/service.py:37-83` reads DB rows then calls `cache.get(ticker)` for each. |
| SC-2 | POST /api/watchlist with a new ticker persists it to `watchlist`, onboards it into the market data source on the next tick, and future SSE emissions include that ticker | VERIFIED | `test_routes_post.py::test_add_new_ticker_returns_added_and_source_tracks_it` asserts row count increases by 1 AND `"PYPL" in app.state.market_source.get_tickers()`. `test_add_warms_cache_via_simulator` asserts cache is warmed via simulator seed. SSE stream iterates cache (`app/market/stream.py`), so cache entry guarantees next SSE emission includes ticker. |
| SC-3 | DELETE /api/watchlist/{ticker} removes the row, stops tracking in the cache, and subsequent SSE emissions no longer include that ticker | VERIFIED | `test_routes_delete.py::test_delete_existing_returns_removed` asserts row deleted AND `"AAPL" not in get_tickers()` AND `cache.get("AAPL") is None`. Simulator `remove_ticker` (`app/market/simulator.py:253-257`) calls both `_sim.remove_ticker` and `_cache.remove`. |
| SC-4 | Idempotent semantics: duplicate POST returns 200 status='exists', missing DELETE returns 200 status='not_present' (D-06) | VERIFIED | `test_duplicate_returns_exists_not_409` asserts POST AAPL on seeded DB → 200 `{"ticker":"AAPL","status":"exists"}` with zero DB delta. `test_missing_ticker_returns_not_present_not_404` asserts DELETE ZZZZ → 200 `{"ticker":"ZZZZ","status":"not_present"}`. Service-level `add_ticker` uses `ON CONFLICT(user_id, ticker) DO NOTHING` + rowcount discriminator; `remove_ticker` uses rowcount discriminator. |

**Score:** 4/4 ROADMAP success criteria verified (all truths passed)

### Required Artifacts (Plan 04-01 + Plan 04-02 must_haves)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/watchlist/__init__.py` | Public barrel re-exporting models, service, router | VERIFIED | 43 lines; imports all models + service + router; alphabetized `__all__` includes `create_watchlist_router` |
| `backend/app/watchlist/models.py` | Pydantic v2 schemas + `normalize_ticker` helper | VERIFIED | 77 lines; `_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")`; `WatchlistAddRequest` has `ConfigDict(extra="forbid")` + `@field_validator("ticker", mode="before")`; `WatchlistItem.direction` uses `Literal["up","down","flat"] \| None`; `WatchlistMutationResponse.status` uses `Literal["added","exists","removed","not_present"]` |
| `backend/app/watchlist/service.py` | Pure-function DB service: get/add/remove | VERIFIED | 135 lines; `DEFAULT_USER_ID = "default"`; `AddResult`/`RemoveResult` frozen slots dataclasses; `ON CONFLICT(user_id, ticker) DO NOTHING` present; no FastAPI imports; `%`-style logging |
| `backend/app/watchlist/routes.py` | FastAPI router factory with GET/POST/DELETE | VERIFIED | 95 lines (plan required ≥80); `create_watchlist_router(db, cache, source)`; DB-first choreography; `await source.add_ticker`/`remove_ticker` inside try/except with `exc_info=True`; `HTTPException(status_code=422)` for malformed DELETE path param |
| `backend/app/lifespan.py` | Mounts `create_watchlist_router(conn, cache, source)` natively before yield | VERIFIED | Line 14 imports `from .watchlist import create_watchlist_router`; line 68 `app.include_router(create_watchlist_router(conn, cache, source))   # D-13` runs before `yield` |
| `backend/tests/test_lifespan.py` | Regression test pinning `/api/watchlist` routes | VERIFIED | `test_includes_watchlist_router_during_startup` asserts `/api/watchlist` AND `/api/watchlist/{ticker}` in `app.router.routes` |
| `backend/tests/watchlist/conftest.py` | `fresh_db` + `warmed_cache` fixtures | VERIFIED | Clone of portfolio conftest; both fixtures present |
| `backend/tests/watchlist/test_models.py` | 17 model tests | VERIFIED | 17 tests (normalize_ticker 8, WatchlistAddRequest 4, WatchlistMutationResponse 5); all passing |
| `backend/tests/watchlist/test_service_get.py` | 4 get tests | VERIFIED | Ordering, warm-cache enrichment, cold-cache None fallback, empty watchlist — all passing |
| `backend/tests/watchlist/test_service_add.py` | 3 add tests | VERIFIED | New → added, duplicate → exists, second-add → exists — all passing |
| `backend/tests/watchlist/test_service_remove.py` | 3 remove tests | VERIFIED | Existing → removed, missing → not_present, double-remove idempotent — all passing |
| `backend/tests/watchlist/test_routes_get.py` | GET integration tests (min_lines: 50) | VERIFIED | 104 lines; 3 tests; module-scoped LifespanManager fixture (1 per file) |
| `backend/tests/watchlist/test_routes_post.py` | POST integration tests (min_lines: 80) | VERIFIED | 175 lines; 5 TestPostWatchlist + 6 parametrized TestPostValidation = 11 tests |
| `backend/tests/watchlist/test_routes_delete.py` | DELETE integration tests (min_lines: 60) | VERIFIED | 170 lines; 4 TestDeleteWatchlist + 3 parametrized TestDeletePathValidation = 7 tests |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `service.py::add_ticker` | watchlist table UNIQUE(user_id, ticker) | `ON CONFLICT(user_id, ticker) DO NOTHING` + rowcount | WIRED | Exact pattern found at line 99-103; rowcount discriminator at line 104 |
| `service.py::get_watchlist` | `PriceCache.get(ticker)` | cache-cold None fallback | WIRED | `cache.get(ticker)` at line 57; None branch at lines 58-69; warm branch at 70-81 |
| `models.py::WatchlistAddRequest` | `normalize_ticker` helper | `@field_validator("ticker", mode="before")` | WIRED | Lines 39-42 |
| `routes.py::post_watchlist_route` | `service.add_ticker` | direct call | WIRED | Line 53 `result = service.add_ticker(db, req.ticker)` |
| `routes.py::post_watchlist_route` | `source.add_ticker` | conditional `await` on status=="added" inside try/except | WIRED | Lines 55-64; gated by `result.status == "added"`; WARNING log with `exc_info=True` on failure |
| `routes.py::delete_watchlist_route` | `normalize_ticker` (path-param pre-check) | `ValueError → HTTPException(422)` | WIRED | Lines 73-76 |
| `routes.py::delete_watchlist_route` | `source.remove_ticker` | conditional `await` on status=="removed" inside try/except | WIRED | Lines 80-88 |
| `__init__.py` | `create_watchlist_router` | barrel re-export | WIRED | `from .routes import create_watchlist_router` at line 20; in `__all__` at line 39 |
| `lifespan.py` | `create_watchlist_router` | `app.include_router(...)` before `yield` | WIRED | Import at line 14; mount at line 68 with `# D-13` comment; precedes `yield` at line 77 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|---------------------|--------|
| GET /api/watchlist response | `items[].price`, `direction`, etc. | `PriceCache` populated by `SimulatorDataSource._run_loop` (500ms tick cadence) | Yes — simulator seeds cache on `start()` and continually updates (test `test_returns_ten_seeded_tickers_with_prices` confirms AAPL price is not None) | FLOWING |
| POST /api/watchlist response | `ticker`, `status` | Live DB INSERT result with rowcount discriminator | Yes — SQL commit via `conn.commit()` on rowcount==1 path | FLOWING |
| DELETE /api/watchlist/{ticker} response | `ticker`, `status` | Live DB DELETE result with rowcount discriminator | Yes — SQL commit on rowcount==1 path | FLOWING |
| POST side effect: SSE emissions include new ticker | `cache[ticker]` | `SimulatorDataSource.add_ticker` seeds cache (`app/market/simulator.py:247-250`) | Yes — `test_add_warms_cache_via_simulator` confirms `cache.get("PYPL") is not None` after POST | FLOWING |
| DELETE side effect: SSE emissions drop ticker | `cache[ticker] = None` | `SimulatorDataSource.remove_ticker` calls `self._cache.remove(ticker)` (`app/market/simulator.py:256`) | Yes — `test_delete_existing_returns_removed` confirms `cache.get("AAPL") is None` after DELETE | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Watchlist + lifespan test suite passes | `uv run --extra dev pytest tests/watchlist/ tests/test_lifespan.py -v` | 62 passed | PASS |
| Full backend test suite passes | `uv run --extra dev pytest -q` | 207 passed, 0 failed, 0 errors | PASS |
| Ruff lint clean on watchlist + lifespan files | `uv run --extra dev ruff check app/watchlist/ tests/watchlist/ app/lifespan.py tests/test_lifespan.py` | All checks passed! | PASS |
| Barrel imports resolve | `uv run python -c "from app.watchlist import create_watchlist_router, get_watchlist, add_ticker, remove_ticker, WatchlistAddRequest, WatchlistMutationResponse, normalize_ticker, AddResult, RemoveResult; print('barrel ok')"` | `barrel ok` | PASS |

### Requirements Coverage

All phase requirement IDs (WATCH-01, WATCH-02, WATCH-03) cross-referenced against REQUIREMENTS.md and implementation.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WATCH-01 | 04-01, 04-02 | GET /api/watchlist returns user's watchlist with latest prices from the cache | SATISFIED | `service.get_watchlist(conn, cache)` + `routes.py::get_watchlist_route` + 4 service tests + 3 integration tests (`test_routes_get.py`) all green |
| WATCH-02 | 04-01, 04-02 | POST /api/watchlist adds a ticker; unknown symbols onboarded into market source on next tick | SATISFIED | `service.add_ticker` with `ON CONFLICT DO NOTHING` + `routes.py::post_watchlist_route` with conditional `await source.add_ticker` + 3 service tests + 5 happy-path + 6 validation integration tests all green |
| WATCH-03 | 04-01, 04-02 | DELETE /api/watchlist/{ticker} removes a ticker and stops tracking in cache | SATISFIED | `service.remove_ticker` with rowcount discriminator + `routes.py::delete_watchlist_route` with conditional `await source.remove_ticker` + 3 service tests + 4 happy-path + 3 path-validation integration tests all green |

No orphaned requirements — REQUIREMENTS.md maps only WATCH-01/02/03 to Phase 4, and all three are claimed by plan frontmatter.

### Anti-Patterns Found

None. Scan of modified files in this phase revealed no blockers, warnings, or concerning patterns:

| File | Scan Result |
|------|-------------|
| `backend/app/watchlist/__init__.py` | Clean — no TODO/FIXME/placeholder, no stub returns |
| `backend/app/watchlist/models.py` | Clean — no defensive empty returns outside of legitimate `| None` type annotations for cache-cold contract |
| `backend/app/watchlist/service.py` | Clean — `%`-style logging; narrow mutation paths; no FastAPI imports (enforces D-02) |
| `backend/app/watchlist/routes.py` | Clean — narrow `try/except Exception` scoped to `await source.*_ticker` only (log-and-continue per D-11); `%`-style logging with `exc_info=True` |
| `backend/app/lifespan.py` | Clean — 2-line addition; no churn |
| `backend/tests/watchlist/test_routes_*.py` | Clean — explicit `finally:` restoration blocks ensure module-scoped fixture isolation; strict `== before + 1` arithmetic |

Minor notes (all acceptable):
- Deprecation warnings on `asyncio.DefaultEventLoopPolicy` (Python 3.14+ / slated 3.16 removal) — inherited from project-level `tests/conftest.py` pattern, not introduced by Phase 4.
- No emojis in code or logs (verified).

### Human Verification Required

None. All success criteria are covered by automated integration tests that exercise the real lifespan with a live `SimulatorDataSource`. The VALIDATION.md documents one manual-only verification item ("SSE stream reflects watchlist add/remove end-to-end"), but explicitly scopes it to **Phase 10 Playwright** — outside Phase 4's boundary. The Phase 4 surface is fully covered automatically through:
- Module-scoped `LifespanManager` + `httpx.AsyncClient` (real FastAPI startup, real router mount, real DB, real simulator).
- `test_add_warms_cache_via_simulator` + `test_delete_existing_returns_removed` prove the SSE-visible state (cache contents) changes atomically with each mutation.

### Gaps Summary

No gaps. All four ROADMAP success criteria pass with direct integration-test evidence. All three requirement IDs (WATCH-01, WATCH-02, WATCH-03) are satisfied. All must_haves from both plan frontmatters (04-01 and 04-02) are present and wired. Full suite: 207/207 green, ruff clean, barrel importable.

Phase is ready to proceed to Phase 5 (AI Chat Integration), which per the plan's hand-off notes reuses `from app.watchlist import add_ticker, remove_ticker` directly — the FastAPI-agnostic service layer (D-02) is the key enabler.

---

*Verified: 2026-04-21T20:20:00Z*
*Verifier: Claude (gsd-verifier)*
