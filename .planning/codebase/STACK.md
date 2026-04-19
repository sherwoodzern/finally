# Technology Stack

**Analysis Date:** 2026-04-19

> **Scope note:** FinAlly is early-stage. The full stack described in `planning/PLAN.md` is aspirational. Today **only the backend market-data subsystem exists**. Everything marked *Planned* below is specified but not yet implemented.

## Languages

**Primary (implemented):**
- Python 3.12+ — Backend (see `backend/pyproject.toml` `requires-python = ">=3.12"`)

**Primary (planned):**
- TypeScript — Next.js frontend in `frontend/` (directory does not exist yet)

## Runtime

**Environment (implemented):**
- Python 3.12 for the backend; asyncio-based
- No web server wired up yet — the app module `backend/app/__init__.py` is essentially empty; no `main.py` / ASGI entrypoint exists

**Environment (planned):**
- Uvicorn hosting FastAPI on port 8000 inside a single Docker container
- Node.js 20 for Next.js static export at build time only

**Package Manager:**
- `uv` for Python (required per `CLAUDE.md`: "Always `uv run xxx` never `python3 xxx`")
- Lockfile: `backend/uv.lock` present (≈150 KB, committed)
- `npm` planned for frontend

## Frameworks

**Core (implemented):**
- `fastapi>=0.115.0` — imported only in `backend/app/market/stream.py` for the SSE `APIRouter`; no app instance exists yet
- `uvicorn[standard]>=0.32.0` — listed in deps but never invoked in code

**Core (planned, not yet present):**
- Next.js (TypeScript, `output: 'export'` for static export) — served by FastAPI as static files
- Tailwind CSS
- Lightweight Charts (canvas) for ticker charts + sparklines
- Recharts (SVG) for P&L line chart
- LiteLLM → OpenRouter (model `openrouter/openai/gpt-oss-120b`, provider Cerebras) with structured outputs
- SQLite (stdlib `sqlite3`) — no schema/init code committed yet

**Testing (implemented):**
- `pytest>=8.3.0` (dev extra)
- `pytest-asyncio>=0.24.0` with `asyncio_mode = "auto"`
- `pytest-cov>=5.0.0`
- Playwright (planned for `test/` E2E — directory does not exist)

**Lint/Format:**
- `ruff>=0.7.0` (dev extra). Config in `backend/pyproject.toml`:
  - `line-length = 100`, `target-version = "py312"`
  - Rules: `E, F, I, N, W`; ignore `E501`

## Key Dependencies

**Critical (implemented):**
- `massive>=1.0.0` — Polygon.io SDK wrapper, used by `backend/app/market/massive_client.py`
- `numpy>=2.0.0` — Cholesky decomposition for correlated GBM, `backend/app/market/simulator.py`
- `rich>=13.0.0` — terminal demo dashboard `backend/market_data_demo.py`

**Critical (planned):**
- `litellm` — LLM gateway (not yet a dependency)
- `python-dotenv` or equivalent — `.env` loading (not yet a dependency)

## Configuration

**Environment variables (per `planning/PLAN.md` §5):**
- `OPENROUTER_API_KEY` — required, LLM chat (planned)
- `MASSIVE_API_KEY` — optional; read by `backend/app/market/factory.py:24` via `os.environ.get`
- `LLM_MOCK` — `"true"` for deterministic LLM responses (planned)

**Build / project config:**
- `backend/pyproject.toml` — Python project, ruff, pytest, coverage config
- `backend/uv.lock`
- `backend/app/market/seed_prices.py` — hardcoded initial prices and GBM params
- `.env.example` — **not present** (called for in `README.md` quick-start but not committed)

## Platform Requirements

**Development (today):**
- macOS / Linux / Windows with Python 3.12 and `uv` installed
- `cd backend && uv sync --extra dev` then `uv run pytest` or `uv run market_data_demo.py`

**Production (planned):**
- Single Docker container exposing port 8000
- Named Docker volume `finally-data` mounted to `/app/db` for SQLite persistence
- Multi-stage `Dockerfile` (Node 20 → Python 3.12 slim) — **not present**
- `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1` — **not present**

---

*Stack analysis: 2026-04-19*
*Update after major dependency changes or when new subsystems are implemented.*
