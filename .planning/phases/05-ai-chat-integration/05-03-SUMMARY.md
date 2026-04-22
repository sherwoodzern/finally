---
phase: 05-ai-chat-integration
plan: 03
subsystem: chat

tags:
  - fastapi
  - lifespan
  - chat
  - routes
  - sqlite
  - integration-tests

# Dependency graph
requires:
  - phase: 05-ai-chat-integration (Plan 01)
    provides: ChatClient Protocol, MockChatClient, LiveChatClient, create_chat_client factory, ChatRequest/ChatResponse/HistoryResponse models, build_messages
  - phase: 05-ai-chat-integration (Plan 02)
    provides: async run_turn orchestration, get_history two-level subquery, ChatTurnError LLM-failure boundary, conftest test doubles (FakeChatClient, RaisingChatClient, FakeSource)
  - phase: 04-watchlist-api
    provides: create_watchlist_router factory-closure + lifespan wiring pattern
  - phase: 03-portfolio-api
    provides: create_portfolio_router factory-closure + Query bounds + HTTPException envelope convention
  - phase: 01-app-shell
    provides: app.lifespan.lifespan with DB/cache/source wiring + LifespanManager integration-test harness
provides:
  - backend/app/chat/routes.py (create_chat_router factory-closure APIRouter)
  - POST /api/chat (HTTP edge for run_turn; ChatTurnError -> 502)
  - GET /api/chat/history?limit=N (Query(default=50, ge=1, le=500))
  - Chat router mounted LAST in app.lifespan.lifespan (D-20)
  - create_chat_client() called once at lifespan start; result stored on app.state.chat_client (D-06)
  - D-05 gated startup warning (LLM_MOCK != 'true' AND missing OPENROUTER_API_KEY) with redacted message
  - Three integration-test modules locking CHAT-01/CHAT-05/D-14/D-18 at the HTTP boundary
affects:
  - Phase 06 (or frontend phase) - consumes /api/chat + /api/chat/history
  - Any future multi-user phase - chat routes currently do NOT expose user_id (single-user invariant preserved)

# Tech tracking
tech-stack:
  added: []   # No new runtime or dev dependencies; reuses httpx/asgi-lifespan/pytest-asyncio installed in 01-03
  patterns:
    - "Factory-closure APIRouter mirroring create_watchlist_router / create_portfolio_router - fresh router per call, no module-level state, prefix='/api/chat'"
    - "ChatTurnError -> HTTPException(502, detail={'error':'chat_turn_error','message': str(exc)}) as the SINGLE branch in the route handler; Pydantic v2 extras/min_length/max_length/Query-bounds validation stays at FastAPI's native 422 handler (no custom 422 handler)"
    - "Lifespan wiring sequence: stream -> portfolio -> watchlist -> chat (D-20), with chat_client built via create_chat_client() exactly once and stored on app.state.chat_client before include_router"
    - "D-05 redaction: startup warning uses a fixed string with no format arg for the key value - greppable invariant (! grep -nE '%s.*OPENROUTER_API_KEY' app/lifespan.py)"
    - "Single-user HTTP surface: routes.py never references user_id - run_turn and get_history carry the 'default' user_id internally; enforced as a greppable invariant"
    - "Mini-lifespan pattern (test_routes_llm_errors.py only) for mount-time ChatClient substitution - documented inline because app.lifespan.lifespan rebinds create_chat_client at import time so module-level patch does not intercept"

key-files:
  created:
    - backend/app/chat/routes.py
    - backend/tests/chat/test_routes_chat.py
    - backend/tests/chat/test_routes_history.py
    - backend/tests/chat/test_routes_llm_errors.py
    - .planning/phases/05-ai-chat-integration/05-03-SUMMARY.md
  modified:
    - backend/app/chat/__init__.py
    - backend/app/lifespan.py

key-decisions:
  - "D-01 materialized: create_chat_router(db, cache, source, client) is a fresh APIRouter per call - mirrors D-04 from 01-CONTEXT.md. Zero module-level state."
  - "D-05 materialized: startup warning fires only when LLM_MOCK != 'true' AND OPENROUTER_API_KEY is empty/missing. Message is a fixed string - the key value is never formatted into the log record."
  - "D-06 materialized: create_chat_client() is called exactly once during lifespan startup and the instance is stored on app.state.chat_client; the same instance is passed into create_chat_router via factory closure."
  - "D-14 materialized: service.ChatTurnError -> HTTPException(status_code=502, detail={'error':'chat_turn_error','message': str(exc)}). The envelope key is 'chat_turn_error' (not the Plan-02-era 'llm_unavailable' placeholder mentioned in one spot of 05-02-SUMMARY - the PLAN.md for 05-03 fixes the key name to match the exception class, and routes.py + all tests + docs in this plan agree)."
  - "D-18 invariant proved at the HTTP boundary: a 502 response still leaves exactly ONE new chat_messages row (the user turn). The assistant row is NOT written. test_routes_llm_errors.py's TestLLMFailureBoundary locks this via a before/after row count with RaisingChatClient."
  - "D-19 materialized: GET /api/chat/history uses Query(default=50, ge=1, le=500). Out-of-bounds values (limit=0, limit=501) return FastAPI's native 422 - no custom handler."
  - "D-20 materialized: chat router is mounted LAST in app.lifespan.lifespan, after SSE + portfolio + watchlist. Verified by awk: exit 0 for (create_chat_router line > create_watchlist_router line)."
  - "Integration-test split: happy/extras/history files use the real app.lifespan.lifespan under LLM_MOCK=true so end-to-end wiring is exercised. ONE file (test_routes_llm_errors.py) uses a bespoke mini-lifespan because injecting a RaisingChatClient requires mount-time substitution - documented inline; the mini-lifespan mirrors real DB/cache/source setup so it is not a test-double of the stack, only of the LLM client."
  - "Plan 03 adds ZERO new dependencies - all required libs (httpx, asgi-lifespan, pytest-asyncio, pydantic v2) were already installed by 01-03 or 05-01."

patterns-established:
  - "Route factory closure signature: create_X_router(db, cache, [source], [client]) -> APIRouter. Chat follows exactly the watchlist signature plus a ChatClient."
  - "Domain-exception -> HTTP envelope mapping: try/except narrow to the specific service exception, raise HTTPException(detail={'error': code_str, 'message': str(exc)}) from exc. 400 for TradeValidationError, 502 for ChatTurnError."
  - "Full-lifespan integration tests for every endpoint + a module-scoped app_with_lifespan fixture. SimulatorDataSource is left running across the module (warmed cache) rather than restarted per test."
  - "Mini-lifespan pattern for mount-time dependency substitution. Limited to one file with an inline docstring explaining why the real lifespan is incompatible with unittest.mock.patch."

requirements-completed:
  - CHAT-01
  - CHAT-05
  - TEST-01

# Metrics
duration: 5min
completed: 2026-04-22
---

# Phase 05 Plan 03: Chat Route Integration Summary

**Factory-closure create_chat_router wiring POST /api/chat and GET /api/chat/history into app.lifespan.lifespan AFTER the watchlist router (D-20), with ChatTurnError -> HTTP 502 mapping and the D-18 user-turn-before-LLM invariant proved at the HTTP boundary.**

## Performance

- **Duration:** ~5 min (3 atomic commits: routes+init, lifespan, tests; no REFACTOR needed)
- **Started:** 2026-04-22T19:44:24Z
- **Completed:** 2026-04-22T19:49:09Z
- **Tasks:** 2 (Task 1 split across routes+init and lifespan commits per plan output staging; Task 2 ships the three integration-test modules)
- **Files modified:** 2 (lifespan + chat __init__ extended)
- **Files created:** 5 (routes.py, 3 integration-test modules, SUMMARY.md)

## Accomplishments

- `POST /api/chat` (CHAT-01) — 200 happy path echoes `ChatResponse` with guaranteed `message`, `trades`, `watchlist_changes` keys; 4 distinct 422 validation boundaries (extras, empty, missing, overlen); 502 envelope on `ChatTurnError` with `{"error":"chat_turn_error","message": str(exc)}` (D-14).
- `GET /api/chat/history` (CHAT-05) — ASC ordering, role interleave (user/assistant/user/assistant), `ChatMessageOut` full-shape invariant, `Query(default=50, ge=1, le=500)` bounds (D-19).
- `create_chat_router(db, cache, source, client)` — factory-closure APIRouter under `prefix="/api/chat"`, zero module-level state, single narrow catch of `service.ChatTurnError` only.
- `backend/app/lifespan.py` — chat client built once via `create_chat_client()` and stored on `app.state.chat_client` (D-06); chat router mounted LAST after watchlist (D-20); D-05 redaction-safe warning replaces the Phase-1 bare `OPENROUTER_API_KEY` warning.
- D-18 user-turn-before-LLM invariant proved at the HTTP boundary: `test_routes_llm_errors.py::TestLLMFailureBoundary` asserts that a 502 response still leaves exactly ONE new `chat_messages` row (the user row) while the assistant row is NOT written.
- Full test suite grew from **283 → 294** (+11 integration tests); `app.chat` coverage **99.17%** (gate 93%); `routes.py` **100%**; `ruff check` clean on all modified files.

## Task Commits

Each task was committed atomically with `--no-verify` (worktree executor):

1. **Task 1a — `create_chat_router` + `__init__` re-export** — `ee150d6` (`feat(05-03): create_chat_router + POST /api/chat + GET /api/chat/history`)
2. **Task 1b — lifespan wiring (D-05, D-06, D-20)** — `ad7f02d` (`feat(05-03): mount chat router in lifespan after watchlist (D-20)`)
3. **Task 2 — integration tests (routes, history, LLM failure)** — `fcb335a` (`test(05-03): integration tests for POST /api/chat + GET /api/chat/history + LLM failure boundary`)

**SUMMARY metadata commit:** pending (next commit after this file).

_No REFACTOR commit required — all three commits green on first run; ruff clean; coverage gate passed without test additions._

## Files Created/Modified

### Created

- `backend/app/chat/routes.py` — Factory-closure `create_chat_router(db, cache, source, client) -> APIRouter`. POST handler wraps `await service.run_turn(...)` with a narrow `except service.ChatTurnError` that translates to `HTTPException(502, detail={"error":"chat_turn_error","message": str(exc)})`. GET handler calls `service.get_history(db, limit=limit)` with `Query(default=50, ge=1, le=500)`. 57 lines, 21 stmts, 100% coverage.
- `backend/tests/chat/test_routes_chat.py` — 6 tests under `TestPostChat`: happy mock + 2-row DB persistence, mock `buy AAPL 1` auto-exec echoes trade result, 4 × 422 validation boundaries (empty, extras, missing, overlen).
- `backend/tests/chat/test_routes_history.py` — 4 tests under `TestGetHistory`: empty case, 2-turn ASC ordering + role interleave + shape invariant, limit=0/501 -> 422, limit=2 tail truncation.
- `backend/tests/chat/test_routes_llm_errors.py` — 1 test under `TestLLMFailureBoundary`: 502 envelope on RaisingChatClient(RuntimeError), exactly one new user row after the failed POST (D-18). Mini-lifespan with inline rationale docstring.

### Modified

- `backend/app/chat/__init__.py` — Added `from .routes import create_chat_router` import and `"create_chat_router"` entry in `__all__` (alphabetical, between `create_chat_client` and `get_history`).
- `backend/app/lifespan.py` — Added `from .chat import create_chat_client, create_chat_router` to import block. Replaced the bare `OPENROUTER_API_KEY` warning with the D-05 gated variant (fires only when `LLM_MOCK != "true" AND` key is empty/missing; message never includes key value). Added three lines after the watchlist router mount: `chat_client = create_chat_client()`, `app.state.chat_client = chat_client`, `app.include_router(create_chat_router(conn, cache, source, chat_client))` with a `# D-20` comment.

## Decisions Made

- **D-14 envelope key:** The PLAN.md specified `"error":"chat_turn_error"` (matches the `ChatTurnError` class name). Plan 02's SUMMARY mentioned a placeholder `"llm_unavailable"` string in one spot; this plan authoritatively locks the key as `"chat_turn_error"` and the test, route, and verification greps all use that value.
- **No custom 422 handler:** Pydantic v2 validation failures (extras, empty, missing, overlen) fall through to FastAPI's native 422. This keeps the route body minimal and avoids duplicating FastAPI's own envelope.
- **Mini-lifespan isolated to one file:** The full-lifespan integration-test topology (real `app.lifespan.lifespan` under `LLM_MOCK=true`) exercises end-to-end wiring in `test_routes_chat.py` + `test_routes_history.py`. The single bespoke mini-lifespan in `test_routes_llm_errors.py` is the minimum diff necessary to substitute `RaisingChatClient` at mount time — `unittest.mock.patch("app.chat.client.create_chat_client", ...)` does NOT intercept the lifespan because `app.lifespan` rebinds the name at import time. Documented inline.

## Deviations from Plan

None - plan executed exactly as written. All grep acceptance criteria pass on first run; no auto-fix rules were triggered.

## Threats Mitigated

All nine STRIDE threats from `<threat_model>` have an explicit proof in the suite or in a greppable code invariant:

- **T-05-03-01 (Spoofing, accepted):** Documented as single-user invariant; no user_id on HTTP surface — `! grep -nE "user_id" backend/app/chat/routes.py` holds.
- **T-05-03-02 (Tampering on message body):** `ChatRequest` `extra="forbid"` + `min_length=1`, `max_length=8192`. `test_routes_chat.py::test_extra_key_returns_422`, `::test_empty_message_returns_422`, `::test_missing_message_returns_422`, `::test_message_over_limit_returns_422`.
- **T-05-03-03 (Tampering on pagination):** `Query(default=50, ge=1, le=500)`. `test_routes_history.py::test_limit_bounds_rejected` for limit=0 and limit=501.
- **T-05-03-04 (Repudiation):** D-18 invariant at HTTP boundary — `test_routes_llm_errors.py::test_chat_turn_error_maps_to_502_with_error_envelope` asserts exactly one new user row on a failing POST.
- **T-05-03-05 (Info disclosure — API key):** D-05 warning is a fixed string; `! grep -nE '%s.*OPENROUTER_API_KEY' backend/app/lifespan.py` holds. `ChatTurnError`'s `str(exc)` comes from LiteLLM/OpenRouter and does not contain the key.
- **T-05-03-06 (DoS — large body):** `max_length=8192` caps input at 8 KB.
- **T-05-03-07 (DoS — large history query):** `limit <= 500` at the Query level; the two-level subquery in `get_history` does the slicing in SQL.
- **T-05-03-08 (Privilege — user_id leak):** routes.py has zero `user_id` references (greppable).
- **T-05-03-09 (Privilege — chat-initiated trades):** `_run_one_trade` in Plan 02's service.py goes through `portfolio.service.execute_trade` — same validation path as manual trades. No weakening in Plan 03.

## Issues Encountered

None. The plan text was precise enough that the three commits each went green on first run.

Minor friction:
- Python 3.14 DeprecationWarning on `asyncio.DefaultEventLoopPolicy` emits 270 warnings across the full suite. Pre-existing (from tests/conftest.py); not caused by this plan.

## User Setup Required

None - no external service configuration required. `LLM_MOCK=true` is set in the integration-test harness so no real `OPENROUTER_API_KEY` is needed to run the suite. Live mode (`LLM_MOCK` unset) will require `OPENROUTER_API_KEY` in `.env`; the D-05 startup warning surfaces the missing-key condition.

## Next Phase Readiness

**Phase 05 (chat integration) is feature-complete at the backend.** The wave-3 executor closes out:

1. `POST /api/chat` + `GET /api/chat/history` are mounted, validated, and covered end-to-end.
2. `app.chat.create_chat_router` is importable from the package root.
3. `app.lifespan.lifespan` wires the chat subsystem LAST (D-20) and stores the chat client on `app.state.chat_client` (D-06).
4. D-05 redaction + the D-14/D-18 error-boundary contract are both greppable invariants and test-locked.

**Ready for next phase (frontend or app-shell polish):**
- Frontend can consume `POST /api/chat` and render trade/watchlist action confirmations inline per PLAN.md §9.
- `GET /api/chat/history` is paginated-safe for transcript reload (default limit=50, max 500).
- No blockers; all contracts stable.

## Open Questions / Followups

None of the following block the next wave, but they are worth flagging for the retrospective:

- **Rate limiting:** `POST /api/chat` has no per-IP/per-minute cap. Out of scope for a single-user localhost demo; worth adding in a future auth/multi-user phase.
- **Server-side streaming:** Deliberately omitted (PLAN.md §9). If Cerebras latency ever regresses, SSE streaming of assistant tokens would be a follow-up.
- **Chat message retention:** No TTL/archive policy. The `chat_messages` table grows unbounded; acceptable for a local demo but a cleanup job would be sensible in a multi-user future.

## Commands for Smoke

```bash
cd backend && uv run --extra dev pytest tests/chat -v
cd backend && uv run --extra dev pytest -v
cd backend && uv run --extra dev pytest --cov=app.chat --cov-fail-under=93
cd backend && uv run --extra dev ruff check app/chat tests/chat app/lifespan.py
```

All four commands exit 0.

## Self-Check: PASSED

Verifying all claims before returning:

1. **Created files exist on disk:**
   - `backend/app/chat/routes.py` — FOUND
   - `backend/tests/chat/test_routes_chat.py` — FOUND
   - `backend/tests/chat/test_routes_history.py` — FOUND
   - `backend/tests/chat/test_routes_llm_errors.py` — FOUND
   - `.planning/phases/05-ai-chat-integration/05-03-SUMMARY.md` — (this file)

2. **Modified files contain expected changes:**
   - `backend/app/chat/__init__.py` — exports `create_chat_router` in `__all__` (alphabetical between `create_chat_client` and `get_history`)
   - `backend/app/lifespan.py` — imports `create_chat_client, create_chat_router`; D-05 warning rewritten; chat wiring mounted after watchlist with `# D-20` comment

3. **Commits exist in worktree branch:**
   - `ee150d6` (routes.py + __init__.py) — FOUND
   - `ad7f02d` (lifespan.py) — FOUND
   - `fcb335a` (integration tests) — FOUND

4. **All grep acceptance criteria pass** (verified inline during execution).

5. **Full suite:** 294 passed, 0 failed (283 prior + 11 new).

6. **Coverage:** `app.chat` 99.17% (gate 93%); `routes.py` 100%.

7. **Lint:** `ruff check app/chat tests/chat app/lifespan.py` clean.

---
*Phase: 05-ai-chat-integration*
*Completed: 2026-04-22*
