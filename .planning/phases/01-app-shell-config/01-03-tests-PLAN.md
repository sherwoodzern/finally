---
phase: 01-app-shell-config
plan: 03
type: execute
wave: 3
depends_on: ["01-app-shell-config-01", "01-app-shell-config-02"]
files_modified:
  - backend/pyproject.toml
  - backend/tests/test_main.py
  - backend/tests/test_lifespan.py
autonomous: true
requirements: [APP-01, APP-03, APP-04]
tags: [pytest, fastapi, sse, asgi, end-to-end]

must_haves:
  truths:
    - "`httpx` and `asgi-lifespan` are dev dependencies declared in backend/pyproject.toml [project.optional-dependencies].dev."
    - "`uv run --extra dev pytest backend/tests/test_main.py -v` exits 0."
    - "`uv run --extra dev pytest backend/tests/test_lifespan.py -v` exits 0."
    - "test_main.py asserts GET /api/health returns 200 with body {\"status\": \"ok\"} via httpx.AsyncClient + ASGITransport."
    - "test_main.py asserts a real EventSource-equivalent (httpx streaming GET on /api/stream/prices) receives at least one `data: ` frame within 5 seconds, with the app entered via LifespanManager so the SSE router is mounted."
    - "test_lifespan.py asserts the lifespan attaches `app.state.price_cache` (a PriceCache) and `app.state.market_source` (a MarketDataSource started with the SEED_PRICES tickers) on entry, and stops the source on exit."
    - "When MASSIVE_API_KEY is unset, test_lifespan asserts the started source is a SimulatorDataSource (delegated to factory)."
    - "Missing OPENROUTER_API_KEY does not raise — the lifespan logs a warning and proceeds (caplog assertion)."
  artifacts:
    - path: "backend/tests/test_main.py"
      provides: "HTTP-level tests for /api/health and end-to-end SSE smoke"
      contains: "TestHealth"
      min_lines: 40
    - path: "backend/tests/test_lifespan.py"
      provides: "Async lifecycle tests for the FastAPI lifespan"
      contains: "TestLifespan"
      min_lines: 40
    - path: "backend/pyproject.toml"
      provides: "httpx and asgi-lifespan dev dependencies"
      contains: "asgi-lifespan"
  key_links:
    - from: "backend/tests/test_main.py"
      to: "backend/app/main.py"
      via: "from app.main import app"
      pattern: "from app\\.main import app"
    - from: "backend/tests/test_lifespan.py"
      to: "backend/app/lifespan.py"
      via: "from app.lifespan import lifespan + LifespanManager(app)"
      pattern: "LifespanManager\\(app\\)"
    - from: "backend/tests/test_main.py SSE test"
      to: "/api/stream/prices (mounted by lifespan, see Plan 01)"
      via: "client.stream('GET', '/api/stream/prices') after LifespanManager enter"
      pattern: "/api/stream/prices"
---

<objective>
Add `httpx` and `asgi-lifespan` as dev dependencies and create two pytest modules under
`backend/tests/` that prove all four Phase 1 success criteria from end to end:

  1. `/api/health` returns `{"status": "ok"}` (APP-01).
  2. The lifespan constructs ONE PriceCache, attaches it + the started market source to
     `app.state`, and includes `create_stream_router(cache)` (APP-01, APP-04).
  3. A real-EventSource-equivalent client opening `/api/stream/prices` receives at least
     one `data:` frame and continues to receive ticks as the cache version advances (APP-04).
  4. Missing `OPENROUTER_API_KEY` does not crash startup (APP-03 missing-env policy); when
     `MASSIVE_API_KEY` is absent, the simulator is selected (APP-03 source selection).

Purpose: Closes the Phase 1 verification loop without requiring a manual browser. Per
CONTEXT.md "Claude's Discretion (SSE end-to-end verification)", this satisfies APP-04
without standing up Playwright (which is Phase 10).
Output: Two test modules + two new dev deps in `pyproject.toml`/`uv.lock`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@backend/CLAUDE.md
@.planning/phases/01-app-shell-config/01-CONTEXT.md
@.planning/phases/01-app-shell-config/01-PATTERNS.md
@.planning/codebase/CONVENTIONS.md
@backend/app/main.py
@backend/app/lifespan.py
@backend/app/market/__init__.py
@backend/app/market/simulator.py
@backend/app/market/seed_prices.py
@backend/tests/conftest.py
@backend/tests/market/test_simulator_source.py
@backend/tests/market/test_factory.py
@backend/pyproject.toml

<interfaces>
<!-- Test client contracts (latest APIs as of 2026). -->

httpx ASGI transport (the recommended FastAPI test client as of FastAPI ≥ 0.115):
```python
from httpx import ASGITransport, AsyncClient

async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    resp = await client.get("/api/health")  # 200, {"status": "ok"}
    async with client.stream("GET", "/api/stream/prices", timeout=5.0) as resp:
        async for line in resp.aiter_lines():
            ...
```

asgi-lifespan — runs the FastAPI lifespan around the test (so the SSE router is mounted
and the market data source is actually running):
```python
from asgi_lifespan import LifespanManager

async with LifespanManager(app):
    # lifespan startup has run; app.state.price_cache, market_source set;
    # SSE router included; source background task is producing ticks
    ...
# lifespan shutdown has run on exit
```

pytest-asyncio convention (already configured in backend/pyproject.toml line 35:
`asyncio_mode = "auto"`); class-grouped tests with explicit `@pytest.mark.asyncio` at
the class level (matches every test in `backend/tests/market/`).

Existing analog for env patching (from backend/tests/market/test_factory.py:19-46):
```python
import os
from unittest.mock import patch

with patch.dict(os.environ, {}, clear=True):
    source = create_market_data_source(cache)
    assert isinstance(source, SimulatorDataSource)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Add httpx and asgi-lifespan as dev dependencies via uv</name>
  <read_first>
    - backend/pyproject.toml (current `[project.optional-dependencies].dev` block, lines 15-21)
    - backend/CLAUDE.md (project rule: install with uv only)
    - .planning/phases/01-app-shell-config/01-PATTERNS.md ("New deps the planner may need")
  </read_first>
  <files>backend/pyproject.toml, backend/uv.lock</files>
  <action>
    From `backend/`, run exactly:

        uv add --dev httpx asgi-lifespan

    Both go into the `dev` optional-dependencies group so the production runtime stays lean.
    Do NOT use pip. Do NOT pin versions yourself — let uv resolve to the latest compatible
    release. Both are needed for the SSE end-to-end test:

      - `httpx` provides `ASGITransport` and `AsyncClient.stream(...)` — the FastAPI-native
        async test client, supersedes `requests`. (httpx may already be a transitive dep of
        starlette via `TestClient`; declaring it explicitly removes ambiguity.)
      - `asgi-lifespan` provides `LifespanManager(app)`, which is what makes the lifespan
        actually run during the test — without it, the SSE router never gets included and
        `/api/stream/prices` returns 404 in tests.
  </action>
  <verify>
    <automated>cd backend &amp;&amp; grep -E '"httpx' pyproject.toml &amp;&amp; grep -E '"asgi-lifespan' pyproject.toml &amp;&amp; uv sync --extra dev &amp;&amp; uv run --extra dev python -c "import httpx, asgi_lifespan; print(httpx.__version__, asgi_lifespan.__version__)"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -E '"httpx' backend/pyproject.toml` matches a line inside the `dev` array.
    - `grep -E '"asgi-lifespan' backend/pyproject.toml` matches a line inside the `dev` array.
    - `cd backend &amp;&amp; uv sync --extra dev` exits 0.
    - `cd backend &amp;&amp; uv run --extra dev python -c "from httpx import ASGITransport, AsyncClient; from asgi_lifespan import LifespanManager"` exits 0.
    - `backend/uv.lock` contains `[[package]]` entries with `name = "httpx"` and `name = "asgi-lifespan"`.
  </acceptance_criteria>
  <done>
    httpx and asgi-lifespan are declared, locked, and importable as dev-only dependencies.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Create backend/tests/test_lifespan.py (async lifecycle assertions)</name>
  <read_first>
    - backend/app/lifespan.py (the SUT — produced by Plan 01)
    - backend/app/market/__init__.py (PriceCache, MarketDataSource public types for asserts)
    - backend/app/market/seed_prices.py (SEED_PRICES — expected ticker set)
    - backend/app/market/simulator.py (SimulatorDataSource — expected default source class)
    - backend/tests/market/test_simulator_source.py (exact analog for "build, await start,
      assert state, await stop" — match its class structure)
    - backend/tests/market/test_factory.py (env patching pattern: `patch.dict(os.environ,
      {...}, clear=True)`)
    - backend/tests/conftest.py (pre-existing test config — do not modify)
    - backend/pyproject.toml (asyncio_mode="auto" + asyncio_default_fixture_loop_scope=
      "function" already configured)
    - .planning/phases/01-app-shell-config/01-PATTERNS.md ("backend/tests/test_lifespan.py")
    - .planning/codebase/CONVENTIONS.md (testing style: class-grouped, one behavior per test)
  </read_first>
  <files>backend/tests/test_lifespan.py</files>
  <action>
    Create `backend/tests/test_lifespan.py` with the exact body below. Uses the
    asgi-lifespan `LifespanManager` to actually run the lifespan around each test (the
    natural async equivalent of FastAPI's `TestClient` lifecycle).

    ```python
    """Async lifecycle tests for the FastAPI app shell lifespan."""

    import logging
    import os
    from unittest.mock import patch

    import pytest
    from asgi_lifespan import LifespanManager
    from fastapi import FastAPI

    from app.lifespan import lifespan
    from app.market import MarketDataSource, PriceCache
    from app.market.seed_prices import SEED_PRICES
    from app.market.simulator import SimulatorDataSource


    def _build_app() -> FastAPI:
        """Build a fresh FastAPI app bound to the production lifespan.

        A fresh app per test ensures no state bleeds between cases (PriceCache,
        market source, included routers all live on app.state / app.router).
        """
        return FastAPI(lifespan=lifespan)


    @pytest.mark.asyncio
    class TestLifespan:
        """The lifespan wires PriceCache + market source + SSE router on entry,
        and cleanly stops the source on exit."""

        async def test_attaches_price_cache_to_app_state(self):
            """Entering the lifespan attaches a PriceCache to app.state.price_cache."""
            app = _build_app()
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    assert isinstance(app.state.price_cache, PriceCache)

        async def test_attaches_market_source_to_app_state(self):
            """Entering the lifespan attaches a started MarketDataSource to app.state."""
            app = _build_app()
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    assert isinstance(app.state.market_source, MarketDataSource)
                    assert set(app.state.market_source.get_tickers()) == set(SEED_PRICES)

        async def test_uses_simulator_when_massive_api_key_absent(self):
            """With no MASSIVE_API_KEY, the factory selects SimulatorDataSource."""
            app = _build_app()
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    assert isinstance(app.state.market_source, SimulatorDataSource)

        async def test_seeds_cache_immediately_on_startup(self):
            """All SEED_PRICES tickers are present in the cache before any test code runs.

            This is the contract that makes /api/stream/prices have data on first connect
            (mirrors backend/tests/market/test_simulator_source.py::test_start_populates_cache).
            """
            app = _build_app()
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    cache: PriceCache = app.state.price_cache
                    for ticker in SEED_PRICES:
                        assert cache.get(ticker) is not None, ticker

        async def test_includes_sse_router_during_startup(self):
            """app.include_router(create_stream_router(cache)) ran in lifespan startup,
            so /api/stream/prices is registered on the app while the lifespan is active."""
            app = _build_app()
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    paths = {getattr(r, "path", None) for r in app.router.routes}
                    assert "/api/stream/prices" in paths, paths

        async def test_missing_openrouter_key_logs_warning_and_proceeds(self, caplog):
            """Missing OPENROUTER_API_KEY does not raise — only a single warning is logged.

            Implements CONTEXT.md missing-env policy: Phase 5 will fail loud when chat is
            hit; Phase 1 startup must not block on a key it does not yet use.
            """
            caplog.set_level(logging.WARNING, logger="app.lifespan")
            app = _build_app()
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    pass
            messages = [rec.message for rec in caplog.records]
            assert any("OPENROUTER_API_KEY" in m for m in messages), messages

        async def test_stops_source_on_shutdown(self):
            """Exiting the lifespan awaits source.stop() — background task is no longer running."""
            app = _build_app()
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    source = app.state.market_source
                # After exit, the simulator's _task is None or done (mirrors
                # SimulatorDataSource.stop semantics in backend/app/market/simulator.py:231-240).
                task = getattr(source, "_task", None)
                assert task is None or task.done()
    ```

    Style notes (CONVENTIONS.md):
      - Class-grouped, one behavior per test, docstring on every method.
      - `@pytest.mark.asyncio` at the class level (matches every `tests/market/*.py`).
      - `patch.dict(os.environ, {}, clear=True)` exact pattern from `test_factory.py`.
      - No emojis. No f-strings in any logger call (none used here).
      - Direct private-attribute access (`source._task`) is acceptable — see
        `tests/market/test_simulator_source.py:108-109` for the precedent.
  </action>
  <verify>
    <automated>cd backend &amp;&amp; uv run --extra dev ruff check tests/test_lifespan.py &amp;&amp; uv run --extra dev pytest tests/test_lifespan.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `backend/tests/test_lifespan.py` exists and `wc -l backend/tests/test_lifespan.py` reports >= 50 lines.
    - `grep -F 'from asgi_lifespan import LifespanManager' backend/tests/test_lifespan.py` matches.
    - `grep -F 'from app.lifespan import lifespan' backend/tests/test_lifespan.py` matches.
    - `grep -F 'from app.market import MarketDataSource, PriceCache' backend/tests/test_lifespan.py` matches.
    - `grep -F 'from app.market.seed_prices import SEED_PRICES' backend/tests/test_lifespan.py` matches.
    - `grep -E '@pytest\.mark\.asyncio' backend/tests/test_lifespan.py` matches at least once.
    - `grep -E 'class TestLifespan' backend/tests/test_lifespan.py` matches.
    - `grep -F 'patch.dict(os.environ, {}, clear=True)' backend/tests/test_lifespan.py` matches.
    - `grep -F '/api/stream/prices' backend/tests/test_lifespan.py` matches (the SSE-router-
      mounted assertion).
    - `cd backend &amp;&amp; uv run --extra dev ruff check tests/test_lifespan.py` exits 0.
    - `cd backend &amp;&amp; uv run --extra dev pytest tests/test_lifespan.py -v` exits 0 with
      >= 7 tests collected and passed.
  </acceptance_criteria>
  <done>
    Lifespan unit-level behavior is fully covered: cache attached, source attached + started
    with SEED_PRICES, simulator selected on absent MASSIVE_API_KEY, SSE route registered,
    missing OPENROUTER_API_KEY tolerated, source stopped on exit.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Create backend/tests/test_main.py (HTTP /api/health + end-to-end SSE smoke)</name>
  <read_first>
    - backend/app/main.py (the SUT — produced by Plan 02)
    - backend/app/lifespan.py (the lifespan that mounts the SSE router)
    - backend/app/market/cache.py (PriceCache.version semantics — used by the cache-advance
      assertion)
    - backend/tests/market/test_simulator_source.py:27-39 (the "version increments over time"
      pattern this test mirrors for SSE)
    - .planning/phases/01-app-shell-config/01-PATTERNS.md ("backend/tests/test_main.py")
    - .planning/codebase/CONVENTIONS.md (test style)
  </read_first>
  <files>backend/tests/test_main.py</files>
  <action>
    Create `backend/tests/test_main.py` with the exact body below. The SSE test is the
    Phase 1 closing artifact — it proves APP-04 ("real EventSource-equivalent receives
    ticks") without requiring a browser.

    ```python
    """HTTP-level tests for the FastAPI app shell — /api/health and end-to-end SSE."""

    import asyncio
    import os
    from unittest.mock import patch

    import pytest
    from asgi_lifespan import LifespanManager
    from httpx import ASGITransport, AsyncClient

    from app.main import app


    @pytest.mark.asyncio
    class TestHealth:
        """GET /api/health — the one inline route in main.py (D-04)."""

        async def test_health_returns_ok(self):
            """Returns HTTP 200 with body {'status': 'ok'}."""
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        resp = await client.get("/api/health")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}


    @pytest.mark.asyncio
    class TestSSEStream:
        """End-to-end proof of APP-04: a real EventSource-equivalent client receives
        ticks from the lifespan-mounted /api/stream/prices."""

        async def test_sse_emits_at_least_one_data_frame(self):
            """A streaming GET on /api/stream/prices yields >= 1 'data:' frame within 5s.

            This proves the full Phase 1 wiring end-to-end: lifespan started, PriceCache
            constructed, simulator producing ticks, SSE router mounted, /api/stream/prices
            reachable through ASGI, and the existing version-gated emit loop pushing data.
            """
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        async with client.stream(
                            "GET", "/api/stream/prices", timeout=5.0
                        ) as resp:
                            assert resp.status_code == 200
                            saw_data = False
                            async for line in resp.aiter_lines():
                                if line.startswith("data:"):
                                    saw_data = True
                                    break
            assert saw_data, "no 'data:' frame received within 5s"

        async def test_sse_continues_emitting_as_cache_version_advances(self):
            """The stream keeps emitting as the simulator advances the cache version.

            Mirrors backend/tests/market/test_simulator_source.py::test_prices_update_over_time
            but at the HTTP boundary — closes APP-04 with continuity, not just first-frame.
            """
            with patch.dict(os.environ, {}, clear=True):
                async with LifespanManager(app):
                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        async with client.stream(
                            "GET", "/api/stream/prices", timeout=5.0
                        ) as resp:
                            assert resp.status_code == 200
                            data_frames = 0
                            async for line in resp.aiter_lines():
                                if line.startswith("data:"):
                                    data_frames += 1
                                    if data_frames >= 2:
                                        break
            assert data_frames >= 2, f"expected >= 2 data frames, got {data_frames}"
    ```

    Style / contract notes:
      - Each test uses its own `LifespanManager(app)` block. Re-entering the lifespan rebuilds
        the cache and source per test (clean isolation, matches the test_factory env-clearing
        pattern).
      - The `data:` frame check is intentionally loose ("starts with `data:`") because
        `stream._generate_events` emits both `retry: 1000\n\n` (skipped) and
        `data: {json}\n\n` payloads.
      - 5 s timeout is generous; the simulator default `update_interval=0.5` means a frame
        should appear in ~500 ms.
      - No `if __name__ == "__main__":` blocks. No emojis. No f-strings in logger calls
        (none used here). ruff-clean.
  </action>
  <verify>
    <automated>cd backend &amp;&amp; uv run --extra dev ruff check tests/test_main.py &amp;&amp; uv run --extra dev pytest tests/test_main.py -v --timeout=20 || uv run --extra dev pytest tests/test_main.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `backend/tests/test_main.py` exists and `wc -l backend/tests/test_main.py` reports >= 40 lines.
    - `grep -F 'from app.main import app' backend/tests/test_main.py` matches.
    - `grep -F 'from asgi_lifespan import LifespanManager' backend/tests/test_main.py` matches.
    - `grep -F 'from httpx import ASGITransport, AsyncClient' backend/tests/test_main.py` matches.
    - `grep -E 'class TestHealth' backend/tests/test_main.py` matches.
    - `grep -E 'class TestSSEStream' backend/tests/test_main.py` matches.
    - `grep -F '/api/health' backend/tests/test_main.py` matches.
    - `grep -F '/api/stream/prices' backend/tests/test_main.py` matches.
    - `grep -E 'resp\.json\(\)\s*==\s*\{"status":\s*"ok"\}' backend/tests/test_main.py` matches.
    - `grep -F "client.stream(" backend/tests/test_main.py` matches.
    - `cd backend &amp;&amp; uv run --extra dev ruff check tests/test_main.py` exits 0.
    - `cd backend &amp;&amp; uv run --extra dev pytest tests/test_main.py -v` exits 0 with
      3 tests collected (1 health + 2 SSE) and all passing.
    - `cd backend &amp;&amp; uv run --extra dev pytest -v` (full suite, including the existing
      73 market tests) exits 0.
  </acceptance_criteria>
  <done>
    APP-04 is verified end-to-end without a browser: a streaming HTTP client opening
    /api/stream/prices on the lifespan-mounted app receives multiple `data:` frames as the
    cache version advances. APP-01 health endpoint passes. Full backend test suite is green.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test process -> in-process ASGI app | `httpx.ASGITransport` calls the app function directly — no network. |
| test env -> patched os.environ | `patch.dict(os.environ, {}, clear=True)` strips real keys for each test. |

## STRIDE Threat Register (ASVS L1, block on `high`)

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01-11 | Information Disclosure | Tests run with the developer's real `OPENROUTER_API_KEY` / `MASSIVE_API_KEY` in env | mitigate | Every test wraps the lifespan in `patch.dict(os.environ, {}, clear=True)` so the dev's real keys are never touched, and the simulator is always selected — so no outbound network call to Polygon happens during test runs (matches the env-isolation pattern in `tests/market/test_factory.py`). |
| T-01-12 | Tampering | A flaky SSE test could mask a real regression | mitigate | The 5 s timeout is much larger than the 0.5 s simulator interval; `aiter_lines()` is bounded by the timeout; `data_frames >= 2` confirms the version-counter loop is alive, not just the initial seed emission. |
| T-01-13 | Denial of Service | Hung SSE generator could leak background tasks across tests | mitigate | `LifespanManager.__aexit__` awaits `source.stop()`; `client.stream` block is `async with`, so the connection is closed before the lifespan teardown runs. Each test gets a fresh PriceCache + source instance. |
| T-01-14 | Elevation of Privilege | Tests reach into private attributes (`source._task`) | accept | Documented codebase convention (see `tests/market/test_simulator_source.py:108-109`). Sharpens the assertion without weakening the public contract. |

No `high`-severity threats. The test surface is in-process, env-isolated, and bounded by
timeouts.
</threat_model>

<verification>
Run from `backend/`:
- `uv sync --extra dev` (resolves httpx + asgi-lifespan into the lock and venv)
- `uv run --extra dev ruff check tests/test_lifespan.py tests/test_main.py` (lint clean)
- `uv run --extra dev pytest tests/test_lifespan.py -v` (>= 7 tests, all green)
- `uv run --extra dev pytest tests/test_main.py -v` (3 tests, all green)
- `uv run --extra dev pytest -v` (full suite, including the existing 73 market tests, all green)

Optional manual smoke (not gated):
- `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &amp;`
- `curl -s http://127.0.0.1:8000/api/health` → `{"status":"ok"}`
- `curl -N http://127.0.0.1:8000/api/stream/prices | head -n 5` → at least one `data: {...}` frame.
</verification>

<success_criteria>
- All four Phase 1 success criteria are now automatically verified:
  (1) `/api/health` returns `{"status": "ok"}` — covered by TestHealth.
  (2) Lifespan constructs ONE PriceCache, selects+starts a market source from
      `MASSIVE_API_KEY`, and includes `create_stream_router(cache)` — covered by TestLifespan.
  (3) An EventSource-equivalent client receives ticks within a few hundred ms and continues
      to receive them as the cache version advances — covered by TestSSEStream.
  (4) Missing env vars do not crash startup; simulator is selected when MASSIVE_API_KEY is
      absent — covered by TestLifespan.
- `httpx` and `asgi-lifespan` are dev-only dependencies (no production weight added).
- The existing 73 market tests still pass; the new tests add ~10 cases without modifying any
  existing test file.
</success_criteria>

<output>
After completion, create `.planning/phases/01-app-shell-config/01-03-SUMMARY.md`.
</output>
