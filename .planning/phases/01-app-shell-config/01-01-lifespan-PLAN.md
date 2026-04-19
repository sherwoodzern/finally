---
phase: 01-app-shell-config
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/pyproject.toml
  - backend/app/lifespan.py
autonomous: true
requirements: [APP-01, APP-03]
tags: [fastapi, lifespan, asgi, env-config, market-data]

must_haves:
  truths:
    - "python-dotenv is a runtime dependency declared in backend/pyproject.toml."
    - "backend/app/lifespan.py exposes an `@asynccontextmanager` named `lifespan(app: FastAPI)`."
    - "On startup the lifespan constructs ONE PriceCache, calls create_market_data_source(cache), and awaits source.start(list(SEED_PRICES.keys()))."
    - "On startup the lifespan attaches `cache` to `app.state.price_cache` and `source` to `app.state.market_source`."
    - "On startup the lifespan calls `app.include_router(create_stream_router(cache))` BEFORE yield, so `/api/stream/prices` is reachable for the lifetime of the app."
    - "On shutdown the lifespan awaits `source.stop()`."
    - "Missing OPENROUTER_API_KEY logs a single warning but does not raise."
  artifacts:
    - path: "backend/app/lifespan.py"
      provides: "FastAPI lifespan context manager wiring PriceCache + MarketDataSource + SSE router"
      contains: "@asynccontextmanager"
      min_lines: 25
    - path: "backend/pyproject.toml"
      provides: "python-dotenv runtime dependency"
      contains: "python-dotenv"
  key_links:
    - from: "backend/app/lifespan.py"
      to: "backend/app/market/__init__.py"
      via: "from .market import PriceCache, create_market_data_source, create_stream_router"
      pattern: "from \\.market import .*PriceCache.*create_market_data_source.*create_stream_router"
    - from: "backend/app/lifespan.py"
      to: "backend/app/market/seed_prices.py"
      via: "from .market.seed_prices import SEED_PRICES"
      pattern: "from \\.market\\.seed_prices import SEED_PRICES"
    - from: "backend/app/lifespan.py"
      to: "FastAPI app instance (consumed by main.py)"
      via: "app.state.price_cache, app.state.market_source, app.include_router"
      pattern: "app\\.state\\.price_cache\\s*=|app\\.include_router\\(create_stream_router"
---

<objective>
Add `python-dotenv` as a runtime dependency and create `backend/app/lifespan.py` — a thin
FastAPI lifespan context manager that constructs the shared `PriceCache`, selects and starts
the market data source from `MASSIVE_API_KEY`, mounts the existing `create_stream_router(cache)`
SSE router, and stops the source cleanly on shutdown. Implements decisions D-01 (two-file shell
location), D-02 (PriceCache built inside lifespan, attached to `app.state`, no module globals),
and D-04 (SSE router included during lifespan startup).

Purpose: Provides the producer/consumer wiring that makes APP-01 ("FastAPI lifespan that
constructs the shared PriceCache, selects and starts the market data source") and APP-03
(`.env` loading for the three project env vars) achievable in a single small module.
Output: `backend/app/lifespan.py` (one async context manager) + the dotenv dependency.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@backend/CLAUDE.md
@planning/PLAN.md
@.planning/phases/01-app-shell-config/01-CONTEXT.md
@.planning/phases/01-app-shell-config/01-PATTERNS.md
@.planning/codebase/CONVENTIONS.md
@backend/app/market/__init__.py
@backend/app/market/factory.py
@backend/app/market/stream.py
@backend/app/market/seed_prices.py
@backend/app/market/simulator.py
@backend/pyproject.toml

<interfaces>
<!-- Public contracts the executor uses directly. No codebase exploration needed. -->

From backend/app/market/__init__.py (public surface — import from `app.market`, never deep paths):
```python
from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import PriceUpdate
from .stream import create_stream_router

__all__ = [
    "PriceUpdate", "PriceCache", "MarketDataSource",
    "create_market_data_source", "create_stream_router",
]
```

From backend/app/market/factory.py (env-driven selection — already correct, do NOT re-validate
in lifespan):
```python
def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """MASSIVE_API_KEY set and non-empty -> MassiveDataSource; otherwise SimulatorDataSource.
    Returns an unstarted source. Caller must await source.start(tickers).
    """
```

From backend/app/market/stream.py (returns an APIRouter with prefix "/api/stream"):
```python
def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Factory returns an APIRouter exposing GET /api/stream/prices (text/event-stream)."""
```

From backend/app/market/interface.py (lifecycle contract):
```python
class MarketDataSource(abc.ABC):
    async def start(self, tickers: list[str]) -> None: ...
    async def stop(self) -> None: ...
    async def add_ticker(self, ticker: str) -> None: ...
    async def remove_ticker(self, ticker: str) -> None: ...
    def get_tickers(self) -> list[str]: ...
```

From backend/app/market/seed_prices.py (single source of truth for the startup ticker set —
per Claude's Discretion in CONTEXT.md):
```python
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00, "GOOGL": 175.00, "MSFT": 420.00, "AMZN": 185.00,
    "TSLA": 250.00, "NVDA": 800.00, "META": 500.00, "JPM": 195.00,
    "V": 280.00, "NFLX": 600.00,
}
```
SEED_PRICES is NOT re-exported from `app.market.__init__` — deep import is correct:
`from .market.seed_prices import SEED_PRICES`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Add python-dotenv runtime dependency via uv</name>
  <read_first>
    - backend/pyproject.toml (current dependencies list, lines 7-13)
    - backend/CLAUDE.md (project rule: install deps with uv, never pip)
    - ./CLAUDE.md (project rule: `uv add xxx`, never `pip install xxx`)
  </read_first>
  <files>backend/pyproject.toml, backend/uv.lock</files>
  <action>
    From the `backend/` directory run exactly:

        uv add python-dotenv

    Do NOT edit `pyproject.toml` by hand. Do NOT use `pip`. Do NOT pin a version yourself —
    let `uv add` resolve to the latest compatible release for `requires-python = ">=3.12"`.
    `uv add` will both append `"python-dotenv>=X.Y.Z"` to `[project].dependencies` AND
    refresh `backend/uv.lock`. Commit both files together.

    Why python-dotenv (and not pydantic-settings or hand-rolled): per
    `.planning/phases/01-app-shell-config/01-PATTERNS.md` "Claude's Discretion" section, the
    project does not yet depend on a settings library and the conventional minimum is
    `load_dotenv()` called once at app construction before lifespan runs. python-dotenv is
    the smallest answer to APP-03 ("`.env` loading for OPENROUTER_API_KEY, MASSIVE_API_KEY,
    LLM_MOCK") that satisfies the hard constraint "missing values must not crash startup"
    (`load_dotenv()` is silent when the file is absent).
  </action>
  <verify>
    <automated>cd backend &amp;&amp; grep -E '^\s*"python-dotenv' pyproject.toml &amp;&amp; uv sync --extra dev &amp;&amp; uv run python -c "import dotenv; print(dotenv.__version__)"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -E '^\s*"python-dotenv' backend/pyproject.toml` matches exactly one line inside the
      `[project].dependencies` array.
    - `cd backend &amp;&amp; uv sync --extra dev` exits 0.
    - `cd backend &amp;&amp; uv run python -c "from dotenv import load_dotenv; load_dotenv()"` exits 0.
    - `backend/uv.lock` contains a `[[package]]` entry whose `name = "python-dotenv"`.
    - No `pip install` invocation appears in shell history for this task.
  </acceptance_criteria>
  <done>python-dotenv is a declared, locked, importable runtime dependency.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Create backend/app/lifespan.py with PriceCache + market source + SSE router wiring</name>
  <read_first>
    - backend/app/market/__init__.py (public re-exports — use these import paths)
    - backend/app/market/factory.py (env-driven source selection — do not duplicate)
    - backend/app/market/stream.py (create_stream_router signature, prefix "/api/stream")
    - backend/app/market/seed_prices.py (SEED_PRICES — startup ticker set)
    - backend/app/market/simulator.py:219-240 (start/stop lifecycle the lifespan delegates to)
    - backend/market_data_demo.py (only existing "build cache, start source, stop source"
      sequencing analog)
    - .planning/phases/01-app-shell-config/01-PATTERNS.md (the lifespan body to mirror)
    - .planning/phases/01-app-shell-config/01-CONTEXT.md (D-01, D-02, D-04 — non-negotiable)
    - .planning/codebase/CONVENTIONS.md (`%`-style logging, no f-strings, no emojis,
      `from __future__ import annotations`)
  </read_first>
  <files>backend/app/lifespan.py</files>
  <action>
    Create `backend/app/lifespan.py` exactly as below (per D-01, D-02, D-04 in CONTEXT.md).
    No defensive try/except around `source.start(...)` — startup must fail loud per project
    rule "no defensive programming". The only logged-and-swallowed condition is the missing
    OPENROUTER_API_KEY warning (per CONTEXT.md "Missing-env policy" — Phase 5 will fail loud
    when `/api/chat` is hit). Do NOT load `.env` here — that happens in main.py (Plan 02)
    BEFORE the app/lifespan is constructed.

    ```python
    """FastAPI lifespan: PriceCache + market data source startup/shutdown."""

    from __future__ import annotations

    import logging
    import os
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from .market import PriceCache, create_market_data_source, create_stream_router
    from .market.seed_prices import SEED_PRICES

    logger = logging.getLogger(__name__)


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Build the shared PriceCache, start the market data source, mount SSE router.

        Decisions implemented:
          D-02: PriceCache and source are constructed here (no module globals) and
                attached to app.state so handlers can reach them via request.app.state.
          D-04: The SSE router (create_stream_router(cache)) is included during startup
                so /api/stream/prices is mounted for the lifetime of the app.

        Startup ticker set is list(SEED_PRICES.keys()) — single source of truth flagged
        in .planning/codebase/CONCERNS.md (Phase 2's DB-backed watchlist will swap in
        without code churn).
        """
        if not os.environ.get("OPENROUTER_API_KEY"):
            logger.warning(
                "OPENROUTER_API_KEY not set; chat endpoint will fail in Phase 5"
            )

        cache = PriceCache()
        source = create_market_data_source(cache)

        tickers = list(SEED_PRICES.keys())
        await source.start(tickers)

        app.state.price_cache = cache
        app.state.market_source = source
        app.include_router(create_stream_router(cache))

        logger.info(
            "App started: %d tickers, source=%s",
            len(tickers),
            type(source).__name__,
        )
        try:
            yield
        finally:
            await source.stop()
            logger.info("App stopped")
    ```

    Notes that justify each line — do NOT add as inline comments, just satisfy them:
      - `from __future__ import annotations` is mandatory per CONVENTIONS.md.
      - Public-API import `from .market import ...` (per backend/CLAUDE.md "Market Data API");
        deep import `from .market.seed_prices import SEED_PRICES` is the documented exception
        (SEED_PRICES is not re-exported from app.market.__init__).
      - `%`-style logging only — never f-strings (CONVENTIONS.md "Anti-patterns").
      - No emojis anywhere.
      - No `try/except` around `source.start(...)` — must fail loud.
  </action>
  <verify>
    <automated>cd backend &amp;&amp; uv run --extra dev ruff check app/lifespan.py &amp;&amp; uv run python -c "from app.lifespan import lifespan; from contextlib import _AsyncGeneratorContextManager; print(lifespan.__name__)"</automated>
  </verify>
  <acceptance_criteria>
    - `backend/app/lifespan.py` exists and `wc -l backend/app/lifespan.py` reports >= 25 lines.
    - `grep -F 'from __future__ import annotations' backend/app/lifespan.py` matches.
    - `grep -F 'from contextlib import asynccontextmanager' backend/app/lifespan.py` matches.
    - `grep -F 'from .market import PriceCache, create_market_data_source, create_stream_router' backend/app/lifespan.py` matches.
    - `grep -F 'from .market.seed_prices import SEED_PRICES' backend/app/lifespan.py` matches.
    - `grep -F '@asynccontextmanager' backend/app/lifespan.py` matches.
    - `grep -E 'async def lifespan\(app: FastAPI\)' backend/app/lifespan.py` matches.
    - `grep -F 'app.state.price_cache = cache' backend/app/lifespan.py` matches.
    - `grep -F 'app.state.market_source = source' backend/app/lifespan.py` matches.
    - `grep -F 'app.include_router(create_stream_router(cache))' backend/app/lifespan.py` matches.
    - `grep -F 'await source.start(tickers)' backend/app/lifespan.py` matches.
    - `grep -F 'await source.stop()' backend/app/lifespan.py` matches.
    - `grep -nE 'f"|f\x27' backend/app/lifespan.py` returns NOTHING in any `logger.` line
      (no f-strings in logging — verify by hand if any f-string exists outside log calls).
    - `grep -nE 'try:\s*$' backend/app/lifespan.py` shows exactly one `try:` (the `try/finally`
      around `yield`).
    - `cd backend &amp;&amp; uv run --extra dev ruff check app/lifespan.py` exits 0.
    - `cd backend &amp;&amp; uv run python -c "from app.lifespan import lifespan; print(lifespan)"` exits 0.
  </acceptance_criteria>
  <done>
    Importable async context manager that constructs PriceCache, selects+starts the
    market data source from env, mounts the SSE router, attaches both to app.state, and
    cleanly stops the source on exit. Plan 02 (main.py) can `from .lifespan import lifespan`.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| environment -> process | `MASSIVE_API_KEY`, `OPENROUTER_API_KEY`, `LLM_MOCK` cross from the host environment / `.env` file into the Python process. |
| factory -> outbound network | When `MASSIVE_API_KEY` is non-empty, `MassiveDataSource` will make outbound calls to Polygon — but only after Plan 02 wires `.env` loading. In Plan 01 the source is selected and started; the network boundary is delegated to the existing, tested market subsystem. |

## STRIDE Threat Register (ASVS L1, block on `high`)

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01-01 | Information Disclosure | `logger.info("App started: ...source=%s", ..., type(source).__name__)` | accept | Logs only the class name (`SimulatorDataSource` / `MassiveDataSource`), never the API key. The factory itself never logs the key value (verified: `factory.py:24-31`). No PII; no key material. |
| T-01-02 | Denial of Service | `await source.start(tickers)` blocks startup on the simulator's seed-price loop or on Massive's first poll | accept | Existing market subsystem is tested for both paths (73 passing tests). Failure to start raises and crashes the process — correct per "no defensive programming"; uvicorn surfaces the traceback. No public input here. |
| T-01-03 | Tampering | An attacker who can write to `.env` could swap `MASSIVE_API_KEY` to a malicious value | accept | Out of scope for Phase 1 (file-system trust boundary belongs to OPS-04 / Phase 9 deployment). `.env` is gitignored; local-dev threat model. |
| T-01-04 | Elevation of Privilege | `app.state` mutation by lifespan exposes `price_cache` and `market_source` to all handlers | accept | Designed behavior — both are read-only consumers. SSE handler (`create_stream_router`) already takes `price_cache` via closure; no new privilege surface introduced by attaching to `app.state`. |
| T-01-05 | Repudiation | No structured audit log of startup events | accept | `logger.info` records lifespan start/stop with ticker count and source class name — sufficient for a single-user local demo. ASVS L1 does not require structured audit. |

No `high`-severity threats. The phase introduces no new attack surface; it only wires
existing, tested components into a FastAPI lifecycle.
</threat_model>

<verification>
Run from `backend/`:
- `uv sync --extra dev` (resolves python-dotenv into the lock and the venv)
- `uv run --extra dev ruff check app/lifespan.py` (lint clean)
- `uv run python -c "from app.lifespan import lifespan; print(lifespan.__name__)"` (importable)
- Manually inspect that no `try/except` wraps `source.start(...)` (only the `try/finally`
  around `yield` is allowed).
</verification>

<success_criteria>
- `python-dotenv` is in `backend/pyproject.toml` `[project].dependencies` and resolved in
  `backend/uv.lock`.
- `backend/app/lifespan.py` exports an `@asynccontextmanager async def lifespan(app: FastAPI)`.
- The lifespan constructs `PriceCache` ONCE per app, calls `create_market_data_source(cache)`,
  awaits `source.start(list(SEED_PRICES.keys()))`, attaches both to `app.state`, includes
  `create_stream_router(cache)` BEFORE `yield`, and awaits `source.stop()` on shutdown.
- All imports use the public `app.market` surface (one documented exception: `SEED_PRICES`).
- No f-strings in logging calls. No emojis. No defensive `try/except` around startup.
- ruff exits 0 on the new module.
</success_criteria>

<output>
After completion, create `.planning/phases/01-app-shell-config/01-01-SUMMARY.md`.
</output>
