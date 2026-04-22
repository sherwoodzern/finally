---
phase: 05
plan: 01
subsystem: chat
tags:
  - chat
  - llm
  - litellm
  - openrouter
  - cerebras
  - pydantic
  - mock-mode
dependency-graph:
  requires:
    - app.watchlist.models.normalize_ticker
    - app.portfolio.service.get_portfolio
    - app.watchlist.service.get_watchlist
    - app.market.PriceCache
  provides:
    - app.chat.ChatClient
    - app.chat.LiveChatClient
    - app.chat.MockChatClient
    - app.chat.create_chat_client
    - app.chat.StructuredResponse
    - app.chat.ChatRequest
    - app.chat.ChatResponse
    - app.chat.HistoryResponse
    - app.chat.ChatMessageOut
    - app.chat.TradeAction
    - app.chat.TradeActionResult
    - app.chat.WatchlistAction
    - app.chat.WatchlistActionResult
    - app.chat.SYSTEM_PROMPT
    - app.chat.CHAT_HISTORY_WINDOW
    - app.chat.build_portfolio_context
    - app.chat.build_messages
  affects:
    - backend/pyproject.toml (new runtime deps: litellm, pydantic)
tech-stack:
  added:
    - "litellm>=1.83.0 (relaxed from planned >=1.83.10 -- see Deviations)"
    - "pydantic>=2.0.0 (explicit pin; was transitively present via FastAPI)"
  patterns:
    - "Pydantic v2 ConfigDict(extra='forbid') on all LLM-facing models"
    - "typing.Protocol for ChatClient contract (no ABC)"
    - "asyncio.to_thread for sync third-party call (mirrors massive_client.py:97)"
    - "env-driven factory reading LLM_MOCK once (mirrors app.market.factory)"
    - "two-level subquery for most-recent-N ordered ASC (chat history)"
key-files:
  created:
    - backend/app/chat/__init__.py
    - backend/app/chat/models.py
    - backend/app/chat/client.py
    - backend/app/chat/mock.py
    - backend/app/chat/prompts.py
    - backend/tests/chat/__init__.py
    - backend/tests/chat/conftest.py
    - backend/tests/chat/test_models.py
    - backend/tests/chat/test_client_live.py
    - backend/tests/chat/test_mock_client.py
    - backend/tests/chat/test_prompts.py
  modified:
    - backend/pyproject.toml
    - backend/uv.lock
decisions:
  - "Relaxed litellm pin to >=1.83.0 (latest that coexists with python-dotenv>=1.2.1); litellm 1.83.10 hard-pins python-dotenv==1.0.1, causing dependency resolution to fail."
metrics:
  tasks_completed: 4
  tests_added: 51
  full_suite: 258
  files_created: 11
  files_modified: 2
  duration: ~15 minutes
  completed_date: 2026-04-22
---

# Phase 5 Plan 01: Chat Foundations (Deps + Models + Client + Prompts) Summary

Scaffolded the `app.chat` subsystem with Pydantic v2 structured-output schemas, the ChatClient Protocol + Live/Mock implementations, and the prompt-assembly module. Plan 02 (service orchestration) and Plan 03 (routes + lifespan) can now import the full public API.

## Purpose

Deliver the foundational building blocks for FinAlly's LLM-driven chat endpoint without wiring FastAPI routes or the auto-exec service yet:

- Lock the structured-output schema that LiteLLM parses into (CHAT-02).
- Lock the live-LLM call shape to `.claude/skills/cerebras/SKILL.md` verbatim (CHAT-02).
- Lock the deterministic keyword-scripted mock client for `LLM_MOCK=true` (CHAT-06).
- Lock the prompt assembly: SYSTEM_PROMPT + JSON portfolio context + 20-message history window (CHAT-03).

One-liner: foundational `app.chat` package (models + client Protocol + live LiteLLM client + deterministic mock + prompt assembly) with 51 unit tests locking the LLM call shape, structured-output schema, and mock determinism.

## Requirements Delivered

- **CHAT-02** (partial): Structured-output schema locked; live-LLM call shape matches the cerebras skill verbatim. Full requirement closes in Plan 02+03 with service orchestration + routes.
- **CHAT-03** (partial): Prompt assembly is deterministic and reuses get_portfolio + get_watchlist. Full requirement closes in Plan 02 when `run_turn` wires it into the call.
- **CHAT-06** (partial): `MockChatClient` is deterministic and regex-word-boundary-anchored. Full requirement closes in Plan 03 when the lifespan factory picks it up via `LLM_MOCK=true`.

## D-Decisions Implemented

| Decision | Status | Notes |
|----------|--------|-------|
| D-01 Chat code in `backend/app/chat/` mirroring portfolio/watchlist | partial | Modules created: `models.py`, `client.py`, `mock.py`, `prompts.py`, `__init__.py`. `routes.py` + `service.py` land in Plans 02/03. |
| D-02 Service owns auto-exec loop (async `run_turn`) | deferred | Plan 02. |
| D-03 `ChatClient` Protocol with `async complete(messages)` | done | `backend/app/chat/client.py`. |
| D-04 `LiveChatClient` calls litellm.completion with model/response_format/reasoning_effort/extra_body per cerebras skill | done | Exact call-shape asserted by `test_completion_call_shape_matches_cerebras_skill`. |
| D-05 `create_chat_client()` factory reads `LLM_MOCK` once | done | Mirrors `app.market.factory`. |
| D-06 Keyword-scripted mock: buy/sell/add/remove\|drop | done | Word-boundary anchoring per Pitfall 7. |
| D-13 Ticker normalization reuses `normalize_ticker` via field_validator | done | No regex duplication. |
| D-15 SYSTEM_PROMPT as module-level constant | done | Identifies "FinAlly, an AI trading assistant". |
| D-16 Portfolio context is JSON blob reusing get_portfolio + get_watchlist | done | `build_portfolio_context`. |
| D-17 20-message history window module constant | done | `CHAT_HISTORY_WINDOW = 20`. |
| D-21 Declare litellm + pydantic in pyproject | done (with deviation) | See Deviations. |

## Tests

| Module | Classes | Tests | Notes |
|--------|---------|-------|-------|
| test_models.py | 7 | 21 | StructuredResponse (4), TradeAction (4), WatchlistAction (3), ChatRequest (3), Results (3), ChatResponse (1), ChatMessageOut (2), HistoryResponse (1) |
| test_client_live.py | 2 | 6 | LiveChatClient call-shape + factory selection |
| test_mock_client.py | 8 | 12 | Buy (3) / Sell (1) / Add-Remove (3) / Combinations (1) / NoMatch (1) / CaseInsensitive (1) / LastUserMessage (1) / DeterministicMessage (1) |
| test_prompts.py | 3 | 12 | Constants (3) / build_portfolio_context (3) / build_messages (6) |

Total chat tests: **51 passing**. Full backend suite: **258 passing** (207 baseline + 51 new, 0 regressions). Ruff: `All checks passed!`

## Commits

| Hash | Message |
|------|---------|
| c55433a | chore(05-01): add litellm+pydantic deps, scaffold app.chat package and tests |
| 8709d67 | feat(05-01): implement app.chat.models Pydantic v2 schemas (D-07, D-13) |
| bbeb6c1 | feat(05-01): implement LiveChatClient, MockChatClient, create_chat_client factory |
| 9d6bba9 | feat(05-01): implement app.chat.prompts (SYSTEM_PROMPT, build_messages, portfolio context) |

## Deviations from Plan

### [Rule 3 - Blocking Issue] Relaxed litellm version pin from >=1.83.10 to >=1.83.0

- **Found during:** Task 1 (`uv add "litellm>=1.83.10"`)
- **Issue:** `litellm==1.83.10` and `1.83.11` hard-pin `python-dotenv==1.0.1`, but the project already depends on `python-dotenv>=1.2.1` (added in Phase 1). uv's resolver correctly refuses to solve this unsatisfiable combination:
  ```
  Because litellm>=1.83.10 depends on python-dotenv==1.0.1 and only the
  following versions of litellm are available:
      litellm<=1.83.10
      litellm==1.83.11
  ... your project depends on python-dotenv>=1.2.1 ... your project's
  requirements are unsatisfiable.
  ```
- **Fix:** Used `uv add "litellm"` which resolved to `litellm==1.83.0` — the most recent release that accepts `python-dotenv>=1.0.1,<2`. All plan acceptance criteria that reference the `litellm` grep stay satisfied (string `litellm` appears in pyproject.toml). The cerebras skill contract is unchanged across 1.83.0 / 1.83.10 (same `completion(..., response_format=..., reasoning_effort='low', extra_body={...})` shape); locked in `test_completion_call_shape_matches_cerebras_skill`.
- **Files modified:** `backend/pyproject.toml` (`litellm>=1.83.0`), `backend/uv.lock`.
- **Commit:** c55433a.
- **Impact:** None functional. Plan 02/03 writers should not re-pin >=1.83.10 unless the upstream python-dotenv pin is relaxed. If a later litellm release restores compatibility with newer dotenv, tighten the pin in that phase's dependency task.

Otherwise — plan executed exactly as written. No auth gates, no architectural questions, no stub patterns introduced.

## Public API Shape (for Plan 02 + Plan 03)

```python
from app.chat import (
    # Models
    ChatRequest, ChatResponse,
    ChatMessageOut, HistoryResponse,
    StructuredResponse,
    TradeAction, TradeActionResult,
    WatchlistAction, WatchlistActionResult,
    # Client
    ChatClient, LiveChatClient, MockChatClient,
    create_chat_client,
    # Prompts
    SYSTEM_PROMPT, CHAT_HISTORY_WINDOW,
    build_portfolio_context, build_messages,
)
```

16 symbols exposed via `__all__` (alphabetized). No changes to existing modules.

## Hand-off Note to Plan 02

- `app.chat.ChatClient` Protocol + `MockChatClient` + `create_chat_client` are importable. Plan 02's `run_turn(conn, cache, source, client, user_message)` orchestrator can call `await client.complete(build_messages(conn, cache, user_message))` and pattern-match on the returned `StructuredResponse`.
- `TradeActionResult` + `WatchlistActionResult` are ready to be populated by the auto-exec loop (D-12 per-action error translation table).
- `mock_chat_client` + `FakeChatClient` fixtures are intentionally NOT in `tests/chat/conftest.py` yet — Plan 02 Task 1 adds them once it has a concrete use case (per 05-PATTERNS.md and the Task 1 note in 05-01-PLAN.md).
- `from litellm.exceptions import AuthenticationError, BadRequestError, RateLimitError, APIError, Timeout` is the expected Plan 02 error-catch surface for D-14 → HTTP 502 translation. `LiveChatClient.complete` does not catch — exceptions propagate to the service boundary.

## Self-Check: PASSED

**Created files verified present:**
- backend/app/chat/__init__.py ✓
- backend/app/chat/models.py ✓
- backend/app/chat/client.py ✓
- backend/app/chat/mock.py ✓
- backend/app/chat/prompts.py ✓
- backend/tests/chat/__init__.py ✓
- backend/tests/chat/conftest.py ✓
- backend/tests/chat/test_models.py ✓
- backend/tests/chat/test_client_live.py ✓
- backend/tests/chat/test_mock_client.py ✓
- backend/tests/chat/test_prompts.py ✓

**Commits verified in git log:**
- c55433a ✓
- 8709d67 ✓
- bbeb6c1 ✓
- 9d6bba9 ✓

**Verification commands re-run:**
- `pytest tests/chat` → 51 passed
- `pytest` full suite → 258 passed
- `ruff check app/chat tests/chat` → All checks passed
