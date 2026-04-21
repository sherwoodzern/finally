"""HTTP edge for the portfolio subsystem: GET /, POST /trade, GET /history."""

from __future__ import annotations

import sqlite3
import time

from fastapi import APIRouter, HTTPException, Query, Request

from app.market import PriceCache

from . import service
from .models import (
    HistoryResponse,
    PortfolioResponse,
    TradeRequest,
    TradeResponse,
)


def create_portfolio_router(
    db: sqlite3.Connection,
    cache: PriceCache,
) -> APIRouter:
    """Build an APIRouter closed over db + cache.

    A fresh router per call mirrors create_stream_router (app/market/stream.py)
    and avoids duplicate routes across test-spawned apps (01-CONTEXT.md D-04).
    Domain validation failures from the service layer map 1:1 to HTTP 400 with
    detail={"error": exc.code, "message": str(exc)} (D-03, D-09, D-10).
    """
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("", response_model=PortfolioResponse)
    async def get_portfolio() -> PortfolioResponse:
        return service.get_portfolio(db, cache)

    @router.post("/trade", response_model=TradeResponse)
    async def post_trade(request: Request, req: TradeRequest) -> TradeResponse:
        try:
            response = service.execute_trade(
                db, cache, req.ticker, req.side, req.quantity,
            )
        except service.TradeValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": exc.code, "message": str(exc)},
            ) from exc
        # D-07: reset the 60s snapshot clock so the tick observer does not
        # double-snapshot within the next minute. Route-level (not service-
        # level) keeps execute_trade FastAPI-agnostic per 03-CONTEXT.md D-02.
        request.app.state.last_snapshot_at = time.monotonic()
        return response

    @router.get("/history", response_model=HistoryResponse)
    async def get_history(
        limit: int = Query(default=1000, ge=1, le=1000),
    ) -> HistoryResponse:
        return service.get_history(db, limit=limit)

    return router
