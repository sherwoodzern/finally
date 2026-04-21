# Phase 4: Watchlist API - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 04-watchlist-api
**Mode:** `--auto` (all gray areas auto-selected, recommended options chosen)
**Areas discussed:** Module layout, Ticker normalization & validation, Idempotency response contract, Service ↔ market source coupling, GET response shape & fallback, Mutation ordering, GET ordering, DB helper location

---

## Module Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Sub-package mirror (routes.py + service.py + models.py + __init__.py) | Matches Phase 3 `app/portfolio/` and Phase 2 `app/db/` | ✓ |
| Single `watchlist.py` module under `app/` | Smaller surface, but breaks the Phase 3 pattern | |
| Co-locate in `app/db/` | Treats watchlist as DB concern only; ignores the HTTP edge | |

**User's choice (recommended):** Sub-package mirror.
**Notes:** Consistency with Phase 3 is the dominant factor — Phase 5 will import from `app.watchlist` the same way it already imports from `app.portfolio`. See CONTEXT.md D-01.

---

## Ticker Normalization & Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic `field_validator` at the edge (uppercase + strip + regex) | Rejects garbage as 422 before the handler runs; service trusts input | ✓ |
| Validate in the service layer | Works for non-HTTP callers but duplicates work when FastAPI validates again | |
| Relying on DB `UNIQUE` for dedup, no pre-validation | Permits lowercase / whitespace-padded rows, breaks PLAN.md §6 equality | |

**User's choice (recommended):** Pydantic field_validator at the edge.
**Notes:** Regex `^[A-Z][A-Z0-9.]{0,9}$` covers standard NYSE/NASDAQ symbols plus compound (`BRK.B`). No whitelist — PLAN.md §6 explicitly supports unknown-ticker onboarding. See CONTEXT.md D-04, D-05.

---

## Idempotency & Response Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Uniform 200 + `status: Literal["added","exists","removed","not_present"]` | Single discriminator for FE + Phase 5 LLM; no HTTP-code sniffing | ✓ |
| 201 on insert / 204 on delete / 409 on conflict | Idiomatic REST but forces branching on status codes | |
| 200 with empty body on no-op | Loses the signal that a no-op happened | |

**User's choice (recommended):** Uniform 200 + status discriminator.
**Notes:** Success criterion #4 explicitly prefers "a sensible response, not a 500". The Phase 5 LLM chat narration is a strong tiebreaker. See CONTEXT.md D-06.

---

## Service ↔ Market Source Coupling

| Option | Description | Selected |
|--------|-------------|----------|
| Route orchestrates DB service (sync) then awaits source | Keeps service FastAPI-agnostic + async-free; Phase 5 reuses trivially | ✓ |
| Service takes `source` and awaits it internally | Forces service to be async and ties it to `MarketDataSource` | |
| Source subscribes to a DB watcher / polls DB | Over-engineered for a single-user app | |

**User's choice (recommended):** Route orchestrates; service stays sync and DB-only.
**Notes:** Mirrors Phase 3's trade service (D-02) — pure functions on `sqlite3.Connection` are the codebase's service idiom. See CONTEXT.md D-02.

---

## GET Response Shape & Cache Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| `{ticker, added_at, price, previous_price, change_percent, direction, timestamp}` with `None` fallback when cache is cold | Mirrors `/api/portfolio` graceful fallback; never 500s on cold start | ✓ |
| Omit price fields when cache is cold | Forces frontend to branch on `"price" in item` | |
| Use `0.0` placeholders | Lies to the frontend about a real price | |
| Fail with 503 if any cache tick missing | Breaks success criterion #1 on first-second-after-startup | |

**User's choice (recommended):** Full shape with `None` fallback.
**Notes:** Consistent with Phase 3 D-01 `avg_cost` fallback on `/api/portfolio`. See CONTEXT.md D-07.

---

## Mutation Ordering (DB vs Source)

| Option | Description | Selected |
|--------|-------------|----------|
| DB first, then source (idempotent awaits) | DB is the canonical set per PLAN.md §6; source re-reads DB on restart | ✓ |
| Source first, then DB | If DB fails we have a source-only ticker that won't survive restart | |
| Two-phase commit across DB + source | Over-engineered; source impls already swallow their own errors | |

**User's choice (recommended):** DB first, source second.
**Notes:** Both `SimulatorDataSource` and `MassiveDataSource` `add_ticker` / `remove_ticker` methods are already idempotent (see `simulator.py:244-257`, `massive_client.py:68-78`). See CONTEXT.md D-09, D-10, D-11.

---

## GET Ordering

| Option | Description | Selected |
|--------|-------------|----------|
| `ORDER BY added_at ASC, ticker ASC` | Matches existing `get_watchlist_tickers` pattern (`app/db/seed.py:69`) | ✓ |
| `ORDER BY ticker ASC` | Ignores chronology — recently-added tickers disappear into alphabetical middle | |
| Unordered | Breaks determinism; frontend would re-sort anyway but tests become flaky | |

**User's choice (recommended):** `added_at ASC, ticker ASC`.
**Notes:** Seed rows share `added_at`; `ticker` is the tiebreaker. See CONTEXT.md D-08.

---

## DB Helper Location

| Option | Description | Selected |
|--------|-------------|----------|
| New `get_watchlist` / `add_ticker` / `remove_ticker` in `app/watchlist/service.py` | Mirrors Phase 3 (SQL lives next to its domain); leaves `get_watchlist_tickers` stable | ✓ |
| Move/extend helpers in `app/db/seed.py` | `seed.py` becomes a catch-all, not a seeder | |
| Introduce `app/db/queries.py` | New module with one owner; premature abstraction for ~3 helpers | |

**User's choice (recommended):** `app/watchlist/service.py`.
**Notes:** Phase 2 D-05 already pushed SQL into the seeder; Phase 3 kept new SQL in its own sub-package. Phase 4 follows Phase 3. See CONTEXT.md D-01, "Claude's Discretion" DB-helper refactor note.

---

## Claude's Discretion

Deferred to the planner per CONTEXT.md:
- Exact SQL dialect (`INSERT ... ON CONFLICT DO NOTHING` vs `INSERT OR IGNORE`)
- `RETURNING` clause usage
- `uuid.uuid4()` / `datetime.now(UTC).isoformat()` style match
- Whether to unify `get_watchlist_tickers` + new `get_watchlist` in a single helper
- Response field naming (`timestamp` vs `updated_at`)
- Handler ordering inside `routes.py`
- Test fixture style (real simulator + `asyncio.sleep(0)` vs mocked source)
- Log level for idempotent no-ops (INFO recommended)

## Deferred Ideas

See CONTEXT.md `<deferred>` — real-time multi-client delivery, external ticker-universe validation, bulk endpoints, soft-delete, per-user watchlists, ticker rename, mutation audit log. None in v1 scope.
