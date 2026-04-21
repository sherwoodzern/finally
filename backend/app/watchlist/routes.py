"""HTTP edge for the watchlist subsystem: GET /, POST /, DELETE /{ticker}."""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException

from app.market import MarketDataSource, PriceCache

from . import service
from .models import (
    WatchlistAddRequest,
    WatchlistMutationResponse,
    WatchlistResponse,
    normalize_ticker,
)

logger = logging.getLogger(__name__)


def create_watchlist_router(
    db: sqlite3.Connection,
    cache: PriceCache,
    source: MarketDataSource,
) -> APIRouter:
    """Build an APIRouter closed over db + cache + source (D-13).

    A fresh router per call mirrors create_stream_router and create_portfolio_router
    and avoids duplicate routes across test-spawned apps. The mutation handlers
    follow a DB-first-then-source choreography (D-11): the SQLite write is the
    source of truth, and a post-commit source-side failure is logged with
    a traceback but returns 200 OK - the next app restart reconciles because
    the price-update loop reads the ticker union from `watchlist` on startup.

    Idempotent no-ops return 200 with status='exists'/'not_present' (D-06, SC#4),
    NOT 409/404.
    """

    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("", response_model=WatchlistResponse)
    async def get_watchlist_route() -> WatchlistResponse:
        """Return the current watchlist with live prices from the cache (WATCH-01)."""
        return service.get_watchlist(db, cache)

    @router.post("", response_model=WatchlistMutationResponse)
    async def post_watchlist_route(
        req: WatchlistAddRequest,
    ) -> WatchlistMutationResponse:
        """Add a ticker; idempotent no-op on duplicate (WATCH-02, D-06, D-09, D-11)."""
        result = service.add_ticker(db, req.ticker)

        if result.status == "added":
            try:
                await source.add_ticker(req.ticker)
            except Exception:
                # D-11: DB is the reconciliation anchor; next restart heals.
                logger.warning(
                    "Watchlist: source.add_ticker(%s) raised after DB commit",
                    req.ticker,
                    exc_info=True,
                )

        return WatchlistMutationResponse(
            ticker=result.ticker, status=result.status
        )

    @router.delete("/{ticker}", response_model=WatchlistMutationResponse)
    async def delete_watchlist_route(ticker: str) -> WatchlistMutationResponse:
        """Remove a ticker; idempotent no-op when absent (WATCH-03, D-06, D-10, D-11)."""
        try:
            normalized = normalize_ticker(ticker)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        result = service.remove_ticker(db, normalized)

        if result.status == "removed":
            try:
                await source.remove_ticker(normalized)
            except Exception:
                logger.warning(
                    "Watchlist: source.remove_ticker(%s) raised after DB commit",
                    normalized,
                    exc_info=True,
                )

        return WatchlistMutationResponse(
            ticker=result.ticker, status=result.status
        )

    return router
