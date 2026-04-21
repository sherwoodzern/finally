"""Pydantic v2 request/response schemas for the portfolio + trading API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TradeRequest(BaseModel):
    """Request body for POST /api/portfolio/trade (D-03).

    Strict config: unknown keys produce 422. Literal side + Field(gt=0) quantity
    guarantee malformed inputs are rejected before the handler runs.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=10)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)


class TradeResponse(BaseModel):
    """Success response for POST /api/portfolio/trade."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    price: float
    cash_balance: float
    position_quantity: float
    position_avg_cost: float
    executed_at: str


class PositionOut(BaseModel):
    """One row in PortfolioResponse.positions."""

    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    change_percent: float


class PortfolioResponse(BaseModel):
    """Response for GET /api/portfolio."""

    cash_balance: float
    total_value: float
    positions: list[PositionOut]


class SnapshotOut(BaseModel):
    """One snapshot in HistoryResponse.snapshots."""

    total_value: float
    recorded_at: str


class HistoryResponse(BaseModel):
    """Response for GET /api/portfolio/history."""

    snapshots: list[SnapshotOut]
