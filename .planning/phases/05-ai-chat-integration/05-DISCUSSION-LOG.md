# Phase 5: AI Chat Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or
> execution agents. Decisions are captured in `05-CONTEXT.md` — this log
> preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 05-ai-chat-integration
**Areas discussed:** Auto-exec contract, Response payload shape,
Mock-mode design, Chat history + prompt window

---

## Auto-exec contract

### Q1: Execution order between `watchlist_changes[]` and `trades[]`

| Option | Description | Selected |
|--------|-------------|----------|
| Watchlist first, then trades | Lets "add PYPL + buy PYPL 10" work in a single chat turn; execute_trade raises UnknownTicker otherwise | ✓ |
| Trades first, then watchlist | Simpler, worse UX — combo turns break until the LLM is trained for two-step | |
| In document order (mixed list) | Gives LLM control; requires schema change from two arrays to one | |

**User's choice:** Watchlist first, then trades (Recommended).
**Notes:** Captured as D-09. Preserves the agentic-AI "wow moment" PROJECT.md calls out as non-negotiable.

### Q2: Partial-failure policy (trade #3 of 4 fails)

| Option | Description | Selected |
|--------|-------------|----------|
| Continue, record per-action status | PLAN.md §9 explicit: failures reflected back, not swallowed | ✓ |
| Fail-fast, stop on first error | Loses downstream work; still leaves earlier commits in place | |
| All-or-none atomic | Cleanest semantically; breaks Phase 3 execute_trade's internal commit pattern | |

**User's choice:** Continue, record per-action status (Recommended).
**Notes:** Captured as D-10. No rollback machinery; service layer unchanged.

### Q3: Cold-cache on same-turn "add + buy"

| Option | Description | Selected |
|--------|-------------|----------|
| Record as failed with price_unavailable | Honest; LLM retries next turn; no timing hacks | ✓ |
| Wait/retry up to N ms | Better UX but adds latency + async timing + retry loop | |
| Eagerly seed the cache on add | Works for SimulatorDataSource only (asymmetric with Massive) | |

**User's choice:** Record as failed with `price_unavailable` (Recommended).
**Notes:** Captured as D-11 + D-12. Maps to the existing Phase 3 `PriceUnavailable` error code.

### Q4: Where does the auto-exec loop live?

| Option | Description | Selected |
|--------|-------------|----------|
| Chat service as async `run_turn` | Thin route, testable service, parity with Phase 3/4 pure-function services | ✓ |
| Route handler orchestrates | Tight coupling, breaks precedent | |
| Dedicated `app/chat/executor.py` | Isolation; probably overkill single-user | |

**User's choice:** Chat service as async function (Recommended).
**Notes:** Captured as D-02. `run_turn(conn, cache, source, client, user_message)` is the one entry point; per-action DB mutations remain sync.

---

## Response payload shape

### B1: Response shape from `POST /api/chat`

| Option | Description | Selected |
|--------|-------------|----------|
| Pass-through + per-action status | Enriched trades/watchlist_changes with status, fills, errors | ✓ |
| Raw LLM output only | Minimal; frontend must re-query to know what happened | |
| Flat `actions[]` with discriminator | Requires schema change; not the PLAN.md shape | |

**User's choice:** Pass-through + per-action status (Recommended).
**Notes:** Captured as D-07. Phase 8 chat UI renders inline green/red chips without a second request.

### B2: What goes in `chat_messages.actions` JSON column

| Option | Description | Selected |
|--------|-------------|----------|
| Enriched per-action result | Same shape as the response; history replay sees fills and failure codes | ✓ |
| Raw LLM structured output | Lighter storage; loses execution outcomes | |

**User's choice:** Enriched per-action result (Recommended).
**Notes:** Captured as D-08. User rows keep `actions = NULL`.

---

## Mock-mode design

### C1: `LLM_MOCK=true` behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Keyword-scripted | Parses buy/sell/add/remove so E2E actually executes actions | ✓ |
| Static canned | Always empty actions; E2E can't test AI trade execution | |
| JSON fixture file | Extensible but adds config surface not needed for v1 | |

**User's choice:** Keyword-scripted (Recommended).
**Notes:** Captured as D-06. Regex patterns documented; unknown input returns empty actions with "mock response" message.

### C2: Where does `LLM_MOCK` branching live?

| Option | Description | Selected |
|--------|-------------|----------|
| ChatClient Protocol + two impls, factory at lifespan | Mirrors `create_market_data_source`; single env read per process | ✓ |
| Inline `if env: mock else: live` in run_turn | Mixes concerns; harder to swap in tests | |

**User's choice:** ChatClient Protocol + factory (Recommended).
**Notes:** Captured as D-03, D-05. `create_chat_client()` in `app/chat/client.py`.

---

## Chat history + prompt window

### D1: `GET /api/chat/history` in Phase 5?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — Phase 5 owns the endpoint | Phase 8 frontend needs it on page reload | ✓ |
| No — defer to Phase 8 | Frontend would reconstruct history from session-local state only | |

**User's choice:** Yes (Recommended).
**Notes:** Captured as D-19. `limit` query param with most-recent-N tail ordered ASC for display.

### D2: Conversation history window in the LLM prompt

| Option | Description | Selected |
|--------|-------------|----------|
| Last 20 messages | Simple, bounded, no token accounting | ✓ |
| Token-budget trimmed | Accurate but needs token counter + complicates mock mode | |
| All history | Unbounded growth → eventual context blowup | |

**User's choice:** Last 20 messages (Recommended).
**Notes:** Captured as D-17. `CHAT_HISTORY_WINDOW = 20` module constant in `prompts.py`.

### D3: Portfolio context format in the prompt

| Option | Description | Selected |
|--------|-------------|----------|
| JSON blob | Token-efficient, matches structured-output ethos | ✓ |
| Markdown table | Readable, heavier | |
| Prose | Least efficient | |

**User's choice:** JSON blob (Recommended).
**Notes:** Captured as D-16. `build_portfolio_context(conn, cache)` reuses `portfolio.service.get_portfolio` + `watchlist.service.get_watchlist`.

---

## Claude's Discretion

Planner picks the conventional answer without re-asking. See
`05-CONTEXT.md` **Claude's Discretion** subsection under
`<decisions>` for the full list: exact system-prompt wording, mock
regex phrasing, Pydantic model file location, test-fixture pattern,
router prefix/tags, `asyncio.to_thread` vs. native async LiteLLM,
`Field` bounds on `quantity`, and per-step log levels.

## Deferred Ideas

- Token-budget history compaction / summarization (part of CHAT-07 v2).
- Clear-history / delete-history endpoints.
- Bulk trade-rollback on partial failure.
- Retry-with-backoff on LLM transient errors.
- Retry-after-watchlist-add to warm the cache for a follow-up trade.
- Per-turn cost / latency telemetry.
- Request-level concurrency control on `/api/chat`.
- Dedicated chat-session / thread boundary (v2 multi-thread UI).
- Structured-output schema versioning.
