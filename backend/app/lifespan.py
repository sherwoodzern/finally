"""FastAPI lifespan: DB + PriceCache + market data source startup/shutdown."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .chat import create_chat_client, create_chat_router
from .db import get_watchlist_tickers, init_database, open_database, seed_defaults
from .market import PriceCache, create_market_data_source, create_stream_router
from .portfolio import create_portfolio_router, make_snapshot_observer
from .watchlist import create_watchlist_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open DB -> init -> seed -> build PriceCache -> start market source -> mount SSE.

    Phase 2 additions on top of Phase 1 (01-CONTEXT.md D-02, D-04):
      D-01/D-09: open sqlite3.Connection at DB_PATH (default db/finally.db),
                 creating the parent directory if missing.
      D-02:      attach the connection to app.state.db alongside price_cache
                 and market_source.
      D-04 (seed idempotency): watchlist seed runs only when the table is empty;
                 users_profile uses INSERT OR IGNORE keyed on id='default'.
      D-05:      source.start(tickers) receives the DB watchlist (not
                 list(SEED_PRICES.keys())) - PLAN.md section 6 contract.
      D-07:      DB_PATH resolved via os.environ.get at lifespan entry, after
                 .env has been loaded in backend/app/main.py.

    Phase 3 additions (03-RESEARCH.md Lifespan diff, D-05/D-06/D-07):
      - Initialise app.state.last_snapshot_at = 0.0 BEFORE registering the
        observer (the observer closure reads state.last_snapshot_at on its
        first tick).
      - Register make_snapshot_observer(app.state) on the market source so a
        portfolio snapshot is written at most once per 60 monotonic seconds.
      - Mount create_portfolio_router(conn, cache) alongside the SSE router so
        /api/portfolio, /api/portfolio/trade, and /api/portfolio/history are
        reachable for the lifetime of the app.
    """
    # D-05: warn on startup if the live LLM path is selected but no key is set.
    # Redact: never log the key value. Only the presence/absence is logged.
    if (
        os.environ.get("LLM_MOCK") != "true"
        and not os.environ.get("OPENROUTER_API_KEY")
    ):
        logger.warning(
            "OPENROUTER_API_KEY is unset and LLM_MOCK != 'true'; "
            "POST /api/chat will return 502 until a key is provided"
        )

    db_path = os.environ.get("DB_PATH", "db/finally.db")
    conn = open_database(db_path)
    init_database(conn)
    seed_defaults(conn)

    cache = PriceCache()
    source = create_market_data_source(cache)

    tickers = get_watchlist_tickers(conn)
    await source.start(tickers)

    app.state.db = conn
    app.state.price_cache = cache
    app.state.market_source = source
    app.state.last_snapshot_at = 0.0                                   # D-06
    source.register_tick_observer(make_snapshot_observer(app.state))   # D-05
    app.include_router(create_stream_router(cache))
    app.include_router(create_portfolio_router(conn, cache))
    app.include_router(create_watchlist_router(conn, cache, source))   # D-13
    chat_client = create_chat_client()
    app.state.chat_client = chat_client
    app.include_router(create_chat_router(conn, cache, source, chat_client))   # D-20

    logger.info(
        "App started: db=%s tickers=%d source=%s",
        db_path,
        len(tickers),
        type(source).__name__,
    )
    try:
        yield
    finally:
        await source.stop()
        conn.close()
        logger.info("App stopped")
