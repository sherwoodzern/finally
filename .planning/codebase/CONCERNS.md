# Concerns

**Analysis Date:** 2026-04-19

The single biggest concern is not in the code that exists — it is the **gap between `planning/PLAN.md` and what is actually built**. The market-data subsystem is solid; nearly everything else is unimplemented. Ship plans must account for that.

## Implementation Gap (by subsystem)

| Subsystem | Planned (PLAN.md) | Built today | Gap severity |
|---|---|---|---|
| Market data — simulator | GBM w/ correlation, shocks, dynamic tickers | ✅ Implemented, 84% covered | None |
| Market data — Massive/Polygon | REST polling, free-tier safe interval | ✅ Implemented | Real-network integration test absent |
| SSE `/api/stream/prices` | Live price stream | 🟡 Router factory exists, **not mounted on any FastAPI app** | High — unreachable |
| FastAPI app + `lifespan` startup | Lazy DB init, start market source, mount SSE + static | ❌ No `app/main.py`, no app instance | High |
| SQLite schema + seed | 6 tables, lazy init, volume-mounted | ❌ No `backend/db/`, no schema, no init code | High |
| Portfolio (REST + logic) | `/api/portfolio`, `/api/portfolio/trade`, `/api/portfolio/history` | ❌ Not started | High |
| Watchlist CRUD | `/api/watchlist` endpoints | ❌ Not started | High |
| Chat / LLM | LiteLLM→OpenRouter, structured outputs, auto-exec | ❌ Not started; `litellm` not a dep | High |
| Frontend | Next.js static export, dark terminal UI | ❌ `frontend/` does not exist | High |
| Docker multi-stage | Node→Python image, single port 8000 | ❌ No `Dockerfile` | Medium (ship blocker) |
| Start/stop scripts | `scripts/start_mac.sh`, etc. | ❌ Not present | Low |
| `.env.example` | Committed template | ❌ Missing even though README references it | Low |
| E2E tests | Playwright in `test/` under `docker-compose.test.yml` | ❌ Not present | Medium (confidence gap) |

## Architectural Risks (inherent to the PLAN.md design)

These are not bugs — they are design choices to watch as implementation proceeds.

1. **Auto-executing LLM trades (`planning/PLAN.md` §9).** By design, the LLM can execute trades with no confirmation dialog. Fine for a demo with play money; fragile boundary if anyone ever points this at real brokerage APIs. Must never be copy-pasted to a production trading product without rethinking.
2. **No authentication / single user.** `user_id` defaults to `"default"` on every table (`planning/PLAN.md` §7). Running this publicly would expose the same state to everyone. Containment: keep it local / behind a personal deploy.
3. **Polygon free-tier rate limit (5 req/min).** `MassiveDataSource` default `poll_interval=15.0` sec keeps us under it, but `add_ticker` calls can't push updates faster than one poll cycle. If the watchlist grows rapidly, the SDK call `get_snapshot_all(tickers=[...])` may stuff a long ticker list into a single snapshot-all request — behavior at scale is not tested.
4. **SSE reconnection semantics.** `stream._generate_events` emits `retry: 1000` and relies on the browser's `EventSource`. Server-side client-disconnect detection is via `request.is_disconnected()` inside a 500 ms sleep — a client that disconnects mid-sleep may linger briefly before cleanup. Acceptable for a demo.
5. **Version-gated SSE.** `stream.py` only emits when `price_cache.version` changes. If the cache never advances (e.g., the producer background task died), the stream silently sends nothing. There is **no heartbeat/keepalive** so proxies may time out the connection on idle.
6. **Daily-change baseline is session-relative.** `planning/PLAN.md` §6 explicitly says "daily" means "since the backend process started tracking this ticker." When the DB layer lands, the `PriceCache` entry still needs a `session_start_price` that restarts with the process — must not be loaded from the DB or it'll mis-report after a restart.
7. **SQLite + single process + Docker volume.** Fine for one user; any future multi-user or high-concurrency path needs a real DB. The schema comment in `planning/PLAN.md` already includes `user_id` "for future multi-user" — but SQLite itself is the bottleneck, not the schema.
8. **Auto-executed LLM trades share validation with manual trades.** Good — but the LLM's ability to *compose* trades (e.g., sell-then-buy) isn't atomic across the two trade calls. A partial execution (first sell succeeds, second buy fails on cash math somewhere) can leave the portfolio in a weird state. Worth considering a transactional wrapper when implementing.
9. **Secrets in env only.** `OPENROUTER_API_KEY`, `MASSIVE_API_KEY` read from env; if docker-compose files or scripts accidentally log `env`, keys leak. Low impact but worth noting in deploy docs.

## Code-Level Concerns (existing code)

Grepped for `TODO`, `FIXME`, `HACK`, `XXX` across the repo — **no hits** in production code. The prior code review (see `planning/archive/MARKET_DATA_REVIEW.md`) found 7 issues, all resolved per `planning/MARKET_DATA_SUMMARY.md`.

Smaller items visible on inspection:

- **Error swallowing in `MassiveDataSource._poll_once`** is intentional and documented (`backend/app/market/massive_client.py:118-121`), but a rapid sequence of 401/429 responses will spin silently with only `logger.error`. Consider a counter + exponential backoff when the DB layer / monitoring lands.
- **`PriceCache.get_all()` returns a shallow copy inside the lock** (`backend/app/market/cache.py:49-52`) — safe because values are frozen `PriceUpdate`s, but if anyone ever mutates `PriceUpdate` fields that assumption breaks. Keeping `frozen=True, slots=True` is load-bearing.
- **`create_market_data_source()` reads env at construction time** (`backend/app/market/factory.py:24`). A test that mutates `MASSIVE_API_KEY` after import must re-import or call the factory fresh.
- **`GBMSimulator._rebuild_cholesky()` is O(n²)** (acknowledged in the comment at `backend/app/market/simulator.py:154`). Fine below ~50 tickers; a user spamming 500 `add_ticker` calls rebuilds the matrix each time.
- **Default seed tickers are duplicated** across `backend/app/market/seed_prices.py` (`SEED_PRICES` keys), `backend/market_data_demo.py` (`TICKERS`), and `planning/PLAN.md` (DB seed). When the DB seed code is written, establish a single source of truth to avoid drift.
- **Random shock events use `random.random()` and `random.choice()`** (`backend/app/market/simulator.py:105-108`) while GBM moves use `numpy`. Two RNG streams; neither is seeded in production paths. Test-time determinism is achieved through mocking, not seeding.

## Documentation Concerns

- **`planning/` has been deleted and re-uploaded (see git log: `Delete planning/MASSIVE_API.md`, `Delete planning/MARKET_SIMULATOR.md`, ... then `Add files via upload`).** The current files are back; this GSD map is anchored to the current state. If `planning/` is churned again, this map may drift.
- **`README.md` references `scripts/start_mac.sh` and `.env.example`** that do not exist in the repo. Following the quick-start as written will fail today.
- **Two CLAUDE.md files** (`./CLAUDE.md` and `./backend/CLAUDE.md`) — both consistent, but if a rule changes, both need updating.

## Security Concerns

- Scanned `.planning/codebase/*.md` and `planning/*` for common secret patterns (API keys, private keys, JWTs) — none found.
- No `.env` or `.env.example` committed. `.gitignore` excludes `.env`.
- Existing code has no eval/exec, no subprocess, no arbitrary user-input-to-filesystem paths.

## Highest-Leverage Next Moves (concerns → actions)

1. **Mount what exists.** Create a minimal `backend/app/main.py` with a FastAPI app, `lifespan` that starts a `PriceCache` + `create_market_data_source()`, and includes `create_stream_router(cache)`. Everything above is specified; nothing is blocked.
2. **Write the DB init module** (`backend/db/` + `backend/app/db/`) so downstream portfolio/watchlist/chat features have a place to live.
3. **Pick a source of truth for the default watchlist** before the DB layer copies it a third time.
4. **Add a `.env.example`** — the README tells new developers to copy it.
5. **Keep PLAN.md fidelity high as work proceeds.** When the plan diverges from reality (e.g., poll interval changes, new env vars), update PLAN.md in the same commit to keep the single source of truth honest.

---

*Update when significant new tech debt is introduced or when an architectural assumption here is explicitly changed.*
