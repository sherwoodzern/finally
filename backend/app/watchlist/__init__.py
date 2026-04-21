"""Watchlist subsystem for FinAlly.

Public API (Plan 04-01 — HTTP router lands in Plan 04-02):
    Models: WatchlistAddRequest, WatchlistItem, WatchlistResponse,
            WatchlistMutationResponse, normalize_ticker
    Service: get_watchlist, add_ticker, remove_ticker, AddResult, RemoveResult,
             DEFAULT_USER_ID
"""

from __future__ import annotations

from .models import (
    WatchlistAddRequest,
    WatchlistItem,
    WatchlistMutationResponse,
    WatchlistResponse,
    normalize_ticker,
)
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
    "get_watchlist",
    "normalize_ticker",
    "remove_ticker",
]
