---
phase: 05-ai-chat-integration
plan: 02
subsystem: chat

tags:
  - chat
  - service
  - auto-exec
  - persistence
  - error-boundary
  - llm
  - sqlite

# Dependency graph
requires:
  - phase: 05-ai-chat-integration (Plan 01)
    provides: ChatClient Protocol, StructuredResponse/TradeAction/WatchlistAction/TradeActionResult/WatchlistActionResult/ChatResponse/HistoryResponse models, MockChatClient, build_messages, CHAT_HISTORY_WINDOW
  - phase: 02-database
    provides: chat_messages schema, init_database, seed_defaults
  - phase: 03-portfolio-api
    provides: execute_trade sync function + TradeValidationError hierarchy (InsufficientCash, InsufficientShares, UnknownTicker, PriceUnavailable)
  - phase: 04-watchlist-api
    provides: add_ticker / remove_ticker sync service + AddResult / RemoveResult dataclasses + routes.py:55-64 source-failure choreography
  - phase: 01-market-data (completed before GSD tracking)
    provides: PriceCache, MarketDataSource interface
provides:
  - app.chat.service.run_turn (async orchestration: persist-user -> LLM -> auto-exec -> persist-assistant)
  - app.chat.service.get_history (two-level-subquery tail-ASC history fetch)
  - app.chat.service.ChatTurnError (single LLM-failure boundary for Plan 03 HTTP 502 mapping)
  - D-12 exception translation table (InsufficientCash/InsufficientShares/UnknownTicker/PriceUnavailable/ValueError -> invalid_ticker / Exception -> internal_error)
  - D-09 watchlist-first auto-exec ordering so "add X and buy X" same-turn produces watchlist status='added' + trade status='failed' error='price_unavailable' (D-11, no retry)
  - D-18 persistence ordering: user row BEFORE client.complete, assistant row AFTER auto-exec with enriched actions JSON
  - Test doubles: FakeChatClient (preset StructuredResponse), RaisingChatClient (preset exception), FakeSource (records add/remove)
affects:
  - 05-03-PLAN (chat routes) — will import run_turn, get_history, ChatTurnError; map ChatTurnError -> HTTPException(502), call run_turn from POST /api/chat, call get_history from GET /api/chat/history

# Tech tracking
tech-stack:
  added: []   # No new runtime dependencies — uses sqlite3 / uuid / json / datetime / asyncio / logging stdlib only
  patterns:
    - "Single broad try/except Exception only around client.complete() (D-14); all other action failures are surfaced as per-action status='failed' entries (D-10)"
    - "Two-step DB+source choreography (mirror watchlist/routes.py:55-64): DB mutation first + commit, then await source.add_ticker/remove_ticker; source exception is WARNING-logged and does NOT downgrade the DB-committed status (D-11, DB = reconciliation anchor)"
    - "Persistence ordering around the LLM call: user row committed BEFORE client.complete() so history stays consistent on failure (D-18)"
    - "Two-level subquery for tail-ASC pagination: SELECT ... FROM (SELECT ... ORDER BY created_at DESC LIMIT ?) ORDER BY created_at ASC (D-19, Pitfall 8)"
    - "Pure service layer — no FastAPI imports in service.py; route layer (Plan 03) owns the HTTP boundary (D-02)"
    - "Exception-subclass catch as tuple (InsufficientCash, InsufficientShares, UnknownTicker, PriceUnavailable) to hit D-12 codes via exc.code without importing the unused base TradeValidationError"

key-files:
  created:
    - backend/app/chat/service.py
    - backend/tests/chat/test_service_run_turn.py
    - backend/tests/chat/test_service_failures.py
    - backend/tests/chat/test_service_persistence.py
  modified:
    - backend/app/chat/__init__.py
    - backend/tests/chat/conftest.py

key-decisions:
  - "D-02 respected: service.py has zero FastAPI imports — HTTPException mapping is owned by Plan 03 routes"
  - "D-09 watchlist-first so one turn can 'add PYPL and buy PYPL' — but D-11 means the trade still fails price_unavailable on cold cache; the frontend can display both events in order"
  - "D-10 continue-on-failure: per-action helpers (_run_one_trade, _run_one_watchlist) NEVER raise; a mid-list failure does not short-circuit the remaining actions"
  - "D-12 exception-to-error-code mapping implemented via TradeValidationError.code lookup (exc.code) and a ValueError fallback for pydantic invalid-ticker. Any other Exception is translated to 'internal_error' with a WARNING log including exc_info"
  - "D-14 ChatTurnError is the ONLY broad try/except Exception in run_turn (around client.complete()). Plan 03 maps it to HTTP 502 detail={'error':'llm_unavailable','message':str(exc)}"
  - "D-18 user-row-commits-before-LLM guarantees the transcript stays consistent on LLM failure; test TestUserTurnBeforeLLM locks this"
  - "D-19 get_history uses a two-level subquery rather than ORDER BY ASC + LIMIT + reverse-in-Python, so SQLite does the work and we avoid full-table scans when rows grow"
  - "Source failure after DB commit (D-11) is logged at WARNING with exc_info and does NOT downgrade the returned WatchlistActionResult — symmetric for both add_ticker and remove_ticker choreography"
  - "Plan text '@history.messages[-1].content == \"world\"' was incorrect — the last row after two MockChatClient turns is the assistant's reply, not the user's message. Test fixed to assert messages[2].content == 'world' (the second user turn, third row)"

patterns-established:
  - "Service-layer purity: all new app.chat.service code is routable-agnostic; import graph is app.chat.service -> app.portfolio.service + app.watchlist.service + app.market + app.chat.{client,models,prompts}, never fastapi"
  - "Per-action result translation helpers (_run_one_trade / _run_one_watchlist) that swallow-and-translate exceptions so the top-level loop is a flat iterator"
  - "Test doubles in conftest.py (FakeChatClient / RaisingChatClient / FakeSource) keep service unit tests free of FastAPI / LifespanManager / httpx — Plan 03 integration tests will swap in the real SimulatorDataSource"

requirements-completed:
  - CHAT-02
  - CHAT-04
  - CHAT-05
  - TEST-01

# Metrics
duration: 45min
completed: 2026-04-22
---

# Phase 05 Plan 02: Chat Service Orchestration Summary

**Async run_turn orchestrator that persists the user turn, calls the LLM, auto-executes watchlist-then-trades with D-12 per-action error translation, and persists an enriched assistant turn — plus get_history and the ChatTurnError LLM-failure boundary.**

## Performance

- **Duration:** ~45 min (test scaffold + GREEN implementation + coverage boost)
- **Started:** 2026-04-22T00:00:00Z (approx. wave-2 executor start)
- **Completed:** 2026-04-22
- **Tasks:** 2 (TDD RED + GREEN — the plan's single orchestration task, split into per-TDD-phase commits)
- **Files modified:** 6 (2 new service files, 3 new test modules, 1 extended conftest, 1 extended package __init__)

## Accomplishments

- `async run_turn(conn, cache, source, client, user_message) -> ChatResponse` orchestrates one complete chat turn with persistence ordering D-18 (user before LLM, assistant after auto-exec).
- D-12 exception translation matrix wired: `InsufficientCash` / `InsufficientShares` / `UnknownTicker` / `PriceUnavailable` / `ValueError` (invalid_ticker) / `Exception` (internal_error). Locked by one test per row.
- D-09 watchlist-first ordering + D-11 cold-cache surfacing: "add PYPL and buy PYPL" produces `watchlist.status='added'` AND `trade.status='failed' error='price_unavailable'` (no retry) in the same turn.
- D-14 `ChatTurnError` is the single broad `try/except Exception` around `client.complete()`; everything else returns per-action `status='failed'` entries.
- D-19 `get_history` uses the two-level subquery for tail-ASC pagination.
- Watchlist add/remove choreography mirrors `watchlist/routes.py:55-64` exactly: DB first, then `await source.add/remove_ticker`; source exception is WARNING-logged and does not downgrade the status.
- `app.chat` line coverage: **99%** (gate 93%); `service.py` coverage **98%**.
- 76 chat-subsystem tests pass (51 from Plan 01 + 25 new in Plan 02); 283 total tests pass; ruff clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: Test scaffolds (RED)** — `75afd2e` (`test(05-02)`). Extended `tests/chat/conftest.py` with `FakeChatClient`, `RaisingChatClient`, `FakeSource`; added `test_service_run_turn.py`, `test_service_failures.py`, `test_service_persistence.py`. Collection fails with `ModuleNotFoundError: app.chat.service` — the expected RED state.
2. **Task 2: Service implementation (GREEN)** — `23ba854` (`feat(05-02)`). Created `backend/app/chat/service.py` (307 lines) with `run_turn`, `get_history`, `ChatTurnError`, `_persist_user_turn`, `_persist_assistant_turn`, `_run_one_trade`, `_run_one_watchlist`. Extended `app/chat/__init__.py` to export the three new public symbols.

_No REFACTOR commit required — service.py shipped at 307 lines (vs 200-line target); all branches clean on first pass after matching ruff unused-import rules._

## Files Created/Modified

### Created

- `backend/app/chat/service.py` — orchestration layer. `run_turn` coroutine, `get_history` pure-sync function, `ChatTurnError` exception class. 307 lines, 85 stmts, 98% coverage.
- `backend/tests/chat/test_service_run_turn.py` — happy-path + watchlist-first + remove + source-failure-after-commit + unexpected-watchlist-error scenarios. 7 tests, all using `MockChatClient` (D-06).
- `backend/tests/chat/test_service_failures.py` — D-12 exception translation matrix (4 tests, one per TradeValidationError subclass) + continue-on-failure + D-09 watchlist-first-with-trade + `internal_error` fallback via `monkeypatch` + D-14 `ChatTurnError` boundary. 8 tests using `FakeChatClient` / `RaisingChatClient`.
- `backend/tests/chat/test_service_persistence.py` — D-18 user-before-LLM, assistant-after-auto-exec with enriched actions JSON, user_id filter, D-19 `get_history` ASC + limit + JSON parse, commit-count (2 on success, 1 on LLM failure). 10 tests.

### Modified

- `backend/app/chat/__init__.py` — added `from .service import ChatTurnError, get_history, run_turn` and three corresponding entries in `__all__`.
- `backend/tests/chat/conftest.py` — appended `mock_chat_client` fixture, `FakeChatClient`, `RaisingChatClient`, `FakeSource` test doubles, and `fake_source` fixture. Existing `fresh_db` and `warmed_cache` fixtures from Plan 01 untouched.

## Decisions Made

See **key-decisions** in frontmatter. Highlights:

- **D-02 respected**: zero FastAPI imports in `service.py`. The route layer (Plan 03) owns HTTPException.
- **D-09 / D-11 interaction**: watchlist-first means "add X and buy X" progresses the watchlist but the trade still fails `price_unavailable` on the cold cache — no retry loop, no polling. The LLM sees the error and can respond in the next turn.
- **D-12 implementation**: tuple-catch `except (InsufficientCash, InsufficientShares, UnknownTicker, PriceUnavailable) as exc` then `exc.code`. This hits all four acceptance-criteria codes via the existing `TradeValidationError.code` attribute without importing the unused base `TradeValidationError` (ruff F401 clean).
- **Two-level subquery for history**: SQLite can push the `LIMIT` into the ORDER-BY DESC subquery and flip to ASC in the outer query — single scan of the tail, not the full table.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test Bug] Fixed `test_returns_rows_asc` assertion**
- **Found during:** Task 1 (RED verification)
- **Issue:** The plan's test text asserted `history.messages[-1].content == "world"`, but after two `MockChatClient` turns the transcript is `[user:"hello", assistant:"mock response", user:"world", assistant:"mock response"]`. The last row is the assistant reply, not the second user turn.
- **Fix:** Changed the assertion to `history.messages[2].content == "world"` (the third row, which is the second user turn) and added `assert history.messages[-1].role == "assistant"` to lock the ordering.
- **Files modified:** `backend/tests/chat/test_service_persistence.py`
- **Verification:** Test passes green; semantics (ASC ordering with four rows) still exercised.
- **Committed in:** `75afd2e` (Task 1 RED commit).

**2. [Rule 2 - Missing Critical Coverage] Added remove-branch + source-failure-on-remove + unexpected-watchlist-error tests**
- **Found during:** Task 2 coverage review (initial service.py coverage 84%)
- **Issue:** Plan's test list only covered the `add` path of `_run_one_watchlist` and the D-12 trade branches — the `remove` branch, `remove`-source-failure symmetric choreography, and the unexpected-watchlist-exception translation (D-12 ValueError + internal_error for watchlist) were not exercised.
- **Fix:** Added `TestRunTurnRemove` (3 tests) and `TestRunTurnWatchlistInternalError` (1 test) to `test_service_run_turn.py`.
- **Files modified:** `backend/tests/chat/test_service_run_turn.py`
- **Verification:** Coverage gate boosted `service.py` from 84% -> 98%; remaining uncovered lines 125 and 215 are the inner `ValueError` branches for `invalid_ticker` (defensive; StructuredResponse normally catches at parse time).
- **Committed in:** `75afd2e` (folded into Task 1 RED commit before Task 2 GREEN).

**3. [Rule 3 - Blocking] Removed unused `FakeSource` imports from test modules**
- **Found during:** Task 1 (ruff F401 before commit)
- **Issue:** `test_service_failures.py` and `test_service_run_turn.py` originally top-level-imported `FakeSource` (and unused `StructuredResponse` / `TradeAction` / `FakeChatClient` in `test_service_persistence.py`) which ruff flagged as unused. The `FakeSource` subclass inside `TestRunTurnSourceFailureAfterAdd` imports locally.
- **Fix:** Removed the unused top-level imports; kept the `from tests.chat.conftest import FakeSource` inside the `BoomSource` test class method (narrow scope).
- **Files modified:** `backend/tests/chat/test_service_run_turn.py`, `backend/tests/chat/test_service_failures.py`, `backend/tests/chat/test_service_persistence.py`
- **Verification:** `uv run --extra dev ruff check app/ tests/` clean.
- **Committed in:** `75afd2e` (Task 1 RED commit).

---

**Total deviations:** 3 auto-fixed (1 test bug, 1 missing critical coverage, 1 blocking lint).
**Impact on plan:** All auto-fixes tightened correctness of the contract documented in the must_haves. No scope creep beyond the plan's acceptance criteria.

## Issues Encountered

None that required abandoning a task. Minor friction:

- Python 3.14 `DeprecationWarning` on `asyncio.DefaultEventLoopPolicy` emits 267 warnings across the suite. Pre-existing (inherited from `tests/conftest.py`), not caused by Plan 02; tracked elsewhere.

## User Setup Required

None - no external service configuration required. `service.py` uses only stdlib (`sqlite3`, `uuid`, `json`, `datetime`, `asyncio`, `logging`) plus already-installed subsystems (`app.portfolio.service`, `app.watchlist.service`, `app.market`, `app.chat.{client,models,prompts}`).

## Next Phase Readiness

**Plan 03 (chat routes) is unblocked.** Plan 03 will:

1. Import `run_turn`, `get_history`, `ChatTurnError` from `app.chat` (all three are now in `__all__`).
2. Wire a factory-closure `create_chat_router(cache, source, client)` returning an `APIRouter`.
3. Map `ChatTurnError` -> `HTTPException(status_code=502, detail={'error': 'llm_unavailable', 'message': str(exc)})` in the `POST /api/chat` handler.
4. Call `get_history(conn, limit=CHAT_HISTORY_WINDOW)` from `GET /api/chat/history`.
5. Compose `ChatRequest` (Plan 01 model) as the request body and return `ChatResponse` (Plan 01 model) as the 200 body.
6. Add httpx-AsyncClient integration tests using `LifespanManager`, the real `SimulatorDataSource`, and `MockChatClient` by default (with `FakeChatClient` for error-path tests).

No blockers. All contracts are stable and locked by 25 new unit tests.

## Self-Check: PASSED

Per role instructions, verifying all claims before returning:

1. **Created files exist on disk:**
   - `backend/app/chat/service.py` — FOUND (307 lines)
   - `backend/tests/chat/test_service_run_turn.py` — FOUND
   - `backend/tests/chat/test_service_failures.py` — FOUND
   - `backend/tests/chat/test_service_persistence.py` — FOUND

2. **Modified files contain expected changes:**
   - `backend/app/chat/__init__.py` — exports `ChatTurnError`, `run_turn`, `get_history` in `__all__`
   - `backend/tests/chat/conftest.py` — contains `class FakeChatClient`, `class RaisingChatClient`, `class FakeSource`, `fake_source` fixture

3. **Commits exist in worktree branch:**
   - `75afd2e` (RED) — FOUND in `git log`
   - `23ba854` (GREEN) — FOUND in `git log`

4. **Acceptance-criteria greps all pass** (see Task 2 commit message body for full verification):
   - `class ChatTurnError`: 1 occurrence
   - `async def run_turn`: 1 occurrence
   - `def get_history`: 1 occurrence
   - `_persist_user_turn`, `_persist_assistant_turn`: 1 occurrence each
   - `from fastapi` in service.py: 0 occurrences (D-02 satisfied)
   - `raise ChatTurnError`: 1 occurrence
   - `ORDER BY created_at DESC LIMIT` subquery: 1 occurrence

5. **Full suite:** 283 passed, 0 failed.
6. **Coverage:** `app.chat` 99% overall, `service.py` 98% (gate 93%).
7. **Lint:** `ruff check app/ tests/` clean.

---
*Phase: 05-ai-chat-integration*
*Completed: 2026-04-22*
