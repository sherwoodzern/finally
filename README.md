# FinAlly — AI Trading Workstation

A visually rich, AI-powered trading workstation: live market data, a simulated portfolio, and an LLM chat assistant that can analyze positions and execute trades on your behalf.

Built entirely by coding agents as the capstone for an agentic AI course.

## Stack

- **Frontend**: Next.js (TypeScript, static export), Tailwind, Lightweight Charts + Recharts
- **Backend**: FastAPI (Python, managed with `uv`), SSE for live prices
- **Storage**: SQLite (volume-mounted)
- **LLM**: LiteLLM → OpenRouter (`openai/gpt-oss-120b` via Cerebras), structured outputs
- **Market data**: built-in simulator by default; Massive/Polygon REST if `MASSIVE_API_KEY` is set
- **Deploy**: single Docker container on port 8000

## Quick Start

```bash
cp .env.example .env     # add OPENROUTER_API_KEY
./scripts/start_mac.sh   # or scripts/start_windows.ps1
```

Open http://localhost:8000. You start with a 10-ticker watchlist and $10,000 in virtual cash.

## Environment

| Var | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | required — LLM chat |
| `MASSIVE_API_KEY` | optional — real market data (else simulator) |
| `LLM_MOCK` | `true` for deterministic mock responses (tests) |

## Project Layout

```
frontend/    Next.js app (static export)
backend/     FastAPI + uv project (API, SSE, market data, LLM, db init)
planning/    Specs and agent reference docs (see PLAN.md)
scripts/     start/stop scripts (mac + windows)
test/        Playwright E2E tests
db/          Runtime SQLite volume mount
```

## Status

Market data subsystem is complete (see `planning/MARKET_DATA_SUMMARY.md`). Remaining components are in progress per `planning/PLAN.md`.

## License

See `LICENSE`.
