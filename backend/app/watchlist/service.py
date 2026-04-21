"""Pure-function service: list / add / remove watchlist entries (DB-only, FastAPI-agnostic)."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.market import PriceCache

from .models import WatchlistItem, WatchlistResponse

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"


@dataclass(frozen=True, slots=True)
class AddResult:
    """Return type for add_ticker: the post-validation ticker + idempotent status."""

    ticker: str
    status: Literal["added", "exists"]


@dataclass(frozen=True, slots=True)
class RemoveResult:
    """Return type for remove_ticker: the post-validation ticker + idempotent status."""

    ticker: str
    status: Literal["removed", "not_present"]


def get_watchlist(
    conn: sqlite3.Connection,
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
) -> WatchlistResponse:
    """Return the watchlist ordered by added_at ASC, ticker ASC (D-08).

    Cache misses fall back to None for every price field (D-05). The watchlist
    has no avg_cost analog, so unlike get_portfolio there is nothing to show
    when the cache is cold - we simply emit None.
    """
    rows = conn.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? "
        "ORDER BY added_at ASC, ticker ASC",
        (user_id,),
    ).fetchall()

    items: list[WatchlistItem] = []
    for row in rows:
        ticker = row["ticker"]
        cached = cache.get(ticker)
        if cached is None:
            items.append(
                WatchlistItem(
                    ticker=ticker,
                    added_at=row["added_at"],
                    price=None,
                    previous_price=None,
                    change_percent=None,
                    direction=None,
                    timestamp=None,
                )
            )
        else:
            items.append(
                WatchlistItem(
                    ticker=ticker,
                    added_at=row["added_at"],
                    price=cached.price,
                    previous_price=cached.previous_price,
                    change_percent=cached.change_percent,
                    direction=cached.direction,
                    timestamp=cached.timestamp,
                )
            )

    return WatchlistResponse(items=items)


def add_ticker(
    conn: sqlite3.Connection,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> AddResult:
    """Idempotently add a ticker to the watchlist (D-06, D-09).

    Relies on the (user_id, ticker) UNIQUE constraint plus ON CONFLICT DO NOTHING
    so a duplicate insert returns cursor.rowcount == 0 without raising. A single
    atomic SQL statement + single commit keeps the write path trivial.
    """
    now = datetime.now(UTC).isoformat()
    cur = conn.execute(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, ticker) DO NOTHING",
        (str(uuid.uuid4()), user_id, ticker, now),
    )
    if cur.rowcount == 1:
        conn.commit()
        logger.info("Watchlist: added %s for user %s", ticker, user_id)
        return AddResult(ticker=ticker, status="added")
    logger.info(
        "Watchlist: %s already present for user %s (no-op)", ticker, user_id
    )
    return AddResult(ticker=ticker, status="exists")


def remove_ticker(
    conn: sqlite3.Connection,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> RemoveResult:
    """Idempotently remove a ticker from the watchlist (D-06, D-09).

    Uses cursor.rowcount to discriminate the "actually deleted" vs. "already
    absent" paths symmetrically with add_ticker.
    """
    cur = conn.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )
    if cur.rowcount == 1:
        conn.commit()
        logger.info("Watchlist: removed %s for user %s", ticker, user_id)
        return RemoveResult(ticker=ticker, status="removed")
    logger.info(
        "Watchlist: %s not present for user %s (no-op)", ticker, user_id
    )
    return RemoveResult(ticker=ticker, status="not_present")
