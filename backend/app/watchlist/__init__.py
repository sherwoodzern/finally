"""Watchlist subsystem for FinAlly.

Public API:
    Models: WatchlistAddRequest, WatchlistItem, WatchlistResponse,
            WatchlistMutationResponse, normalize_ticker
    Service: get_watchlist, add_ticker, remove_ticker, AddResult, RemoveResult,
             DEFAULT_USER_ID
    Router: create_watchlist_router
"""

from __future__ import annotations

from .models import (
    WatchlistAddRequest,
    WatchlistItem,
    WatchlistMutationResponse,
    WatchlistResponse,
    normalize_ticker,
)
from .routes import create_watchlist_router
from .service import (
    DEFAULT_USER_ID,
    AddResult,
    RemoveResult,
    add_ticker,
    get_watchlist,
    remove_ticker,
)

__all__ = [
    "DEFAULT_USER_ID",
    "AddResult",
    "RemoveResult",
    "WatchlistAddRequest",
    "WatchlistItem",
    "WatchlistMutationResponse",
    "WatchlistResponse",
    "add_ticker",
    "create_watchlist_router",
    "get_watchlist",
    "normalize_ticker",
    "remove_ticker",
]
