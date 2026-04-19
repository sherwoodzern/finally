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

    Startup ticker set is list(SEED_PRICES.keys()) - single source of truth flagged
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
