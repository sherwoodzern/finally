"""SQLite persistence subsystem for FinAlly.

Public API:
    open_database           - Open a long-lived sqlite3.Connection.
    init_database           - Run CREATE TABLE IF NOT EXISTS for all six tables.
    seed_defaults           - Insert default user + 10-ticker watchlist (idempotent).
    get_watchlist_tickers   - Return the default user's watchlist ticker list.
"""

from __future__ import annotations

from .connection import open_database
from .seed import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    get_watchlist_tickers,
    init_database,
    seed_defaults,
)

__all__ = [
    "open_database",
    "init_database",
    "seed_defaults",
    "get_watchlist_tickers",
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_USER_ID",
]
