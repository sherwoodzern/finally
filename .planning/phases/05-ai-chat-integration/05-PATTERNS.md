# Phase 5: AI Chat Integration - Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 22 (7 new production modules, 1 modified production module, 12 new test modules, 1 config edit, 1 docs edit)
**Analogs found:** 21 / 22 (prompts.py has a light analog only; all others are exact-match to Phase 3/4 counterparts)

## File Classification

### New Production Modules (backend/app/chat/)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `backend/app/chat/__init__.py` | package-facade (public re-export) | n/a | `backend/app/watchlist/__init__.py`, `backend/app/portfolio/__init__.py` | exact |
| `backend/app/chat/models.py` | pydantic schemas (request/response + structured output + history) | request-response + transform | `backend/app/watchlist/models.py`, `backend/app/portfolio/models.py` | exact |
| `backend/app/chat/client.py` | strategy provider + factory (live LLM call) | request-response (outbound HTTP via SDK) | `backend/app/market/factory.py` (env-driven factory) + `backend/app/market/massive_client.py:91-130` (asyncio.to_thread wrap) + `.claude/skills/cerebras/SKILL.md` (LiteLLM call shape) | role-match (new shape: Protocol, not ABC) |
| `backend/app/chat/mock.py` | strategy provider (deterministic test double) | transform (regex over input string) | `backend/app/market/simulator.py` (in-process deterministic data source) | role-match (much simpler; no background task) |
| `backend/app/chat/prompts.py` | constants + pure helper (prompt assembly) | transform | `backend/app/market/seed_prices.py` (constants-only module) + light borrow from `backend/app/portfolio/service.py:228-272` for the read-composition pattern | partial (constants-module shape + service-read composition; no perfect analog) |
| `backend/app/chat/service.py` | pure-function service (orchestration + auto-exec loop) | CRUD + request-response | `backend/app/portfolio/service.py:83-211` (execute_trade) + `backend/app/watchlist/service.py:86-135` (add_ticker/remove_ticker) | exact (combines both patterns) |
| `backend/app/chat/routes.py` | HTTP edge (factory-closure router) | request-response | `backend/app/watchlist/routes.py:23-94` + `backend/app/portfolio/routes.py:21-61` | exact |

### New Tests (backend/tests/chat/)

| New File | Role | Closest Analog | Match Quality |
|----------|------|----------------|---------------|
| `backend/tests/chat/__init__.py` | test-package marker | `backend/tests/watchlist/__init__.py` | exact |
| `backend/tests/chat/conftest.py` | shared fixtures (fresh_db, warmed_cache, mock_chat_client) | `backend/tests/watchlist/conftest.py`, `backend/tests/portfolio/conftest.py` | exact |
| `backend/tests/chat/test_models.py` | unit tests for Pydantic validators + StructuredResponse parse | `backend/tests/watchlist/test_models.py` | exact |
| `backend/tests/chat/test_mock_client.py` | unit tests for MockChatClient regex map | no direct analog; tests a pure transform module | partial |
| `backend/tests/chat/test_prompts.py` | unit tests for build_portfolio_context + build_messages + history window | `backend/tests/portfolio/test_service_portfolio.py` (read-composition) | role-match |
| `backend/tests/chat/test_service_run_turn.py` | unit tests for happy path auto-exec | `backend/tests/portfolio/test_service_buy.py` + `backend/tests/watchlist/test_service_add.py` | exact |
| `backend/tests/chat/test_service_failures.py` | unit tests for per-action failure translation (D-12 matrix) | `backend/tests/portfolio/test_service_validation.py` | exact |
| `backend/tests/chat/test_service_persistence.py` | unit tests for chat_messages write ordering (D-18) | `backend/tests/portfolio/test_service_buy.py` (DB write verification) | role-match |
| `backend/tests/chat/test_client_live.py` | smoke test for LiveChatClient (skipped if no OPENROUTER_API_KEY) | no direct analog; new pattern | partial |
| `backend/tests/chat/test_routes_chat.py` | integration test for POST /api/chat via LifespanManager + httpx | `backend/tests/watchlist/test_routes_post.py` | exact |
| `backend/tests/chat/test_routes_history.py` | integration test for GET /api/chat/history (ordering + limit + NULL actions) | `backend/tests/watchlist/test_routes_delete.py` (module-scoped lifespan) | exact |
| `backend/tests/chat/test_routes_llm_errors.py` | integration test for LLM failure → 502, user turn persisted, assistant NOT persisted | `backend/tests/watchlist/test_routes_post.py` (test_source_failure_after_commit_returns_200_and_logs_warning at :128-155) | role-match |

### Modified Files

| File | Change | Notes |
|------|--------|-------|
| `backend/app/lifespan.py` | 3 additive lines (D-20) | Insert after line 56 (`source = create_market_data_source(cache)`), after line 63 (`app.state.market_source = source`), and after line 68 (`app.include_router(create_watchlist_router(conn, cache, source))`) |
| `backend/pyproject.toml` | Add `litellm>=1.83.10` and `pydantic>=2.0.0` to `[project].dependencies` | Pydantic already arrives transitively via FastAPI; explicit pin per D-21 |
| `backend/CLAUDE.md` | Documentation — public imports note | Append after the "Market Data API" section: `from app.chat import create_chat_router, create_chat_client, MockChatClient, ChatClient, run_turn` |

## Shared Patterns

### Module Header (applies to ALL new .py files)

**Source:** every module in `backend/app/`.
**Apply to:** all new chat package modules.

```python
"""<one-line module docstring describing role>."""

from __future__ import annotations
```

Citations:
- `backend/app/watchlist/models.py:1-3` (docstring + `from __future__`)
- `backend/app/watchlist/service.py:1-4`
- `backend/app/portfolio/service.py:1-3`
- `backend/app/market/factory.py:1-5`

### Logger Setup (applies to service.py, client.py, routes.py)

**Source:** any module that logs.

```python
import logging

logger = logging.getLogger(__name__)
```

**Constraint (CONVENTIONS.md):** `%`-placeholders only; never f-strings in `logger.<level>` calls. Example:

```python
logger.info("Watchlist: added %s for user %s", ticker, user_id)   # backend/app/watchlist/service.py:106
logger.info("Trade executed: %s %s x %.4f @ %.2f (cash=%.2f)",    # backend/app/portfolio/service.py:193
            ticker, side, quantity, price, new_cash)
```

### User-ID Constant

**Source:** `backend/app/portfolio/service.py:25`, `backend/app/watchlist/service.py:18`.

```python
DEFAULT_USER_ID = "default"
```

**Apply to:** `chat/service.py` and `chat/prompts.py` (both filter `chat_messages` by `user_id`). Import from `app.watchlist.service` or re-declare — existing code does the latter, so the chat service should follow suit (CONVENTIONS.md "short modules, clear names" trumps DRY on this one constant).

### Factory-Closure Router (applies to routes.py)

**Source:** `backend/app/watchlist/routes.py:23-94`, `backend/app/portfolio/routes.py:21-61`.

**Apply to:** `chat/routes.py` — MUST be a factory that returns a fresh `APIRouter` per call. **Never** define a module-level `router = APIRouter(...)` and decorate it.

```python
# backend/app/watchlist/routes.py:23-41 (analog)
def create_watchlist_router(
    db: sqlite3.Connection,
    cache: PriceCache,
    source: MarketDataSource,
) -> APIRouter:
    """Build an APIRouter closed over db + cache + source (D-13).

    A fresh router per call mirrors create_stream_router and create_portfolio_router
    and avoids duplicate routes across test-spawned apps.
    """
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])
    ...
    return router
```

### Per-Write `conn.commit()` (applies to service.py)

**Source:** `backend/app/portfolio/service.py:191`, `backend/app/watchlist/service.py:105,129`.

**Apply to:** `chat/service._persist_user_turn` and `chat/service._persist_assistant_turn` — each helper issues exactly one `conn.commit()` after its INSERT (D-18). `run_turn` commits twice per successful turn (once after user, once after assistant); once per failed turn (user only).

### Narrow Exception Handling at Boundaries

**Source:** `backend/app/market/massive_client.py:96-129`, `backend/app/market/simulator.py` (`_run_loop` uses `logger.exception`).

**Rule (CONVENTIONS.md):** Do NOT wrap broad `try/except Exception` anywhere except:
1. The LLM call itself in `run_turn` (→ `ChatTurnError` → route maps to 502, D-14).
2. Each per-action body in the auto-exec loop (→ `status="failed"` with `error="internal_error"`, D-12 fallback row).

The `try/except` in `watchlist/routes.py:56-64` shows the shape to mirror for the auto-exec loop:

```python
# backend/app/watchlist/routes.py:55-64
if result.status == "added":
    try:
        await source.add_ticker(req.ticker)
    except Exception:
        # D-11: DB is the reconciliation anchor; next restart heals.
        logger.warning(
            "Watchlist: source.add_ticker(%s) raised after DB commit",
            req.ticker,
            exc_info=True,
        )
```

### Test-Module Common Header

**Source:** `backend/tests/watchlist/test_service_add.py:1-5`, `backend/tests/portfolio/test_service_validation.py:1-13`.

**Apply to:** every chat test module.

```python
"""<one-line describing what the test module covers>."""

from __future__ import annotations

<imports under test>
```

### Test Class Grouping

**Source:** `backend/tests/watchlist/test_service_add.py:14-42`, `backend/tests/portfolio/test_service_validation.py:27-81`.

**Apply to:** all chat test modules. One class per behavior cluster; one `test_*` method per invariant.

```python
class TestAddTicker:
    def test_new_ticker_commits_row_and_returns_added(self, fresh_db):
        ...
    def test_duplicate_returns_exists_and_leaves_count_unchanged(self, fresh_db):
        ...
```

---

## Pattern Assignments

### `backend/app/chat/__init__.py` (package-facade)

**Analog:** `backend/app/watchlist/__init__.py` (exact), `backend/app/portfolio/__init__.py` (secondary).

**Imports pattern + `__all__`** (`backend/app/watchlist/__init__.py:1-43`):

```python
"""Watchlist subsystem for FinAlly.

Public API:
    Models: WatchlistAddRequest, WatchlistItem, WatchlistResponse,
            WatchlistMutationResponse, normalize_ticker
    Service: get_watchlist, add_ticker, remove_ticker, AddResult, RemoveResult,
             DEFAULT_USER_ID
    Router: create_watchlist_router
"""

from __future__ import annotations

from .models import (
    WatchlistAddRequest,
    ...
)
from .routes import create_watchlist_router
from .service import (
    DEFAULT_USER_ID,
    AddResult,
    ...
)

__all__ = [
    "DEFAULT_USER_ID",
    "AddResult",
    ...
]
```

**Delta for chat:**
- Docstring lists `Models`, `Client`, `Service`, `Router` sections (extra "Client" section for the `ChatClient` Protocol + `create_chat_client()`).
- Re-exports: `ChatClient`, `create_chat_client`, `MockChatClient` (from `.client` and `.mock`), `StructuredResponse`, `ChatRequest`, `ChatResponse`, `HistoryResponse`, `ChatMessageOut` (from `.models`), `run_turn`, `get_history`, `ChatTurnError` (from `.service`), `create_chat_router` (from `.routes`).
- `__all__` is alphabetized (matching watchlist/portfolio ordering).

**Key constraints:** Every public symbol MUST appear in `__all__`; `backend/CLAUDE.md` documents these as the project's public API; no deep imports.

---

### `backend/app/chat/models.py` (pydantic schemas)

**Analog:** `backend/app/watchlist/models.py` (exact — has `ConfigDict(extra="forbid")`, `field_validator`, ticker normalization), `backend/app/portfolio/models.py` (secondary — has `Field(gt=0)` for quantity).

**Imports pattern** (`backend/app/watchlist/models.py:1-11`):

```python
"""Pydantic v2 request/response schemas + ticker normalization for the watchlist API."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")
```

**Ticker normalizer (reuse, do not duplicate)** — `backend/app/watchlist/models.py:13-24`:

```python
def normalize_ticker(value: str) -> str:
    """Strip + uppercase + regex-validate a ticker symbol.

    Raises ValueError if the normalized form does not match ^[A-Z][A-Z0-9.]{0,9}$.
    The regex (1) forces a leading alpha, (2) allows digits/dot for classes like
    BRK.B, and (3) caps total length at 10 chars so SQL injection surfaces stay
    narrow (D-04).
    """
    v = value.strip().upper()
    if not _TICKER_RE.fullmatch(v):
        raise ValueError(f"invalid ticker: {value!r}")
    return v
```

**Request model with `extra="forbid"` + `field_validator`** — `backend/app/watchlist/models.py:27-42`:

```python
class WatchlistAddRequest(BaseModel):
    """Request body for POST /api/watchlist (D-03, D-04).

    extra='forbid' rejects unknown keys with 422. The before-mode validator
    normalizes the ticker before the regex enforces shape; downstream handlers
    can trust `request.ticker` is already uppercase and valid.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_ticker(v)
```

**Literal + `Field(gt=0)` pattern for trades** — `backend/app/portfolio/models.py:10-22`:

```python
class TradeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str = Field(min_length=1, max_length=10)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
```

**Literal-union response status** — `backend/app/watchlist/models.py:68-76`:

```python
class WatchlistMutationResponse(BaseModel):
    ticker: str
    status: Literal["added", "exists", "removed", "not_present"]
```

**Delta for chat:**
- Reuse `normalize_ticker` via `from app.watchlist.models import normalize_ticker` (D-13 — no duplicated regex). Cite: research `Don't Hand-Roll` table.
- **Structured-output sub-models MUST all have `model_config = ConfigDict(extra="forbid")`** (Pitfall 2 — OpenAI structured outputs require `additionalProperties: false` on every nested object). Affected models: `StructuredResponse`, `TradeAction`, `WatchlistAction`, `ChatRequest`.
- **Field ordering matters** (Pitfall 3): in `StructuredResponse`, `message: str` comes BEFORE `trades: list[TradeAction] = Field(default_factory=list)` and `watchlist_changes: list[WatchlistAction] = Field(default_factory=list)`. Required fields before defaulted fields.
- `TradeAction` and `WatchlistAction` apply the same `@field_validator("ticker", mode="before")` as `WatchlistAddRequest`, but reusing `normalize_ticker` rather than re-declaring the regex.
- `TradeActionResult` and `WatchlistActionResult` models use Optional fields (`price: float | None = None`) since fields populate based on `status`. Use `X | None` per CONVENTIONS.md, never `Optional[X]`.
- `ChatMessageOut.actions: dict | None` — parsed JSON after `json.loads(row["actions"])` in `get_history`, or `None` for user rows (Pitfall 4).
- `ChatResponse` structure matches D-07 exactly — pass-through `message`, list of `TradeActionResult`, list of `WatchlistActionResult`.

**Key constraints:**
- `ConfigDict(extra="forbid")` on ALL structured-output models (avoid Pitfall 2).
- `field_validator` uses `mode="before"` + `@classmethod` + imports `normalize_ticker` from watchlist (D-13, no regex duplication).
- `list[TradeAction] = Field(default_factory=list)` — optional list defaults to `[]`, never `None`, so auto-exec loop iterates unconditionally.

---

### `backend/app/chat/client.py` (live LLM wrapper + Protocol + factory)

**Analog:** `backend/app/market/factory.py` (env-driven factory, exact), `backend/app/market/massive_client.py:91-130` (asyncio.to_thread wrap, exact), `.claude/skills/cerebras/SKILL.md` (LiteLLM call shape, exact).

**Factory pattern** — `backend/app/market/factory.py:16-31`:

```python
def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
```

**asyncio.to_thread for sync third-party SDK** — `backend/app/market/massive_client.py:96-99`:

```python
try:
    # The Massive RESTClient is synchronous — run in a thread to
    # avoid blocking the event loop.
    snapshots = await asyncio.to_thread(self._fetch_snapshots)
```

**LiteLLM structured-output call shape** — `.claude/skills/cerebras/SKILL.md:24-42`:

```python
from litellm import completion
MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

# For Structured Outputs:
response = completion(model=MODEL, messages=messages, response_format=MyBaseModelSubclass, reasoning_effort="low", extra_body=EXTRA_BODY)
result = response.choices[0].message.content
result_as_object = MyBaseModelSubclass.model_validate_json(result)
```

**Delta for chat:**
- **Protocol, not ABC** (D-03): the strategy contract for `ChatClient` is a `typing.Protocol` with one `async def complete(self, messages: list[dict]) -> StructuredResponse: ...` method. No inheritance on implementations. Contrast with `MarketDataSource(ABC)` in `backend/app/market/interface.py:9-69` which has lifecycle (`start`/`stop`/`add_ticker`/`remove_ticker`/`register_tick_observer`) — there ABC pays off.
- **Factory reads `LLM_MOCK`** (D-05): `env == "true"` → `MockChatClient()`; else → `LiveChatClient()`. Mirrors the `MASSIVE_API_KEY` check at `factory.py:24-31`.
- **`LiveChatClient` never reads or stores `OPENROUTER_API_KEY`** (Pitfall 9): LiteLLM picks it up from the environment at call time. Missing key → `AuthenticationError` at `completion()` call → caller maps to HTTP 502 per D-14.
- **Module constants for model + provider** at file top (mirrors `backend/app/market/seed_prices.py` style):
  ```python
  MODEL = "openrouter/openai/gpt-oss-120b"
  EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
  ```
- **Sync `completion` wrapped in `asyncio.to_thread`** (D-04 + Pitfall 1) — NOT `acompletion`. Research cites `github.com/BerriAI/litellm/issues/8060` for `acompletion` + `response_format` divergence.
- **No module-level `completion()` call** (anti-pattern in research): build the client in the factory; never evaluate LiteLLM at import time (`.env` may not be loaded yet).
- **Return type is the parsed Pydantic model**, not the raw `ChatCompletionResponse`. Parse at the client boundary with `StructuredResponse.model_validate_json(response.choices[0].message.content)`.

**Key constraints:**
- `%`-style logging on error paths only; INFO log at completion is optional but low-value (LiteLLM emits its own debug logs).
- `LLM_MOCK` read exactly once, in the factory (NOT per-request — Pitfall 6 / research "anti-patterns").
- Module MUST stay under ~80 lines (CONTEXT.md target).

---

### `backend/app/chat/mock.py` (deterministic test double)

**Analog:** no perfect analog. Closest in structure: `backend/app/market/simulator.py` (in-process deterministic data source) — but mock.py is far simpler: no background task, no lifecycle, pure transform.

**Imports pattern + compiled regex constants** — structure mirrors `backend/app/watchlist/models.py:1-11` for the regex compile idiom:

```python
"""Deterministic keyword-scripted chat client for LLM_MOCK=true (D-06)."""

from __future__ import annotations

import re

from .models import StructuredResponse, TradeAction, WatchlistAction

_TICKER = r"[A-Z][A-Z0-9.]{0,9}"
_QTY = r"\d+(?:\.\d+)?"

_BUY = re.compile(rf"\bbuy\s+({_TICKER})\s+({_QTY})\b", re.IGNORECASE)
_SELL = re.compile(rf"\bsell\s+({_TICKER})\s+({_QTY})\b", re.IGNORECASE)
_ADD = re.compile(rf"\badd\s+({_TICKER})\b", re.IGNORECASE)
_REMOVE = re.compile(rf"\b(?:remove|drop)\s+({_TICKER})\b", re.IGNORECASE)
```

(Research Example 6 has the full implementation shape.)

**Delta for chat:**
- **Module-level compiled regexes** with `re.IGNORECASE` + word boundaries `\b` (Pitfall 7: raw `buy (\w+)` would match "buyout AAPL").
- Class implements the `ChatClient` Protocol structurally — no `class MockChatClient(ChatClient)` inheritance (D-03 Protocol).
- `async def complete(self, messages: list[dict]) -> StructuredResponse` extracts the LAST user message from `messages` (the live client sees the whole stack, the mock only needs the user's latest text for pattern matching).
- Multi-match combination: `_BUY.finditer` → all buy trades; `_SELL.finditer` → all sell trades; both combined via `list + list`. Same for watchlist. One message can have multiple trades AND multiple watchlist changes.
- `message` field on the return is deterministic: `"mock response"` if no match, else `"Mock: executing buy AAPL 10, add PYPL"`-style join. Stable for E2E snapshots.
- Ticker groups constructed via `TradeAction(ticker=..., side=..., quantity=...)` — passes through the Pydantic `field_validator` so downstream code sees already-normalized tickers.

**Key constraints:**
- Module MUST stay under ~80 lines (CONTEXT.md target).
- No imports from `app.watchlist` or `app.portfolio` — mock is isolated from domain services (keeps LLM_MOCK=true test path pristine).
- No emojis in the deterministic message strings (CONVENTIONS.md).

---

### `backend/app/chat/prompts.py` (constants + pure helper)

**Analog:** `backend/app/market/seed_prices.py` (constants-only module shape) + `backend/app/portfolio/service.py:228-272` (`get_portfolio` — pattern for composing reads from the cache + DB into a Pydantic response).

**Constants-only module style** — `backend/app/market/seed_prices.py:1-15`:

```python
"""Seed prices and per-ticker parameters for the market simulator."""

# Realistic starting prices for the default watchlist (as of project creation)
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    ...
}
```

**Read-composition pattern** — `backend/app/portfolio/service.py:228-272` (excerpt 228-244):

```python
def get_portfolio(
    conn: sqlite3.Connection,
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
) -> PortfolioResponse:
    """Return cash, total_value, and positions with live prices falling back to avg_cost."""
    cash_row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?",
        (user_id,),
    ).fetchone()
    cash = float(cash_row["cash_balance"]) if cash_row else 0.0

    rows = conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? "
        "ORDER BY ticker ASC",
        (user_id,),
    ).fetchall()
    ...
```

**Delta for chat (D-15, D-16, D-17):**
- Module-level `SYSTEM_PROMPT: str` constant identifies the assistant as "FinAlly, an AI trading assistant" and specifies the structured-output schema (research Example 4 gives the wording; exact phrasing is Claude's discretion per CONTEXT.md).
- Module-level `CHAT_HISTORY_WINDOW: int = 20` constant (D-17).
- `build_portfolio_context(conn, cache) -> dict` **reuses** `portfolio.service.get_portfolio` and `watchlist.service.get_watchlist` (research "Don't Hand-Roll" — no duplicated SQL). Returns a plain `dict` (not a Pydantic model) so JSON serialization is trivial.
- `build_messages(conn, cache, user_message) -> list[dict]` issues the history query inline (the history-window subquery is not reused outside this module — keep it private). Research Example 4 has the full shape; note the two-level subquery for "most-recent-N ordered ASC":
  ```python
  conn.execute(
      "SELECT role, content FROM ("
      "  SELECT role, content, created_at FROM chat_messages "
      "  WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
      ") ORDER BY created_at ASC",
      ("default", CHAT_HISTORY_WINDOW),
  ).fetchall()
  ```
- `from app.market import PriceCache` — use public import per `backend/CLAUDE.md`.

**Key constraints:**
- No FastAPI imports (pure module; caller is `service.run_turn`).
- `json.dumps(ctx)` when embedding portfolio context as a string (D-16 labelled `"# Current portfolio state\n"`).
- Default user_id filter uses `"default"` — either import `DEFAULT_USER_ID` from `app.watchlist.service` or declare a local `DEFAULT_USER_ID = "default"` (follows Phase 3/4 convention).
- No emojis; no f-strings in logging (there is no logging in this module — it's pure).

---

### `backend/app/chat/service.py` (orchestration + auto-exec + persistence)

**Analog:** `backend/app/portfolio/service.py:83-211` (execute_trade exception hierarchy + commit-at-end), `backend/app/watchlist/service.py:86-135` (idempotent service functions, cursor.rowcount discrimination), and the `try/except Exception` boundary shape from `backend/app/watchlist/routes.py:55-64`.

**Exception hierarchy pattern** — `backend/app/portfolio/service.py:31-58`:

```python
class TradeValidationError(Exception):
    """Base class for trade validation failures (D-09)."""

    code: str = "trade_validation_error"


class InsufficientCash(TradeValidationError):  # noqa: N818
    """Buy rejected: quantity * price exceeds users_profile.cash_balance."""

    code: str = "insufficient_cash"


class InsufficientShares(TradeValidationError):  # noqa: N818
    ...

class UnknownTicker(TradeValidationError):  # noqa: N818
    ...

class PriceUnavailable(TradeValidationError):  # noqa: N818
    ...
```

**INSERT + commit write pattern** — `backend/app/watchlist/service.py:97-111`:

```python
now = datetime.now(UTC).isoformat()
cur = conn.execute(
    "INSERT INTO watchlist (id, user_id, ticker, added_at) "
    "VALUES (?, ?, ?, ?) "
    "ON CONFLICT(user_id, ticker) DO NOTHING",
    (str(uuid.uuid4()), user_id, ticker, now),
)
if cur.rowcount == 1:
    conn.commit()
    logger.info("Watchlist: added %s for user %s", ticker, user_id)
    return AddResult(ticker=ticker, status="added")
```

**Pure-function service signature** — `backend/app/portfolio/service.py:83-95` (with `from __future__ import annotations`):

```python
def execute_trade(
    conn: sqlite3.Connection,
    cache: PriceCache,
    ticker: str,
    side: Literal["buy", "sell"],
    quantity: float,
    user_id: str = DEFAULT_USER_ID,
) -> TradeResponse:
    """Execute a market-order trade: validate, then write cash + position + trade + snapshot.

    All writes happen inside one implicit sqlite3 transaction and commit once at the
    end (D-12). On any validation failure, zero rows are written.
    """
```

**Delta for chat:**
- `async def run_turn(...)` is `async` specifically because it awaits `source.add_ticker` / `source.remove_ticker` in the auto-exec loop (D-02) and awaits `client.complete(messages)`. Everything else (DB writes, `execute_trade`, `add_ticker`, `remove_ticker` on the DB) stays synchronous — do NOT wrap sync calls in `asyncio.to_thread` (Pitfall 10, research "Anti-Patterns").
- **Two helpers for persistence** (D-18): `_persist_user_turn(conn, content)` runs BEFORE the LLM call (so history stays consistent on LLM failure); `_persist_assistant_turn(conn, content, trade_results, watchlist_results)` runs AFTER the auto-exec loop with `actions_json = json.dumps({"trades": [...], "watchlist_changes": [...]})` (Pitfall 4). Each helper has its own `conn.commit()`.
- **One new exception class, `ChatTurnError(Exception)`**, raised when the LLM call fails (D-14). Route translates it to `HTTPException(502, detail={"error": "llm_unavailable", "message": str(exc)})`.
- **Two narrow `try/except` boundaries:** (a) around `await client.complete(...)` → `ChatTurnError`; (b) INSIDE each per-action helper → `status="failed"`. These are the ONLY broad `except Exception` blocks in the module. Research "Anti-Patterns to Avoid" is explicit: "Wrapping the LLM call in the auto-exec try/except Exception block" is forbidden.
- **Auto-exec loop: watchlist FIRST, trades SECOND** (D-09, hard rule). `execute_trade` raises `UnknownTicker` if the ticker isn't in `watchlist`, so `add PYPL` must happen before `buy PYPL 10`.
- **Per-action continue-on-failure** (D-10): the loop NEVER raises on per-action failure; each failure becomes a `TradeActionResult(status="failed", error=<code>, message=<str>)` or `WatchlistActionResult(status="failed", ...)`.
- **Exception-to-code translation table** (D-12, verbatim from research):
  | Exception | Code |
  |-----------|------|
  | `portfolio.service.InsufficientCash` | `insufficient_cash` |
  | `portfolio.service.InsufficientShares` | `insufficient_shares` |
  | `portfolio.service.UnknownTicker` | `unknown_ticker` |
  | `portfolio.service.PriceUnavailable` | `price_unavailable` |
  | `ValueError` (ticker normalization from Pydantic) | `invalid_ticker` |
  | Any other `Exception` | `internal_error` (fallback; `logger.warning(..., exc_info=True)`) |
  All Phase 3 exceptions already carry `.code` — use `exc.code` directly, do not re-map.
- **`get_history(conn, limit, user_id) -> HistoryResponse`** uses the same two-level subquery pattern as the prompt's history query (Pitfall 8) but SELECTs all 5 columns: `id, role, content, actions, created_at`. Parses `actions` with `json.loads(row["actions"]) if row["actions"] is not None else None` (Pitfall 4).
- **Each auto-exec action emits INFO log, fallback uses WARNING with `exc_info=True`** (CONTEXT.md Discretion, Log levels):
  ```python
  logger.info("Chat auto-exec: trade %s %s x %s executed", ticker, side, quantity)
  logger.info("Chat auto-exec: trade %s %s x %s FAILED %s", ticker, side, quantity, exc.code)
  logger.warning("Chat auto-exec: trade %s unexpected error", ticker, exc_info=True)
  logger.error("LLM call failed", exc_info=True)
  ```
- **Watchlist auto-exec mirrors the route choreography** (`backend/app/watchlist/routes.py:55-64`): after `service.add_ticker(db, ticker)` returns `status == "added"`, await `source.add_ticker(ticker)` inside its own small try/except (logs WARNING on source failure, does NOT downgrade the action to failed — DB is the reconciliation anchor per Phase 4 D-11).

**Key constraints:**
- Module target ≤150 lines (CONTEXT.md). Helpers (`_persist_user_turn`, `_persist_assistant_turn`, `_run_one_trade`, `_run_one_watchlist`) keep `run_turn` short.
- No FastAPI imports (pure service; route owns HTTPException translation).
- `from __future__ import annotations` at top.
- `DEFAULT_USER_ID = "default"` constant (mirrors Phase 3/4).
- Timestamps: `datetime.now(UTC).isoformat()` (matches `backend/app/portfolio/service.py:143`, `backend/app/watchlist/service.py:97`).
- Every `chat_messages` query filters `WHERE user_id = ?` (Pitfall 5).

---

### `backend/app/chat/routes.py` (HTTP edge)

**Analog:** `backend/app/watchlist/routes.py:23-94` (exact — factory with all three dependencies), `backend/app/portfolio/routes.py:21-61` (secondary — shows `Query(default=..., ge=..., le=...)` for the history endpoint).

**Factory + POST with service-error translation** — `backend/app/portfolio/routes.py:38-53`:

```python
@router.post("/trade", response_model=TradeResponse)
async def post_trade(request: Request, req: TradeRequest) -> TradeResponse:
    try:
        response = service.execute_trade(
            db, cache, req.ticker, req.side, req.quantity,
        )
    except service.TradeValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": exc.code, "message": str(exc)},
        ) from exc
    ...
```

**Query-parameter constraint pattern** — `backend/app/portfolio/routes.py:55-59`:

```python
@router.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = Query(default=1000, ge=1, le=1000),
) -> HistoryResponse:
    return service.get_history(db, limit=limit)
```

**Delta for chat:**
- Factory signature: `create_chat_router(db, cache, source, client) -> APIRouter` — FOUR dependencies (the chat client joins db/cache/source). Router prefix `/api/chat`, tags `["chat"]` (CONTEXT.md Discretion).
- `POST /api/chat`:
  ```python
  @router.post("", response_model=ChatResponse)
  async def post_chat(req: ChatRequest) -> ChatResponse:
      try:
          return await service.run_turn(db, cache, source, client, req.message)
      except service.ChatTurnError as exc:
          raise HTTPException(
              status_code=502,
              detail={"error": "llm_unavailable", "message": str(exc)},
          ) from exc
  ```
  Note: 502 (not 400) for LLM failures; distinguishes upstream-gateway errors from validation errors.
- `GET /api/chat/history`:
  ```python
  @router.get("/history", response_model=HistoryResponse)
  async def get_chat_history(
      limit: int = Query(default=50, ge=1, le=500),
  ) -> HistoryResponse:
      return service.get_history(db, limit=limit)
  ```
  Limit range (50 default, 1-500) smaller than portfolio history (1000 default) because chat messages are larger strings. (D-19.)
- The route does NOT need `Request` parameter — unlike `post_trade` which uses `request.app.state.last_snapshot_at`, the chat route has no app-state mutation side effect; service owns all state changes.
- No per-action try/except in the route — the service already returned per-action statuses in the `ChatResponse`; the route just serializes.

**Key constraints:**
- Fresh router per call (factory-closure pattern — mandatory per CONTEXT.md).
- `response_model=ChatResponse` / `response_model=HistoryResponse` on every endpoint (matches watchlist/portfolio).
- `from . import service` then use `service.ChatTurnError`, `service.run_turn`, `service.get_history` (matches `backend/app/portfolio/routes.py:12` + `:44`, `backend/app/watchlist/routes.py:12` + `:53,78`).
- Module ≤80 lines.

---

### `backend/app/lifespan.py` (modified — 3 additive lines)

**Analog:** the file itself — edit in place around existing line numbers.

**Current shape** (`backend/app/lifespan.py:55-68`):

```python
    cache = PriceCache()
    source = create_market_data_source(cache)                           # line 56

    tickers = get_watchlist_tickers(conn)
    await source.start(tickers)

    app.state.db = conn
    app.state.price_cache = cache
    app.state.market_source = source                                    # line 63
    app.state.last_snapshot_at = 0.0                                   # D-06
    source.register_tick_observer(make_snapshot_observer(app.state))   # D-05
    app.include_router(create_stream_router(cache))
    app.include_router(create_portfolio_router(conn, cache))
    app.include_router(create_watchlist_router(conn, cache, source))   # line 68 - D-13
```

**Delta for Phase 5 (D-20 — additive only):**
1. Add import at top: `from .chat import create_chat_client, create_chat_router`
2. After line 56: `chat_client = create_chat_client()` (D-20 #1, reads `LLM_MOCK`)
3. After line 63 (alongside `app.state.market_source = source`): `app.state.chat_client = chat_client` (D-20 #2)
4. After line 68 (after watchlist router mount): `app.include_router(create_chat_router(conn, cache, source, chat_client))` (D-20 #3)

**No existing line changes.** The startup WARNING on missing `OPENROUTER_API_KEY` at `lifespan.py:45-48` is already in place from Phase 1 and stays as-is (Pitfall 9: "logged as WARNING only, explicitly NOT crashing"; Phase 5 fails loud at call time, not at startup).

**Key constraints:**
- Additive only — do not reorder the existing lines.
- Import order: package-absolute `.chat` import goes with the other subsystem imports at lines 11-14.
- The `logger.info(..., "App started: ...")` block at lines 70-75 can optionally include the chat client type (e.g., `type(chat_client).__name__`) but CONTEXT.md says additive only — leave it alone unless needed for debug visibility.

---

### `backend/pyproject.toml` (modified)

**Current `[project].dependencies` block** (`backend/pyproject.toml:7-14`):

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "numpy>=2.0.0",
    "massive>=1.0.0",
    "rich>=13.0.0",
    "python-dotenv>=1.2.1",
]
```

**Delta (D-21):**
- Add `"litellm>=1.83.10"` — pinned to the current latest per research Standard Stack.
- Add `"pydantic>=2.0.0"` — explicit declaration of the transitive FastAPI dependency.

**Resulting block:**

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "numpy>=2.0.0",
    "massive>=1.0.0",
    "rich>=13.0.0",
    "python-dotenv>=1.2.1",
    "litellm>=1.83.10",
    "pydantic>=2.0.0",
]
```

**Installation command** (research Standard Stack):

```bash
cd backend && uv add litellm pydantic
```

`uv add` updates both `pyproject.toml` and `uv.lock` atomically — CONVENTIONS.md rule "always uv add, never pip install."

---

### `backend/CLAUDE.md` (documentation)

**Current shape:** has a `## Market Data API` section that documents public imports.

**Delta:** Add a new `## Chat API` section after the Market Data section with the same structure. Key entry:

```markdown
## Chat API

The AI chat subsystem lives in `app/chat/`. Use these imports:

\`\`\`python
from app.chat import (
    create_chat_router,
    create_chat_client,
    ChatClient,
    MockChatClient,
    run_turn,
)
\`\`\`
```

---

## Test File Pattern Assignments

### `backend/tests/chat/__init__.py`

**Analog:** `backend/tests/watchlist/__init__.py:1`.

```python
"""Tests for chat subsystem."""
```

### `backend/tests/chat/conftest.py`

**Analog:** `backend/tests/watchlist/conftest.py` (exact), `backend/tests/portfolio/conftest.py` (identical structure).

**Copy verbatim** (`backend/tests/watchlist/conftest.py:1-35`):

```python
"""Shared fixtures for watchlist service + route tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from app.db import init_database, seed_defaults
from app.market import PriceCache
from app.market.seed_prices import SEED_PRICES


@pytest.fixture
def fresh_db() -> Iterator[sqlite3.Connection]:
    """Yield a seeded in-memory sqlite3.Connection with sqlite3.Row row factory."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    seed_defaults(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def warmed_cache() -> PriceCache:
    """Return a PriceCache pre-populated with seed prices for the 10 default tickers."""
    cache = PriceCache()
    for ticker, price in SEED_PRICES.items():
        cache.update(ticker=ticker, price=price)
    return cache
```

**Delta for chat:** Add a `mock_chat_client` fixture returning `MockChatClient()`:

```python
from app.chat import MockChatClient


@pytest.fixture
def mock_chat_client() -> MockChatClient:
    """Return a fresh MockChatClient for per-test isolation."""
    return MockChatClient()
```

Optionally add a scripted `FakeChatClient` test double for tests that need to inject a SPECIFIC `StructuredResponse` (rather than drive via user message text). Shape:

```python
class FakeChatClient:
    """Test double that returns a caller-specified StructuredResponse once."""

    def __init__(self, response: StructuredResponse) -> None:
        self._response = response

    async def complete(self, messages: list[dict]) -> StructuredResponse:
        return self._response
```

This FakeChatClient lets `test_service_failures.py` inject responses that trigger specific branches of the D-12 exception translation table without depending on the mock client's regex.

### `backend/tests/chat/test_models.py`

**Analog:** `backend/tests/watchlist/test_models.py:1-72` (exact — tests normalize_ticker + WatchlistAddRequest + literal status).

**Copy the structure directly** (classes: `TestNormalizeTicker`, `TestWatchlistAddRequest`, `TestWatchlistMutationResponse`) and retarget at the chat models. Key test classes for chat:

- `TestStructuredResponse` — parse valid JSON with trades+watchlist_changes, reject `extra` keys, default both lists to `[]` when omitted, reject missing `message`.
- `TestTradeAction` — normalizes ticker, rejects `quantity <= 0`, rejects bad `side`.
- `TestWatchlistAction` — normalizes ticker, rejects bad `action`.
- `TestChatRequest` — rejects empty message (`min_length=1`), rejects extra keys.
- `TestChatMessageOut` — accepts both `actions: dict` and `actions: None` for user rows.

**Cite:** `backend/tests/watchlist/test_models.py:15-43` for ValidationError patterns:

```python
class TestNormalizeTicker:
    def test_strips_and_uppercases(self):
        assert normalize_ticker("  aapl  ") == "AAPL"

    def test_rejects_leading_digit(self):
        with pytest.raises(ValueError, match="invalid ticker"):
            normalize_ticker("1X")
```

### `backend/tests/chat/test_mock_client.py`

**Analog:** no direct test analog. Pure regex-map tests. Structure mirrors `backend/tests/watchlist/test_models.py` class-per-behavior pattern.

**Test classes needed:**
- `TestBuyPattern` — "buy AAPL 10" → one trade; "please buy AAPL 10 shares" → one trade; "buyout AAPL" → zero trades (Pitfall 7 word-boundary).
- `TestSellPattern` — similar.
- `TestAddRemovePattern` — "add PYPL", "remove PYPL", "drop PYPL" → exactly one watchlist change each.
- `TestCombinations` — "add PYPL and buy PYPL 10" → 1 watchlist add + 1 trade.
- `TestNoMatch` — "hello" → `StructuredResponse(message="mock response", trades=[], watchlist_changes=[])`.
- `TestDeterministicMessage` — matched output uses the "Mock: executing ..." format and is stable across calls.

### `backend/tests/chat/test_prompts.py`

**Analog:** `backend/tests/portfolio/test_service_portfolio.py` (read-composition test shape).

**Test classes:**
- `TestBuildPortfolioContext` — returns dict with `cash_balance`, `total_value`, `positions: []`, `watchlist: []` keys; integers serialize as numbers (not strings). Use `fresh_db` + `warmed_cache` fixtures.
- `TestBuildMessages` — system prompt first; portfolio context second; user message last; history rows inserted between portfolio context and user message; ordered ASC by `created_at`; honors `CHAT_HISTORY_WINDOW = 20`.
- `TestChatHistoryWindow` — when > 20 rows exist, only the 20 most recent appear, still ASC ordered.

### `backend/tests/chat/test_service_run_turn.py`

**Analog:** `backend/tests/portfolio/test_service_buy.py` (sync execute_trade tests) + mock client injection pattern.

**Module pytestmark:** `pytest.mark.asyncio` (since `run_turn` is async).

**Test classes:**
- `TestRunTurnHappyPath` — user message "buy AAPL 10" via MockChatClient → one executed trade, `cash_balance` decreased, `position_quantity` increased, both chat_messages rows written.
- `TestRunTurnWatchlistFirst` — "add PYPL and buy PYPL 10" → watchlist `added` status + trade `failed: price_unavailable` (cache cold — D-11).
- `TestRunTurnDefaultMessage` — "hello" → MockChatClient returns empty arrays → no DB changes to positions/watchlist; chat_messages still gets 2 rows (user + assistant with empty `actions` JSON).

### `backend/tests/chat/test_service_failures.py`

**Analog:** `backend/tests/portfolio/test_service_validation.py:27-82` (per-exception DB-counts-unchanged pattern).

**The D-12 exception-to-code matrix:** one test per row.

```python
# Shape mirrors backend/tests/portfolio/test_service_validation.py:30-37:
class TestAutoExecFailureTranslation:
    async def test_insufficient_cash_surfaces_as_failed_action(
        self, fresh_db, warmed_cache
    ):
        """Injected 'buy AAPL 100000' → trade failed, code=insufficient_cash, DB unchanged."""
        client = FakeChatClient(StructuredResponse(
            message="ok", trades=[TradeAction(ticker="AAPL", side="buy", quantity=100000)]
        ))
        result = await run_turn(fresh_db, warmed_cache, FakeSource(), client, "do it")
        assert result.trades[0].status == "failed"
        assert result.trades[0].error == "insufficient_cash"
```

Each failure-path test also asserts the `chat_messages.actions` column on the assistant row contains the `status:"failed"` entry, confirming D-08 enrichment.

### `backend/tests/chat/test_service_persistence.py`

**Analog:** `backend/tests/portfolio/test_service_buy.py` (DB write verification pattern).

**Test classes:**
- `TestUserTurnBeforeLLM` — inject a `FakeChatClient` that raises `RuntimeError` in `.complete()`. After `run_turn` raises `ChatTurnError`, exactly ONE `chat_messages` row exists (the user turn), with `actions IS NULL`.
- `TestAssistantTurnAfterAutoExec` — after a successful turn, assistant row's `actions` column is the JSON string `{"trades": [...], "watchlist_changes": [...]}` with the enriched per-action statuses (D-08).
- `TestChatMessagesUserIdFilter` — second `user_id="other"` row doesn't pollute `get_history` when querying `"default"`.
- `TestCommitPerTurn` — exactly 2 commits per successful turn (verify via `conn.total_changes` sampled before and after).

### `backend/tests/chat/test_client_live.py`

**Analog:** none (new pattern for live-LLM smoke).

```python
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="Requires OPENROUTER_API_KEY for live LLM call",
)

# One small test: build a prompt, call LiveChatClient, assert it returns
# a StructuredResponse with a non-empty `message`. Networked.
```

**Key constraint:** MUST skip when no API key is set — otherwise CI without the key errors. Use `pytestmark` at module scope.

### `backend/tests/chat/test_routes_chat.py`

**Analog:** `backend/tests/watchlist/test_routes_post.py` (module-scoped lifespan, LifespanManager, httpx.AsyncClient + ASGITransport).

**Copy the module-scoped lifespan fixture verbatim** (`backend/tests/watchlist/test_routes_post.py:22-46`):

```python
pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def app_with_lifespan(tmp_path_factory) -> AsyncIterator[FastAPI]:
    db_path = tmp_path_factory.mktemp("chat_routes") / "finally.db"
    app = FastAPI(lifespan=lifespan)
    with patch.dict(os.environ, {"DB_PATH": str(db_path), "LLM_MOCK": "true"}, clear=True):
        async with LifespanManager(app):
            yield app


@pytest_asyncio.fixture(loop_scope="module")
async def client(app_with_lifespan: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app_with_lifespan)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

**Delta for chat:**
- `env` override dict ADDS `"LLM_MOCK": "true"` so `create_chat_client()` returns `MockChatClient` at lifespan entry.
- Test cleanup helpers mirror `_ensure_absent` / `_reinsert_if_missing` but for `chat_messages`: `_wipe_chat(db)` → `db.execute("DELETE FROM chat_messages WHERE user_id = ?", ("default",)); db.commit()` (Pitfall 6 — module-scoped tests must clean up shared state).

**Test classes:**
- `TestPostChatHappyPath` — `POST /api/chat {"message": "buy AAPL 10"}` → 200 with `message` + one executed trade. DB rows: 2 `chat_messages`, 1 `trade`, 1 `position` delta.
- `TestPostChatValidation` — 422 for missing/empty/extra message (mirrors `TestPostValidation` at `test_routes_post.py:158-175`).
- `TestPostChatPersistence` — two `chat_messages` rows after one call; assistant row's `actions` column has the enriched JSON.

### `backend/tests/chat/test_routes_history.py`

**Analog:** `backend/tests/watchlist/test_routes_delete.py` (module-scoped lifespan + cleanup helper pattern).

**Test classes:**
- `TestHistoryOrdering` — multiple POSTs, then `GET /api/chat/history` → rows in ASC order by `created_at`.
- `TestHistoryLimit` — 30 POSTs, `GET /api/chat/history?limit=10` → last 10 rows ordered ASC (Pitfall 8 subquery verification).
- `TestHistoryLimitValidation` — `limit=0` → 422; `limit=501` → 422 (from `Query(ge=1, le=500)`).
- `TestHistoryNullActions` — user rows have `actions: null`, assistant rows have `actions: {trades:[...], watchlist_changes:[...]}` (Pitfall 4).

### `backend/tests/chat/test_routes_llm_errors.py`

**Analog:** `backend/tests/watchlist/test_routes_post.py:128-155` (monkeypatch source method to raise, verify response + logs).

**Test classes:**
- `TestLlmFailureReturns502` — monkeypatch `app.state.chat_client.complete` to raise `RuntimeError("connection refused")`. POST → 502 with `detail.error == "llm_unavailable"` and `detail.message` non-empty.
- `TestLlmFailurePersistsUserTurnOnly` — after the failure above, `SELECT COUNT(*) FROM chat_messages` == 1 (user row), `actions IS NULL`.
- `TestLlmFailureLogsError` — `caplog` captures `ERROR` level with `"LLM call failed"`.

**Monkeypatch shape** (from `test_routes_post.py:135-141`):

```python
original_complete = app.state.chat_client.complete

async def _boom(messages):
    raise RuntimeError("connection refused")

app.state.chat_client.complete = _boom  # type: ignore[assignment]
try:
    resp = await client.post("/api/chat", json={"message": "hi"})
    assert resp.status_code == 502
finally:
    app.state.chat_client.complete = original_complete  # type: ignore[assignment]
```

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `backend/app/chat/prompts.py` | constants + helper | No existing pure "prompt assembly" module. Closest precedent is `seed_prices.py` (constants-only) + `portfolio/service.py` (read composition). New-style module. |
| `backend/tests/chat/test_mock_client.py` | regex-map tests | No existing test module for a pure regex-driven transform. Classes-per-behavior shape from `test_models.py` is the closest template. |
| `backend/tests/chat/test_client_live.py` | live-LLM smoke (skipif) | No prior skipif-on-env-var test in this codebase. New pattern. |

## Summary of Key Constraints (recap for all new files)

- **Module docstring + `from __future__ import annotations`** at top of every new module (CONVENTIONS.md).
- **`%`-placeholders in logging**, never f-strings (CONVENTIONS.md, verified in every existing logger call).
- **No emojis** in code, logs, docstrings, or print statements (CLAUDE.md project rule).
- **`X | None`** type annotations, never `Optional[X]` (CONVENTIONS.md).
- **Short modules / short functions** — targets: `service.py` ≤150, `client.py` ≤80, `mock.py` ≤80, `routes.py` ≤80, `prompts.py` ≤80.
- **Narrow exception handling at boundaries only** — two `try/except Exception` blocks in `service.py` (LLM call → `ChatTurnError`; per-action body → `status="failed"`). Nowhere else.
- **Factory-closure routers** — never module-level `router = APIRouter(...)`.
- **Pure-function services** — no FastAPI imports in `service.py` or `prompts.py`; `routes.py` translates exceptions to `HTTPException`.
- **Pydantic v2 with `ConfigDict(extra="forbid")`** on every request and every structured-output model (Pitfall 2 — structured outputs REQUIRE `additionalProperties: false`).
- **Field ordering**: required fields before defaulted fields (Pitfall 3).
- **`json.dumps` when writing `chat_messages.actions`; `json.loads` with NULL guard when reading** (Pitfall 4).
- **History query uses two-level subquery** for "most recent N ordered ASC" (Pitfall 8, D-19).
- **Filter every `chat_messages` query by `user_id`** (Pitfall 5).
- **`asyncio.to_thread` on `litellm.completion` only** — never on `execute_trade`, `add_ticker`, `remove_ticker` (Pitfall 10, anti-pattern in research).
- **Read `LLM_MOCK` exactly once, in the factory**, never per-request (Pitfall 6, D-05).
- **`LiveChatClient` NEVER reads `OPENROUTER_API_KEY`** — LiteLLM picks it up at call time, Phase 1 D-01 startup WARNING stays as-is (Pitfall 9).
- **Package re-exports via `__all__`** in every `__init__.py` (CONVENTIONS.md + backend/CLAUDE.md "Public imports" rule).
- **Module-scoped lifespan + httpx+ASGITransport + LifespanManager** for route integration tests (Phase 4 Plan 04-02 pattern).

## Metadata

**Analog search scope:** `backend/app/`, `backend/tests/`, `backend/pyproject.toml`, `backend/CLAUDE.md`, `.claude/skills/cerebras/SKILL.md`.
**Files scanned:** 22 production/test files read in full; surface scan of `tests/watchlist/` and `tests/portfolio/` directories for cross-check.
**Pattern extraction date:** 2026-04-21
