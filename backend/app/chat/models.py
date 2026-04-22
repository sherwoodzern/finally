"""Pydantic v2 schemas for the chat subsystem: structured LLM output + request/response."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.watchlist.models import normalize_ticker


class TradeAction(BaseModel):
    """One trade entry in the LLM's structured response (PLAN.md Section 9, D-13)."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_ticker(v)


class WatchlistAction(BaseModel):
    """One watchlist mutation in the LLM's structured response (PLAN.md Section 9, D-13)."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    action: Literal["add", "remove"]

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_ticker(v)


class StructuredResponse(BaseModel):
    """LLM output contract (PLAN.md Section 9). response_format target for LiteLLM."""

    model_config = ConfigDict(extra="forbid")

    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistAction] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """POST /api/chat request body (D-07). extra='forbid' rejects unknown keys with 422."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=8192)


class TradeActionResult(BaseModel):
    """Enriched trade entry in ChatResponse (D-07 pass-through + per-action status)."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    status: Literal["executed", "failed"]
    price: float | None = None
    cash_balance: float | None = None
    executed_at: str | None = None
    error: str | None = None
    message: str | None = None


class WatchlistActionResult(BaseModel):
    """Enriched watchlist mutation in ChatResponse (D-07)."""

    ticker: str
    action: Literal["add", "remove"]
    status: Literal["added", "exists", "removed", "not_present", "failed"]
    error: str | None = None
    message: str | None = None


class ChatResponse(BaseModel):
    """POST /api/chat response body (D-07)."""

    message: str
    trades: list[TradeActionResult]
    watchlist_changes: list[WatchlistActionResult]


class ChatMessageOut(BaseModel):
    """One row in GET /api/chat/history response (D-19)."""

    id: str
    role: Literal["user", "assistant"]
    content: str
    actions: dict | None
    created_at: str


class HistoryResponse(BaseModel):
    """GET /api/chat/history response body (D-19)."""

    messages: list[ChatMessageOut]
