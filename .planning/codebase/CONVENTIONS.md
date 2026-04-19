# Coding Conventions

**Analysis Date:** 2026-04-19

Conventions come from two sources: (a) explicit rules in `~/.claude/CLAUDE.md` and the project `CLAUDE.md` / `backend/CLAUDE.md`, (b) patterns visible in the existing `backend/app/market/` code.

## Explicit Rules (from CLAUDE.md files)

**From `~/.claude/CLAUDE.md` (global):**
- Be simple; approach tasks incrementally, small steps, validate each increment.
- Use latest library APIs (current as of today).
- Do not over-engineer. Do not program defensively. Use exception handlers only when needed.
- Identify root cause before fixing issues — "PROVE THE PROBLEM FIRST — don't guess."
- `uv` is the Python package manager: always `uv run xxx` (never `python3 xxx`), always `uv add xxx` (never `pip install xxx`).
- Favor clear, concise docstring comments. Be sparing with comments outside docstrings.
- Favor short modules, short methods and functions. Name things clearly.
- **Never** use emojis in code, print statements, or logging.
- Keep `README.md` concise.

**From project `CLAUDE.md`:**
- All project documentation is in `planning/`.
- `planning/PLAN.md` is the source of truth; consult it only when required.

**From `backend/CLAUDE.md`:**
- Install deps with `uv sync --extra dev`.
- Market-data public API is re-exported from `app.market` — import from there, not deep paths.
- Run tests with `uv run --extra dev pytest -v`, coverage with `--cov=app`, lint with `uv run --extra dev ruff check app/ tests/`.

## Formatting / Lint (from `backend/pyproject.toml`)

- `ruff` with:
  - `line-length = 100`
  - `target-version = "py312"`
  - rules: `E, F, I, N, W` (pycodestyle, pyflakes, import order, PEP 8 naming, warnings)
  - `E501` ignored (line length handled by formatter)

## Patterns Observed in Code

### Module structure
- Every module starts with a one-line module docstring describing its role.
- Every module uses `from __future__ import annotations`.
- Public names are re-exported through package `__init__.py` (see `backend/app/market/__init__.py:11-23` with explicit `__all__`).
- Modules are intentionally small (the largest, `backend/app/market/simulator.py`, is ~270 lines and contains two classes with a clear split: pure-math `GBMSimulator` + lifecycle-shell `SimulatorDataSource`).

### Classes and data
- Immutable data is a `@dataclass(frozen=True, slots=True)` — see `PriceUpdate` at `backend/app/market/models.py:9-49`.
- Derived values expressed as `@property` (e.g., `change`, `change_percent`, `direction`) instead of precomputed fields.
- Serialization via a `to_dict()` method rather than external serializers.
- Abstract contracts use `abc.ABC` + `@abstractmethod` with docstrings describing lifecycle (see `backend/app/market/interface.py`).

### Typing
- Modern PEP 604 / 585 types throughout: `list[str]`, `dict[str, PriceUpdate]`, `float | None`.
- Optional return values typed as `T | None`, never `Optional[T]`.
- Forward references handled via `from __future__ import annotations` rather than string literals.

### Error handling — narrow and intentional
- `MassiveDataSource._poll_once` wraps the API call in `try/except Exception` and logs; the loop retries next interval (`backend/app/market/massive_client.py:94-121`). Rationale in comments: "Don't re-raise — the loop will retry on the next interval."
- Individual snapshot parse errors are caught narrowly with `(AttributeError, TypeError)` and logged as `warning`, so one bad row doesn't abort the whole poll.
- `SimulatorDataSource._run_loop` uses `logger.exception(...)` to capture tracebacks without crashing the background task.
- Everywhere else: no defensive try/except. First-ever cache writes produce `direction == "flat"` naturally; add/remove operations are idempotent no-ops instead of raising.

### Logging
- `logger = logging.getLogger(__name__)` at the top of every non-trivial module.
- Levels used:
  - `info` — lifecycle events (start/stop, add/remove ticker, client connect/disconnect)
  - `debug` — hot-path details (per-tick random events, per-poll counts)
  - `warning` — recoverable anomalies (malformed Massive snapshot)
  - `error` — poll failures
  - `exception` — unexpected in the simulator hot loop
- Uses `%`-style placeholders (`logger.info("Simulator started with %d tickers", n)`), never f-strings — this is the recommended pattern because args are only formatted if the level is enabled.
- No emojis in log messages.

### Async / concurrency
- `asyncio` everywhere for I/O and background loops.
- Long-running work is a single `asyncio.Task` created in `start()` and cancelled in `stop()`.
- Synchronous third-party calls (Polygon SDK) are offloaded with `asyncio.to_thread` (`backend/app/market/massive_client.py:97`).
- `PriceCache` uses `threading.Lock` because writes can come from a worker thread.

### FastAPI idioms
- Routers are built by factory functions that close over dependencies (`create_stream_router(price_cache)`) instead of using global state or DI.
- SSE hand-rolled with `StreamingResponse` + an async generator; explicit headers: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.

### Docstrings
- Modules: one-line summary.
- Classes: docstring explaining purpose + example lifecycle where relevant.
- Methods: docstring stating behavior, not restating signature. Hot paths annotated (e.g., `# This is the hot path — called every 500ms. Keep it fast.` in `GBMSimulator.step`).
- Inline comments sparingly and only when non-obvious (e.g., math derivations, rate-limit rationale).

### Config / constants
- Per-ticker tuning and correlation structure live in `backend/app/market/seed_prices.py` as module-level constants — easy to audit, easy to edit.
- Default tickers (the "10-ticker watchlist") are repeated in two places today: `SEED_PRICES` keys in `seed_prices.py` and the `TICKERS` list in `market_data_demo.py`. PLAN.md also lists them for the DB seed. Watch for drift.

### Testing style (see TESTING.md for full detail)
- Tests are class-grouped (`class TestPriceCache`, `class TestMassiveDataSource`) with one behavior per `test_*` method.
- `@pytest.mark.asyncio` applied at the class level for async suites.
- Private attributes are sometimes set directly in tests to bypass setup (`source._tickers = [...]`, `source._client = MagicMock()`) — acceptable for isolation; noted as a conscious choice.

## Anti-patterns to Avoid

Derived from the rules and the code:

- ❌ Emojis in any output (code, print, logs, commit messages).
- ❌ `print()` for runtime diagnostics — use `logging`.
- ❌ Broad `try/except Exception` that swallows silently. If you catch, log (and say why you caught in a comment).
- ❌ f-strings in logging calls (breaks lazy formatting and flagged by ruff in stricter configs).
- ❌ Deep relative imports (`from app.market.cache import ...`) from inside the package — use `from .cache import ...`.
- ❌ `Optional[X]` — use `X | None`.
- ❌ Adding dependencies with `pip`. Use `uv add`.
- ❌ Jumping to fixes without reproducing and identifying the root cause.

---

*Update if new explicit rules are added, ruff config changes, or a new subsystem establishes a different style.*
