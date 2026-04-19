# Directory Structure

**Analysis Date:** 2026-04-19

## Actual Layout (today)

```
finally/
├── CLAUDE.md                  # Project instructions → inlines planning/PLAN.md
├── LICENSE
├── README.md                  # Short stack + quick-start description
├── .gitignore                 # Standard Python .gitignore (large)
├── .github/                   # (GitHub config — minimal)
├── .idea/                     # JetBrains IDE settings
├── .claude/                   # Claude Code project settings/skills
├── .planning/                 # GSD workspace (this is where maps live)
│   └── codebase/              # ← you are here
├── backend/                   # FastAPI + uv project (only module that exists)
│   ├── CLAUDE.md              # Backend dev guide (uv, market API imports, tests)
│   ├── README.md              # Backend-specific README
│   ├── pyproject.toml         # Python project config, ruff, pytest
│   ├── uv.lock                # Locked dependency graph (~150 KB)
│   ├── market_data_demo.py    # Rich terminal demo — only runnable entrypoint
│   ├── app/
│   │   ├── __init__.py        # One-line package marker; no app wiring here
│   │   └── market/            # Market-data subsystem (the whole implementation)
│   │       ├── __init__.py    # Public re-exports
│   │       ├── models.py      # PriceUpdate frozen dataclass
│   │       ├── cache.py       # PriceCache (thread-safe, version-counted)
│   │       ├── interface.py   # MarketDataSource ABC
│   │       ├── factory.py     # create_market_data_source(cache)
│   │       ├── simulator.py   # GBMSimulator + SimulatorDataSource
│   │       ├── massive_client.py  # MassiveDataSource (Polygon.io REST)
│   │       ├── seed_prices.py # Seed prices, GBM params, correlation groups
│   │       └── stream.py      # create_stream_router(cache) — SSE APIRouter
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py        # Asyncio event loop policy fixture
│       └── market/            # 6 test modules, 73 tests, 84% coverage
│           ├── __init__.py
│           ├── test_models.py          # 11 tests
│           ├── test_cache.py           # 13 tests
│           ├── test_simulator.py       # 17 tests
│           ├── test_simulator_source.py # 10 tests
│           ├── test_factory.py         # 7 tests
│           └── test_massive.py         # 13 tests
├── planning/                  # Project-wide spec docs (separate from .planning/)
│   ├── PLAN.md                # Canonical product spec (~900 lines)
│   ├── MARKET_DATA_SUMMARY.md # "What was built" summary for market data
│   ├── MARKET_INTERFACE.md    # Interface reference
│   ├── MARKET_SIMULATOR.md    # Simulator reference
│   ├── MASSIVE_API.md         # Massive client reference
│   └── archive/               # Older/fuller versions kept for history
│       ├── MARKET_DATA_DESIGN.md   # ~50 KB design doc
│       ├── MARKET_DATA_REVIEW.md
│       ├── MARKET_INTERFACE.md
│       ├── MARKET_SIMULATOR.md
│       └── MASSIVE_API.md
└── savedfiles/                # Loose stash of reusable agent/hook configs
    ├── agents/
    ├── commands/
    ├── filesUnder.ClaudeDirectory/
    └── filesUnderfinally/
```

## Key Locations

**Where code currently lives:**
- All production code: `backend/app/market/` (8 modules, ~500 LOC)
- All tests: `backend/tests/market/` (6 modules, ~730 LOC)
- The only runnable program: `backend/market_data_demo.py`

**Where documentation lives:**
- Canonical spec: `planning/PLAN.md` (also inlined via `CLAUDE.md`)
- Market-data handoff docs: `planning/MARKET_DATA_SUMMARY.md` and the per-component docs beside it
- Developer guides: `CLAUDE.md` (repo root) and `backend/CLAUDE.md`
- Reference history: `planning/archive/`

**Where things are expected but missing (per PLAN.md §4):**
- `frontend/` — Next.js static-export app (does not exist)
- `backend/db/` — schema SQL + seed logic (does not exist)
- `backend/app/main.py` (or equivalent) — FastAPI app/entry point (does not exist)
- `db/` — runtime SQLite volume mount, with `.gitkeep` (does not exist)
- `scripts/start_mac.sh`, `stop_mac.sh`, `start_windows.ps1`, `stop_windows.ps1` (none exist)
- `test/` — Playwright E2E + `docker-compose.test.yml` (does not exist)
- `Dockerfile`, `docker-compose.yml`, `.env`, `.env.example` (none exist)

## Naming Conventions

**Python (enforced by what's already checked in):**
- Module names: lowercase snake_case (`massive_client.py`, `seed_prices.py`)
- Class names: `CapWords` (`PriceUpdate`, `PriceCache`, `GBMSimulator`, `SimulatorDataSource`)
- Function/method names: snake_case
- Constants: `UPPER_SNAKE_CASE` (`SEED_PRICES`, `TICKER_PARAMS`, `INTRA_TECH_CORR`, `DEFAULT_DT`)
- Private helpers prefixed with `_` (`_rebuild_cholesky`, `_poll_once`, `_generate_events`)
- Test files: `test_<module>.py`; test classes `Test<Thing>`; test methods `test_<behavior>` (pytest convention)

**Package layout:**
- `app/` holds application code; tests mirror the layout under `tests/`
- Each subpackage exposes its public API via its `__init__.py` (see `backend/app/market/__init__.py` for the pattern)

## Import Patterns

- Relative imports *within* `app.market` (`from .cache import PriceCache`)
- Absolute imports from tests (`from app.market.cache import PriceCache`)
- Every module starts with `from __future__ import annotations` (simulator, interface, factory, cache, models, massive_client, stream)
- `pyproject.toml` ruff rule `I` keeps import order enforced

---

*Update when new top-level directories are added or a subsystem is carved off its own package.*
