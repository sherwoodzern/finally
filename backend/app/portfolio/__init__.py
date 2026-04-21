"""Portfolio + trading subsystem for FinAlly.

Public API (filled in across Plan 03-02 and 03-03):
    Models: TradeRequest, TradeResponse, PositionOut, PortfolioResponse,
            SnapshotOut, HistoryResponse
    Service: execute_trade, get_portfolio, compute_total_value, get_history,
             make_snapshot_observer
    Exceptions: TradeValidationError, InsufficientCash, InsufficientShares,
                UnknownTicker, PriceUnavailable
    Router: create_portfolio_router
"""

from __future__ import annotations

from .models import (
    HistoryResponse,
    PortfolioResponse,
    PositionOut,
    SnapshotOut,
    TradeRequest,
    TradeResponse,
)
from .routes import create_portfolio_router
from .service import (
    DEFAULT_USER_ID,
    InsufficientCash,
    InsufficientShares,
    PriceUnavailable,
    TradeValidationError,
    UnknownTicker,
    compute_total_value,
    execute_trade,
    get_history,
    get_portfolio,
    make_snapshot_observer,
)

__all__ = [
    "DEFAULT_USER_ID",
    "HistoryResponse",
    "InsufficientCash",
    "InsufficientShares",
    "PortfolioResponse",
    "PositionOut",
    "PriceUnavailable",
    "SnapshotOut",
    "TradeRequest",
    "TradeResponse",
    "TradeValidationError",
    "UnknownTicker",
    "compute_total_value",
    "create_portfolio_router",
    "execute_trade",
    "get_history",
    "get_portfolio",
    "make_snapshot_observer",
]
