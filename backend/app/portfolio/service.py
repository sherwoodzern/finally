"""Pure-function service: trade execution, portfolio valuation, history, snapshot observer."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Literal

from app.market import PriceCache

from .models import TradeResponse

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"

# Epsilon for float residuals when deciding whether a sell zeroed a position (D-15).
_ZERO_QTY_EPSILON = 1e-9


class TradeValidationError(Exception):
    """Base class for trade validation failures (D-09)."""

    code: str = "trade_validation_error"


class InsufficientCash(TradeValidationError):  # noqa: N818
    """Buy rejected: quantity * price exceeds users_profile.cash_balance."""

    code: str = "insufficient_cash"


class InsufficientShares(TradeValidationError):  # noqa: N818
    """Sell rejected: requested quantity exceeds the held position."""

    code: str = "insufficient_shares"


class UnknownTicker(TradeValidationError):  # noqa: N818
    """Trade rejected: ticker is not in the user's watchlist (D-14)."""

    code: str = "unknown_ticker"


class PriceUnavailable(TradeValidationError):  # noqa: N818
    """Trade rejected: PriceCache has no tick for this ticker yet (D-13)."""

    code: str = "price_unavailable"


def _compute_total_value_with(
    conn: sqlite3.Connection,
    cache: PriceCache,
    cash: float,
    user_id: str,
) -> float:
    """Sum cash + Σ(qty * (cache.get_price(t) or avg_cost)) over all positions."""
    rows = conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    total = cash
    for row in rows:
        ticker = row["ticker"]
        qty = float(row["quantity"])
        avg = float(row["avg_cost"])
        cached = cache.get_price(ticker)
        price = cached if cached is not None else avg
        total += qty * price
    return total


def execute_trade(
    conn: sqlite3.Connection,
    cache: PriceCache,
    ticker: str,
    side: Literal["buy", "sell"],
    quantity: float,
    user_id: str = DEFAULT_USER_ID,
) -> TradeResponse:
    """Execute a market-order trade: validate, then write cash + position + trade + snapshot.

    All writes happen inside one implicit sqlite3 transaction and commit once at the
    end (D-12). On any validation failure, zero rows are written.
    """
    ticker = ticker.strip().upper()

    # D-14: ticker must be in the user's watchlist.
    hit = conn.execute(
        "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    if hit is None:
        raise UnknownTicker(f"Ticker {ticker} is not in the watchlist")

    # D-13: cache must have at least one tick.
    price = cache.get_price(ticker)
    if price is None:
        raise PriceUnavailable(f"No cached price for {ticker} yet")

    cash_row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?",
        (user_id,),
    ).fetchone()
    cash_balance = float(cash_row["cash_balance"])

    pos_row = conn.execute(
        "SELECT id, quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    old_qty = float(pos_row["quantity"]) if pos_row else 0.0
    old_avg = float(pos_row["avg_cost"]) if pos_row else 0.0

    gross = quantity * price

    if side == "buy":
        if gross > cash_balance:
            raise InsufficientCash(
                f"Need ${gross:.2f}, have ${cash_balance:.2f}"
            )
        new_qty = old_qty + quantity
        new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty if new_qty else 0.0
        new_cash = cash_balance - gross
    else:  # side == "sell"
        if quantity > old_qty + _ZERO_QTY_EPSILON:
            raise InsufficientShares(
                f"Requested {quantity}, held {old_qty}"
            )
        new_qty = old_qty - quantity
        new_avg = old_avg
        new_cash = cash_balance + gross

    now = datetime.now(UTC).isoformat()

    # Update cash.
    conn.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
        (new_cash, user_id),
    )

    # Upsert or delete the position row (D-15 epsilon delete).
    if abs(new_qty) < _ZERO_QTY_EPSILON:
        conn.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        pos_qty_out = 0.0
        pos_avg_out = 0.0
    elif pos_row is None:
        conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, ticker, new_qty, new_avg, now),
        )
        pos_qty_out = new_qty
        pos_avg_out = new_avg
    else:
        conn.execute(
            "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
            "WHERE user_id = ? AND ticker = ?",
            (new_qty, new_avg, now, user_id, ticker),
        )
        pos_qty_out = new_qty
        pos_avg_out = new_avg

    # Append trade row.
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, ticker, side, quantity, price, now),
    )

    # Record post-trade snapshot (PORT-05 immediate snapshot after each trade).
    total_value = _compute_total_value_with(conn, cache, new_cash, user_id)
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
        "VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, total_value, now),
    )

    conn.commit()

    logger.info(
        "Trade executed: %s %s x %.4f @ %.2f (cash=%.2f)",
        ticker,
        side,
        quantity,
        price,
        new_cash,
    )

    return TradeResponse(
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        cash_balance=new_cash,
        position_quantity=pos_qty_out,
        position_avg_cost=pos_avg_out,
        executed_at=now,
    )
