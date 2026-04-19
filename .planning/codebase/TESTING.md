# Testing

**Analysis Date:** 2026-04-19

## Status Snapshot

- **Backend unit tests: present and strong.** `backend/tests/market/` has 6 modules, **73 tests, 84% overall coverage** for the implemented market-data subsystem (per `planning/MARKET_DATA_SUMMARY.md`).
- **Frontend tests: do not exist** (no `frontend/` yet).
- **E2E tests: do not exist** (no `test/`, no `docker-compose.test.yml`, no Playwright install).

Everything checked in today validates the one subsystem that exists.

## Framework

**Python (implemented):**
- `pytest>=8.3.0`
- `pytest-asyncio>=0.24.0` with `asyncio_mode = "auto"` (in `backend/pyproject.toml:35`) — no need to decorate every async test
- `pytest-cov>=5.0.0`
- `asyncio_default_fixture_loop_scope = "function"` to avoid loop leakage between async tests

**Planned (not yet installed):**
- React Testing Library / Vitest for frontend components
- Playwright for cross-browser E2E, with `LLM_MOCK=true` for determinism (see `planning/PLAN.md` §12)

## Layout

```
backend/
├── pyproject.toml            # pytest / coverage / ruff config lives here
└── tests/
    ├── __init__.py
    ├── conftest.py           # Event-loop policy fixture
    └── market/
        ├── __init__.py
        ├── test_models.py           # 11 tests — PriceUpdate derived props, JSON shape
        ├── test_cache.py            # 13 tests — update/get/remove, version counter, thread-safety
        ├── test_simulator.py        # 17 tests — GBM math, Cholesky, add/remove ticker
        ├── test_simulator_source.py # 10 tests — integration: start/stop, cache seeding
        ├── test_factory.py          # 7 tests  — env-var selection
        └── test_massive.py          # 13 tests — REST poller with mocked SDK
```

Tests mirror the source layout: one test module per production module.

## Configuration (in `backend/pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

[tool.coverage.run]
source = ["app"]
omit = ["tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Running Tests

From `backend/`:

```bash
uv sync --extra dev                         # install test/lint tooling
uv run --extra dev pytest -v                # all tests, verbose
uv run --extra dev pytest --cov=app         # with coverage report
uv run --extra dev pytest tests/market/test_cache.py -v  # one module
uv run --extra dev ruff check app/ tests/   # lint
```

(The `--extra dev` flag is required when dev extras aren't already installed into the active env; `backend/CLAUDE.md` shows both forms.)

## Patterns Observed

### Structure
- Tests are grouped inside `class Test<Thing>` blocks with one behavior per method (see `backend/tests/market/test_cache.py:5-30` and `test_massive.py:21-50`).
- One test = one assertion concept; descriptive names (`test_first_update_is_flat`, `test_poll_updates_cache`, `test_malformed_snapshot_skipped`).
- Async suites mark the whole class: `@pytest.mark.asyncio class TestMassiveDataSource:` (`backend/tests/market/test_massive.py:21-22`).

### Mocking strategy
- External API calls are mocked with `unittest.mock.MagicMock` / `patch.object` — no real network I/O in tests.
- Mock factory pattern for repeatable fixtures: `_make_snapshot(ticker, price, timestamp_ms)` in `test_massive.py:11-18`.
- Private attributes of source-under-test are sometimes written directly to bypass lifecycle: `source._tickers = ["AAPL", "GOOGL"]`, `source._client = MagicMock()` (see `test_massive.py:33-34`). Called out as intentional so `_poll_once` can be unit-tested without running `start()`.

### Coverage
- `coverage.run.source = ["app"]`, `omit = ["tests/*"]`
- Reported per-module in `planning/MARKET_DATA_SUMMARY.md`:
  - `models.py`, `cache.py`, `factory.py`: 100%
  - `simulator.py`: 98%
  - `massive_client.py`: 56% (most misses are branches behind the real SDK — methods mocked)
  - Overall: 84%

### Event loop handling
- `backend/tests/conftest.py` provides an `event_loop_policy` fixture returning the default policy so async tests get a clean loop.
- Combined with `asyncio_mode = "auto"`, any `async def test_*` runs without decoration.

### What's *not* tested
- The SSE generator `stream._generate_events` has no direct test (integration-level; would need a FastAPI `TestClient`).
- `massive_client.py` branches involving the real Polygon SDK are behind mocks (expected — covered by dependency's own tests).

## E2E Plan (not yet implemented)

Per `planning/PLAN.md` §12:

- **Infra:** `test/docker-compose.test.yml` spins up the app container + a Playwright container (keeps browser deps out of the production image).
- **Env:** Tests run with `LLM_MOCK=true` for speed and determinism.
- **Key scenarios:**
  - Fresh start: default watchlist, $10k cash, live prices
  - Watchlist add/remove
  - Buy/sell with correct cash + position accounting
  - Portfolio heatmap + P&L chart render with data
  - AI chat (mocked) renders trade execution inline
  - SSE disconnect / reconnect

## Conventions Summary

- **Test names state the behavior.** Not `test_1`, not `test_it_works`.
- **One behavior per test.** Split into a new test rather than piling assertions.
- **Class per subject under test.** `TestPriceCache`, `TestMassiveDataSource`.
- **Mock at the edge.** The Polygon SDK is mocked; nothing internal is mocked.
- **No real network, no real time.** Long intervals (`poll_interval=60.0`) are set so the loop doesn't auto-poll during unit tests.
- **No emojis.** (Global rule.)

---

*Update when a new testing framework is introduced, coverage targets change, or E2E infra lands.*
