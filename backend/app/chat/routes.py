"""HTTP edge for the chat subsystem: POST /, GET /history."""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, Query

from app.market import MarketDataSource, PriceCache

from . import service
from .client import ChatClient
from .models import ChatRequest, ChatResponse, HistoryResponse

logger = logging.getLogger(__name__)


def create_chat_router(
    db: sqlite3.Connection,
    cache: PriceCache,
    source: MarketDataSource,
    client: ChatClient,
) -> APIRouter:
    """Build an APIRouter closed over db + cache + source + LLM client (D-01, D-13).

    Mirrors create_watchlist_router + create_portfolio_router: a fresh router per
    lifespan so test-spawned apps never collide on routes (01-CONTEXT.md D-04,
    05-CONTEXT.md D-01).

    Error boundary (D-14): app.chat.service.ChatTurnError -> HTTP 502 with
    detail={"error":"chat_turn_error","message": str(exc)}. Pydantic v2 validation
    failures (extras, empty message, missing message, out-of-bounds limit) map to
    422 via FastAPI's default handler - we do NOT write a custom handler.
    """
    router = APIRouter(prefix="/api/chat", tags=["chat"])

    @router.post("", response_model=ChatResponse)
    async def post_chat_route(req: ChatRequest) -> ChatResponse:
        """Run a single chat turn (CHAT-01, CHAT-04, CHAT-05)."""
        try:
            return await service.run_turn(db, cache, source, client, req.message)
        except service.ChatTurnError as exc:
            # D-14: LLM transport / auth / malformed JSON. The user-turn row was
            # already persisted inside run_turn before client.complete() was
            # invoked (D-18 invariant - verified by test_routes_llm_errors.py).
            raise HTTPException(
                status_code=502,
                detail={"error": "chat_turn_error", "message": str(exc)},
            ) from exc

    @router.get("/history", response_model=HistoryResponse)
    async def get_chat_history_route(
        limit: int = Query(default=50, ge=1, le=500),
    ) -> HistoryResponse:
        """Return the most-recent `limit` chat rows in ASC order (CHAT-05, D-19)."""
        return service.get_history(db, limit=limit)

    return router
