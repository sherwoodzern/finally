# Phase 5: AI Chat Integration - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up `POST /api/chat` that takes a user message, calls LiteLLM →
OpenRouter → `openrouter/openai/gpt-oss-120b` with Cerebras as the inference
provider using structured outputs, then auto-executes any proposed
`watchlist_changes[]` and `trades[]` through the same service-layer
validation path used by manual HTTP trades and watchlist mutations.
Persist both turns (user + assistant) in `chat_messages`, surface every
action's execution result back to the caller in one synchronous JSON
payload, and gate the live LLM call behind `LLM_MOCK=true` so the Phase 10
E2E pack can exercise the whole chat/auto-exec path without an API key.

**In scope:**
- `app/chat/` sub-package mirroring `app/portfolio/` (Phase 3 D-01) and
  `app/watchlist/` (Phase 4 D-01): `routes.py`, `service.py`, `models.py`,
  `client.py`, `mock.py`, `prompts.py`, `__init__.py` (explicit `__all__`).
- Pydantic v2 request/response + structured-output models with
  `extra="forbid"` on the request body.
- Pure-function service orchestration: `async run_turn(conn, cache, source,
  user_message) -> ChatResponse` that builds the prompt, invokes the
  `ChatClient` protocol, runs the auto-exec loop, persists both turns in
  `chat_messages`, and returns the enriched response.
- `ChatClient` protocol with two implementations (`LiveChatClient` via the
  `cerebras` skill, `MockChatClient` keyword-scripted) selected by a
  `create_chat_client()` factory at lifespan time.
- `GET /api/chat/history?limit=N` returning the last N `chat_messages`
  rows ordered `created_at ASC` (needed by Phase 8 frontend on reload).
- Lifespan wiring: `app.state.chat_client = create_chat_client()` and
  `app.include_router(create_chat_router(conn, cache, source,
  chat_client))` after the watchlist router.
- Backend test suite extension (TEST-01): chat service unit tests, mock
  client tests, auto-exec failure-path tests, route integration tests.
- Dependency additions: `litellm` (runtime), `pydantic` already present via
  FastAPI transitive dep — verify and pin explicitly.

**Out of scope (belongs to later phases):**
- Frontend chat panel UI, inline trade-confirmation chips, loading
  indicator → Phase 8 (FE-09, FE-11).
- Token-by-token streaming → v2 (CHAT-07, PROJECT.md Out of Scope).
- Playwright E2E for chat → Phase 10 (TEST-04).
- Dockerfile / `.env.example` changes → Phase 9.
- History pagination beyond a `limit` query parameter.
- Clear-history / delete-history endpoints.
- Multi-user / `user_id != "default"` — schema supports it, UI/auth does
  not (AUTH-01 is v2).
- Retrying failed trades after a watchlist add (cold-cache cases return
  `price_unavailable` and let the LLM retry on the next turn).

</domain>

<decisions>
## Implementation Decisions

### Module & Service Layout

- **D-01:** Chat code lives in `backend/app/chat/` mirroring
  `app/portfolio/` and `app/watchlist/`:
  - `routes.py` — FastAPI router factory
    `create_chat_router(db, cache, source, client)` with `POST /api/chat`
    and `GET /api/chat/history`.
  - `service.py` — orchestration: `async run_turn(conn, cache, source,
    client, user_message) -> ChatResponse`, plus
    `get_history(conn, limit) -> HistoryResponse`. No FastAPI imports.
  - `client.py` — `ChatClient` Protocol + `LiveChatClient` (LiteLLM
    wrapper per the `cerebras` skill) + `create_chat_client()` factory
    reading `LLM_MOCK`.
  - `mock.py` — `MockChatClient` (keyword-scripted).
  - `prompts.py` — system prompt constant + `build_portfolio_context(
    conn, cache) -> dict` returning the JSON-blob dict embedded in the
    user message.
  - `models.py` — Pydantic v2 request/response + structured-output models.
  - `__init__.py` — explicit `__all__` re-exporting
    `create_chat_router`, `create_chat_client`, `ChatClient`,
    `run_turn`, `MockChatClient`.

- **D-02:** The auto-exec loop lives in the chat service, not in the
  route, and not in a separate `executor.py`. The service is the single
  place that knows the action-execution contract. `run_turn` is `async`
  because it awaits `source.add_ticker` / `source.remove_ticker`; the
  per-action database mutations remain synchronous
  (`watchlist.service.add_ticker`, `watchlist.service.remove_ticker`,
  `portfolio.service.execute_trade` are all sync pure functions with
  internal `conn.commit()`). No new async DB wrapper.

### LLM Client & Mock Mode

- **D-03:** `ChatClient` is a `typing.Protocol` with a single method:
  `async def complete(self, messages: list[dict]) -> StructuredResponse`
  where `StructuredResponse` is the Pydantic v2 model matching
  PLAN.md §9 (`message`, `trades`, `watchlist_changes`). Protocol, not
  ABC, so the mock implementation is a plain class.

- **D-04:** `LiveChatClient` wraps the `cerebras` skill exactly:
  ```python
  from litellm import completion
  MODEL = "openrouter/openai/gpt-oss-120b"
  EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
  response = completion(
      model=MODEL,
      messages=messages,
      response_format=StructuredResponse,
      reasoning_effort="low",
      extra_body=EXTRA_BODY,
  )
  return StructuredResponse.model_validate_json(
      response.choices[0].message.content
  )
  ```
  The synchronous `litellm.completion` call is wrapped in
  `asyncio.to_thread` to keep the event loop responsive, matching the
  pattern `MassiveDataSource` already uses for the sync Polygon SDK
  (`massive_client.py:97`).

- **D-05:** `create_chat_client()` factory reads `LLM_MOCK` from
  `os.environ` once at lifespan entry, mirroring `factory.py`'s
  `MASSIVE_API_KEY` check (Phase 1). Returns `MockChatClient()` when
  `LLM_MOCK == "true"`, else `LiveChatClient()`. Client is attached to
  `app.state.chat_client` and injected into the router factory.
  Rationale: picked once per process; tests override via lifespan env.
  Rejected: inline `if env: mock else live` inside `run_turn` (mixes
  concerns, harder to unit-test the live path in isolation).

- **D-06:** `MockChatClient.complete` is **keyword-scripted** so the
  Phase 10 E2E pack can exercise real auto-exec:
  - `buy <TICKER> <QTY>` → `trades=[{ticker, side:"buy", quantity}]`
  - `sell <TICKER> <QTY>` → `trades=[{ticker, side:"sell", quantity}]`
  - `add <TICKER>` → `watchlist_changes=[{ticker, action:"add"}]`
  - `remove <TICKER>` / `drop <TICKER>` →
    `watchlist_changes=[{ticker, action:"remove"}]`
  - Multiple patterns in one message combine into one structured
    response (all matches wired into the respective arrays).
  - Unknown / no match → `StructuredResponse(message="mock response",
    trades=[], watchlist_changes=[])`.
  Regexes are case-insensitive, ticker matches `[A-Z][A-Z0-9.]{0,9}`
  (same shape as Phase 4 D-04 `normalize_ticker`), quantity matches
  `\d+(?:\.\d+)?`. The `message` field for matched patterns is a short
  deterministic string like `"Mock: executing buy AAPL 10"` so E2E
  snapshots stay stable.

### Response Payload & Persistence

- **D-07:** `POST /api/chat` returns a **pass-through + per-action
  status** shape (never the raw LLM output alone):
  ```json
  {
    "message": "<assistant conversational text>",
    "trades": [
      {"ticker": "AAPL", "side": "buy", "quantity": 10,
       "status": "executed", "price": 191.23, "cash_balance": 8087.7,
       "executed_at": "2026-..."}
      /* or */
      {"ticker": "XYZ", "side": "buy", "quantity": 1000,
       "status": "failed", "error": "insufficient_cash",
       "message": "Need $120000.00, have $10000.00"}
    ],
    "watchlist_changes": [
      {"ticker": "PYPL", "action": "add", "status": "added"}
      /* or */
      {"ticker": "PYPL", "action": "add", "status": "exists"}
      /* or */
      {"ticker": "PYPL", "action": "remove", "status": "not_present"}
      /* or */
      {"ticker": "BAD!", "action": "add", "status": "failed",
       "error": "invalid_ticker", "message": "..."}
    ]
  }
  ```
  - `trades[].status`: `"executed" | "failed"`.
  - `watchlist_changes[].status`: the Phase 4 service discriminator
    `"added" | "exists" | "removed" | "not_present"`, plus `"failed"`
    for edge cases (bad ticker shape that Pydantic validation caught).
  - `executed` trades inline the `TradeResponse` fields
    (price, cash_balance, executed_at). No need for the frontend to
    re-query `/api/portfolio`.
  - `failed` actions carry an `error` code and a human `message`
    mirroring the Phase 3 trade-validation contract
    (`insufficient_cash`, `insufficient_shares`, `unknown_ticker`,
    `price_unavailable`).

- **D-08:** `chat_messages.actions` JSON column stores the **enriched
  per-action result from D-07** on the assistant turn, not the raw LLM
  output. Shape: `{"trades": [...], "watchlist_changes": [...]}` (drops
  the conversational `message` since that lives in `content`). Rationale:
  history replay by Phase 8 shows exactly what ran, with fills and
  failure reasons intact, without re-running actions. User turns always
  have `actions = NULL` (PLAN.md §7).

### Auto-Exec Contract

- **D-09:** **Execution order is watchlist first, then trades** (no
  mixed ordering, no document-order). Rationale:
  `portfolio.service.execute_trade` raises `UnknownTicker` if the ticker
  is not in `watchlist` (Phase 3 D-14,
  `backend/app/portfolio/service.py:99-104`). Running watchlist mutations
  first lets one chat turn say "add PYPL and buy PYPL 10" and actually
  work. This is the agentic-AI "wow" moment PROJECT.md calls out as
  non-negotiable.

- **D-10:** **Continue-on-failure per-action** semantics (never
  fail-fast, never all-or-none atomic). Every action runs; failures are
  captured in the response as `status="failed"` with an error code, and
  downstream actions still execute. Rationale: matches PLAN.md §9
  ("If a trade fails validation, the error is included in the chat
  response so the LLM can inform the user"); preserves the Phase 3
  `execute_trade` contract (per-trade commit, service-owned
  transaction). No new transactional savepoint machinery.

- **D-11:** **Cold-cache trades surface `price_unavailable`, no retry
  loop**. If the LLM adds a previously-unknown ticker and immediately
  tries to buy it in the same turn, `execute_trade` raises
  `PriceUnavailable` because the market source hasn't ticked yet. The
  auto-exec path records this as a failed action with
  `error="price_unavailable"` and continues. The LLM sees the failure
  on its next turn and can retry. Rejected: sleep-and-retry loops (add
  latency, ad-hoc timing), eagerly priming the cache on add
  (works for Simulator via `simulator.py:244-257` seed, doesn't work
  for MassiveDataSource — asymmetric).

- **D-12:** **Per-action error translation**. The auto-exec loop catches
  and translates to the response-shape `{status:"failed", error, message}`:
  | Exception                                | Code              | Source             |
  |------------------------------------------|-------------------|--------------------|
  | `portfolio.service.InsufficientCash`     | `insufficient_cash`   | Phase 3 D-09 |
  | `portfolio.service.InsufficientShares`   | `insufficient_shares` | Phase 3 D-09 |
  | `portfolio.service.UnknownTicker`        | `unknown_ticker`      | Phase 3 D-14 |
  | `portfolio.service.PriceUnavailable`     | `price_unavailable`   | Phase 3 D-13 |
  | `ValueError` from ticker normalization   | `invalid_ticker`      | Phase 4 D-04 |
  | Any other `Exception` during auto-exec   | `internal_error`      | fallback     |
  The fallback catch wraps only the auto-exec loop body (narrow, at the
  boundary — CONVENTIONS.md) and logs `logger.exception`. The LLM call
  itself is NOT inside this try (D-14 covers LLM errors separately).

- **D-13:** **Ticker normalization inside auto-exec** reuses
  `watchlist.service`'s normalization exactly by going through the
  Pydantic `StructuredResponse` model (structured outputs already
  enforce `side ∈ {buy, sell}` and `action ∈ {add, remove}`; a
  `field_validator` on `ticker` fields applies the same strip+upper+
  regex transform as Phase 4 D-04). No duplicated regex. If the LLM
  emits a malformed ticker (unlikely with structured outputs), the
  entire response fails parse at the client boundary and the whole
  turn surfaces as a chat failure (D-14).

### LLM Call Error Handling

- **D-14:** Errors from the LLM call path (network, auth, rate limit,
  malformed JSON the structured-output validator rejects) map to
  `HTTPException(502, detail={"error": "llm_unavailable", "message":
  str(exc)})`. The user turn is still persisted in `chat_messages`
  before the LLM call so chat history stays consistent; no assistant
  turn is persisted on failure. Missing `OPENROUTER_API_KEY` surfaces
  here at call time (Phase 1 D-01 log at startup was a warning, not a
  hard fail — deliberate, Phase 1 decision).

### Prompt Construction

- **D-15:** **System prompt** is a module-level constant in
  `prompts.py`, identified as "FinAlly, an AI trading assistant". It
  instructs the model to: analyze portfolio composition, risk, and
  P&L; suggest trades with reasoning; auto-execute trades the user asks
  for (no confirmation needed); manage the watchlist; be concise and
  data-driven; always respond via the structured output schema. Exact
  wording is Claude's discretion (see below).

- **D-16:** **Portfolio context is a JSON blob** (not markdown, not
  prose). `build_portfolio_context(conn, cache)` returns:
  ```json
  {
    "cash_balance": 8087.7,
    "total_value": 10123.4,
    "positions": [
      {"ticker": "AAPL", "quantity": 10, "avg_cost": 191.23,
       "current_price": 193.0, "unrealized_pnl": 17.7,
       "change_percent": 0.93}
    ],
    "watchlist": [
      {"ticker": "AAPL", "price": 193.0, "change_percent": 0.93}
    ]
  }
  ```
  Built by reusing `portfolio.service.get_portfolio` and
  `watchlist.service.get_watchlist` (no duplicated SQL). Serialized
  with `model_dump(mode="json")` and embedded as a system-role message
  after the static system prompt, labelled `"# Current portfolio state\n"`
  then the JSON. Rationale: token-efficient, easy for the LLM to parse,
  matches the structured-output ethos.

- **D-17:** **Conversation history window** is the **last 20 messages**
  (10 user + 10 assistant turns nominally) from `chat_messages` ordered
  `created_at ASC`, inserted between the portfolio-context system
  message and the new user message. No token counting, no summary
  compaction — simple bounded window. Each historical row is rendered as
  `{"role": role, "content": content}` (the `actions` JSON is
  dropped from the prompt to save tokens; history replay from
  `GET /api/chat/history` still returns it). Window size `CHAT_HISTORY_WINDOW
  = 20` is a module constant in `prompts.py`.

### Persistence Ordering

- **D-18:** **Write the user turn BEFORE calling the LLM**, write the
  assistant turn AFTER auto-exec resolves (so `actions` JSON reflects
  real outcomes). On LLM failure (D-14), only the user turn exists in
  `chat_messages` — intentional: the LLM call was logged as attempted,
  and the history stays consistent with `actions IS NULL` for user
  rows. One `conn.commit()` per turn, matching Phase 3 D-12 and Phase
  4 D-09.

### History Endpoint

- **D-19:** `GET /api/chat/history` returns
  `HistoryResponse { messages: list[ChatMessage] }` where `ChatMessage`
  is `{id, role, content, actions (parsed JSON or null), created_at}`,
  ordered `created_at ASC`. Query parameter
  `limit: int = Query(default=50, ge=1, le=500)`. When `limit` is
  smaller than the total row count, return the **most recent** `limit`
  rows but still ordered ASC (subquery: `SELECT ... FROM (SELECT ...
  ORDER BY created_at DESC LIMIT ?) ORDER BY created_at ASC`).
  Rationale: Phase 8 frontend renders the tail of the conversation on
  reload, needs chronological order for display but only the tail for
  bandwidth.

### Lifespan Integration

- **D-20:** `lifespan` additions (additive; no existing lines change):
  1. `chat_client = create_chat_client()` after `source = create_market_data_source(cache)`.
  2. `app.state.chat_client = chat_client` alongside the other state attachments.
  3. `app.include_router(create_chat_router(conn, cache, source, chat_client))`
     after the watchlist router mount (line 68).
  No new DB schema (chat_messages already exists from Phase 2 DB-01).
  No new env vars beyond `LLM_MOCK` (already loaded by Phase 1 D-01).

### Dependencies

- **D-21:** Add `litellm` as a runtime dependency in
  `backend/pyproject.toml`. The `cerebras` skill lists `litellm` +
  `pydantic`; `pydantic` already arrives transitively via FastAPI, but
  declare it explicitly (`pydantic>=2.0.0`) so the Phase 5 team isn't
  relying on a transitive pin. No other new deps.

### Claude's Discretion

Planner may pick the conventional answer without re-asking.

- **Exact wording of the system prompt.** Keep concise; emphasize
  structured-output compliance and demo-quality responses. Do not
  include emojis (CONVENTIONS.md).
- **Mock regex phrasing.** The four patterns in D-06 are the
  contract; exact word-boundary / case-insensitivity nits are
  implementation detail.
- **StructuredResponse Pydantic model location.** Either
  `app/chat/models.py` (preferred) or a dedicated
  `app/chat/schema.py`. Either is fine.
- **Test-fixture pattern for the chat client.** Prefer a
  `MockChatClient` instance injected into `create_chat_router` for
  route tests, and lifespan-level `LLM_MOCK=true` env override for
  `test_main.py`-style integration tests. Match the module-scoped
  fixture pattern established in Phase 4 02-integration tests.
- **Router prefix / tags.** `prefix="/api/chat"`, `tags=["chat"]`
  on the APIRouter itself, matching Phase 3/4 routers.
- **`asyncio.to_thread` for `litellm.completion`.** Preferred; but if
  LiteLLM exposes a true async API in a current version, use that
  instead (rule: "latest APIs").
- **Pydantic field for `quantity`.** Follow Phase 3 `TradeRequest`
  (`quantity: float = Field(gt=0)`). LLM structured outputs emit JSON
  numbers — Python float is fine for fractional share support.
- **Log levels.** `INFO` for each auto-exec action (one line
  per action, ticker + status), `WARNING` with `exc_info=True` for
  unexpected auto-exec exceptions, `ERROR` with `exc_info=True` for
  LLM call failures. Match `seed_defaults` / `execute_trade` log
  style (`%`-placeholders, no f-strings).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification (the source of truth)
- `planning/PLAN.md` §5 — `LLM_MOCK=true` behavior (deterministic
  mock responses). Backs D-05, D-06.
- `planning/PLAN.md` §7 — `chat_messages` schema: `id`, `user_id`,
  `role ∈ {user, assistant}`, `content`, `actions` (JSON, null on
  user rows), `created_at`. Already live in
  `backend/app/db/schema.py`. Backs D-08, D-18.
- `planning/PLAN.md` §8 — API endpoint table for `POST /api/chat`.
  Backs D-07. History endpoint is additive (D-19).
- `planning/PLAN.md` §9 — LLM integration contract: prompt
  assembly, LiteLLM → OpenRouter → Cerebras, structured output
  schema (`message`, `trades[]`, `watchlist_changes[]`), auto-
  execution semantics, mock mode. Backs D-03, D-04, D-06, D-09,
  D-10, D-15, D-16, D-17.

### Project planning
- `.planning/REQUIREMENTS.md` — CHAT-01..CHAT-06 and TEST-01 (the
  seven requirements this phase delivers).
- `.planning/ROADMAP.md` — Phase 5 "Success Criteria" (all five must
  evaluate TRUE, especially #4 "failures reflected back, not swallowed"
  and #5 mock-mode determinism).
- `.planning/PROJECT.md` — Constraints: no over-engineering, latest
  APIs, `%`-style logging, no emojis, short modules + functions.
  "Demo-grade polish and inline AI-driven trade execution are non-
  negotiable" — backs D-09 watchlist-first.
- `.planning/phases/01-app-shell-config/01-CONTEXT.md` — `app.state`
  pattern (D-02), factory-closure routers mounted in lifespan (D-04),
  `python-dotenv` + `.env` at startup (D-07 in that file).
  Backs D-05, D-20.
- `.planning/phases/02-database-foundation/02-CONTEXT.md` — one
  long-lived `sqlite3.Connection` on `app.state.db`, manual commit per
  write path. Backs D-18.
- `.planning/phases/03-portfolio-trading-api/03-CONTEXT.md` —
  sub-package mirror + pure-function service + Pydantic v2 + factory
  router + error contract (TradeValidationError subclasses → 400).
  Backs D-01, D-02, D-12.
- `.planning/phases/04-watchlist-api/04-CONTEXT.md` — service-layer
  idempotent add/remove with `status` discriminator; ticker
  normalization at Pydantic edge; DB-first-then-source ordering.
  Backs D-02, D-07 watchlist block, D-13.

### Codebase intel
- `.planning/codebase/CONVENTIONS.md` — module docstring,
  `from __future__ import annotations`, `%`-style logging, narrow
  exception handling at boundaries, no emojis, factory routers.
- `.planning/codebase/ARCHITECTURE.md` — strategy pattern for market
  data (applies directly to the `ChatClient` protocol design).
- `.planning/codebase/STRUCTURE.md` — `app/portfolio/`, `app/watchlist/`
  sub-package layouts that `app/chat/` mirrors.
- `.planning/codebase/CONCERNS.md` — OPENROUTER_API_KEY absence is
  logged as a warning only at startup (Phase 1 decision); Phase 5
  fails loud at call time (D-14).

### Project skills
- `.claude/skills/cerebras/SKILL.md` — exact code shape for
  `litellm.completion` + `response_format=StructuredResponse` +
  `extra_body={"provider": {"order": ["cerebras"]}}`. Backs D-04.

### Reusable code touched by Phase 5
- `backend/app/lifespan.py` — append `chat_client` construction + router
  mount after the watchlist mount (line 68). No other changes.
- `backend/app/main.py` — unchanged (router mount lives in lifespan,
  Phase 1 D-04 pattern).
- `backend/app/db/schema.py` — `chat_messages` table already created
  by Phase 2; no schema change needed.
- `backend/app/portfolio/service.py:83-211` — `execute_trade` called
  directly by the chat service auto-exec loop. Sync, commits internally.
- `backend/app/portfolio/service.py:31-58` — `TradeValidationError`
  hierarchy translated to D-07 failure entries (D-12 table).
- `backend/app/portfolio/service.py:228-272` — `get_portfolio` reused
  by `build_portfolio_context`.
- `backend/app/watchlist/service.py:86-135` — `add_ticker` /
  `remove_ticker` called by the auto-exec loop. Pure functions, commit
  internally.
- `backend/app/watchlist/service.py:37-83` — `get_watchlist` reused
  by `build_portfolio_context`.
- `backend/app/market/interface.py` — `add_ticker` / `remove_ticker`
  async contract awaited by the auto-exec loop (same hand-off as Phase
  4 routes).
- `backend/app/market/massive_client.py:97` — `asyncio.to_thread`
  precedent for wrapping the sync `litellm.completion` call.
- `backend/app/portfolio/models.py` — template for Pydantic v2
  request/response models.
- `backend/tests/conftest.py` — `_build_app` helper + module-scoped
  lifespan fixture pattern (Phase 4 04-02) — extend for chat route
  integration tests with a `MockChatClient` injection.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`app.state.db`, `app.state.price_cache`, `app.state.market_source`**
  — attached in `backend/app/lifespan.py`. Phase 5 adds
  `app.state.chat_client`.
- **`portfolio.service.execute_trade(conn, cache, ticker, side, qty)`**
  — sync, validates + commits, raises typed exceptions. Auto-exec
  calls this directly.
- **`watchlist.service.add_ticker(conn, ticker)` /
  `remove_ticker(conn, ticker)`** — sync, idempotent, return
  `AddResult` / `RemoveResult`. Auto-exec calls these then awaits
  `source.add_ticker` / `source.remove_ticker` (same flow as the
  Phase 4 routes).
- **`portfolio.service.get_portfolio` + `watchlist.service.get_watchlist`**
  — used by `prompts.build_portfolio_context` to avoid duplicated
  SQL.
- **Pydantic v2 models with `extra="forbid"` + `field_validator`** —
  template: `backend/app/portfolio/models.py`,
  `backend/app/watchlist/models.py`.
- **Factory-closure routers mounted in lifespan** —
  `create_stream_router` / `create_portfolio_router` /
  `create_watchlist_router` are the direct templates for
  `create_chat_router`.
- **`asyncio.to_thread` for sync third-party calls** —
  `MassiveDataSource._poll_once` (`massive_client.py:97`) is the
  precedent for wrapping `litellm.completion`.
- **Module-scoped lifespan fixture pattern** — Phase 4 Plan 04-02
  integration tests (`tests/watchlist/test_routes.py`) show the
  `pytest_asyncio.fixture(loop_scope="module", scope="module")` +
  `LifespanManager` pattern; Phase 5 tests extend it by overriding
  `create_chat_client` via env var (`LLM_MOCK=true`) or by passing a
  `MockChatClient` explicitly to `create_chat_router` in route tests.
- **`cerebras` skill** — exact LiteLLM call signature including
  `response_format=PydanticModel`, `reasoning_effort="low"`, and
  `extra_body={"provider": {"order": ["cerebras"]}}`.

### Established Patterns
- Factory-closure routers; no module-level router objects.
- One long-lived `sqlite3.Connection` with `check_same_thread=False`
  and `sqlite3.Row` rows — shared across services, never opened per
  request.
- Explicit `conn.commit()` inside each service write path.
- `%`-style logging — never f-strings in log calls.
- Narrow exception handling only at boundaries
  (`try/except Exception` + `logger.exception` around the LLM call
  and the auto-exec loop body; nothing else wraps more than it needs).
- Pure sync service functions on `sqlite3.Connection`; async is used
  only where I/O genuinely blocks (LLM call, market source add/remove).
- Short modules / short functions. Target: `app/chat/service.py` ≤150
  lines after splitting `run_turn` into helpers; `client.py` ≤80
  lines; `mock.py` ≤80 lines.

### Integration Points
- `backend/app/lifespan.py` — three additive lines
  (client construction, `app.state` attachment, router mount) after
  the watchlist router mount (line 68).
- `backend/app/main.py` is untouched.
- `backend/app/db/schema.py` is untouched (chat_messages already
  defined).
- `backend/tests/conftest.py` — `_build_app()` extends cleanly; add a
  `mock_chat_client` fixture for route tests.
- `backend/CLAUDE.md` — extend "Public imports" after this phase:
  `from app.chat import create_chat_router, create_chat_client,
  MockChatClient`.

</code_context>

<specifics>
## Specific Ideas

- The auto-exec contract intentionally mirrors the manual HTTP
  flow. Anything you can do by hand (`POST /api/portfolio/trade`,
  `POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`) is what the
  LLM ends up triggering — same validations, same error codes, same
  idempotency. That's the point: the LLM is just another caller.
- The keyword-scripted mock client (D-06) is how Phase 10's §12 E2E
  scenario "AI chat (mocked): send a message, receive a response,
  trade execution appears inline" actually works. Without it, E2E
  would need a live LLM key.
- JSON-blob portfolio context (D-16) means the Phase 5 prompt cost
  scales linearly with position count but is bounded for a single-
  user demo. Token-counting compaction can come later (CHAT-07 or a
  v2 ticket).
- 20-message history window (D-17) is the simplest bounded policy.
  For a typical demo session (<30 minutes) the user won't hit the
  cap; when they do, the window slides and older context is lost —
  acceptable for v1.

</specifics>

<deferred>
## Deferred Ideas

- **Token-budget history compaction / summarization.** CHAT-07 (v2)
  also covers streaming; history compaction follows when the
  single-user demo outgrows the 20-message window.
- **Clear-history / delete-history endpoints.** No UI for this in
  v1; easy to add if needed.
- **Bulk trade-rollback on partial failure.** Out of scope —
  continue-on-failure semantics (D-10) are the explicit contract.
- **Retry-with-backoff on LLM transient errors.** Single failure
  surfaces as 502 (D-14); the user/chat UI can resend. Not worth
  the state machine complexity for v1.
- **Retry-after-watchlist-add to warm the cache for a follow-up
  trade** (D-11). Revisit if the LLM frequently emits "add + buy"
  combinations and the `price_unavailable` rate is high enough to
  hurt the demo.
- **Per-turn cost / latency telemetry.** Useful once the app ships;
  out of scope for the capstone demo.
- **Request-level concurrency control on `/api/chat`.** Single-user
  demo — concurrent posts are unlikely. If v2 adds auth, serialize
  per-`user_id` with an `asyncio.Lock` dict.
- **Dedicated chat-session boundary.** History is one flat thread
  per `user_id`. Multi-thread/session modeling is a v2 concern.
- **Structured-output schema versioning.** PLAN.md §9 schema is
  treated as v1 and frozen for Phase 5. Schema changes require a
  new phase / contract bump.

</deferred>

---

*Phase: 05-ai-chat-integration*
*Context gathered: 2026-04-21*
