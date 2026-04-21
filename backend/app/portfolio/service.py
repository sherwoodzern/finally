"""Pure-function service: trade execution, portfolio valuation, history, snapshot observer."""

from __future__ import annotations

import logging
import sqlite3
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from app.market import PriceCache

from .models import (
    HistoryResponse,
    PortfolioResponse,
    PositionOut,
    SnapshotOut,
    TradeResponse,
)

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


def compute_total_value(
    conn: sqlite3.Connection,
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
) -> float:
    """Return cash + sum(qty * current_or_avg). Shared by get_portfolio + snapshot observer."""
    cash_row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?",
        (user_id,),
    ).fetchone()
    cash = float(cash_row["cash_balance"]) if cash_row else 0.0
    return _compute_total_value_with(conn, cache, cash, user_id)


def get_portfolio(
    conn: sqlite3.Connection,
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
) -> PortfolioResponse:
    """Return cash, total_value, and positions with live prices falling back to avg_cost."""
    cash_row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?",
        (user_id,),
    ).fetchone()
    cash = float(cash_row["cash_balance"]) if cash_row else 0.0

    rows = conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? "
        "ORDER BY ticker ASC",
        (user_id,),
    ).fetchall()

    positions: list[PositionOut] = []
    total = cash
    for row in rows:
        ticker = row["ticker"]
        qty = float(row["quantity"])
        avg = float(row["avg_cost"])
        cached = cache.get_price(ticker)
        current = cached if cached is not None else avg
        pnl = (current - avg) * qty
        pct = ((current - avg) / avg * 100.0) if avg != 0.0 else 0.0
        total += qty * current
        positions.append(
            PositionOut(
                ticker=ticker,
                quantity=qty,
                avg_cost=avg,
                current_price=current,
                unrealized_pnl=round(pnl, 2),
                change_percent=round(pct, 2),
            )
        )

    return PortfolioResponse(
        cash_balance=cash,
        total_value=round(total, 2),
        positions=positions,
    )


def get_history(
    conn: sqlite3.Connection,
    limit: int | None = None,
    user_id: str = DEFAULT_USER_ID,
) -> HistoryResponse:
    """Return portfolio_snapshots for user_id, ORDER BY recorded_at ASC."""
    if limit is None:
        rows = conn.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at ASC",
            (user_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at ASC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    snaps = [
        SnapshotOut(total_value=float(r["total_value"]), recorded_at=r["recorded_at"])
        for r in rows
    ]
    return HistoryResponse(snapshots=snaps)


def make_snapshot_observer(state) -> Callable[[], None]:
    """Return a zero-arg tick observer that writes a snapshot every 60s (D-05, D-06, D-07).

    Closes over `state` (FastAPI app.state) with:
        - state.db:                sqlite3.Connection
        - state.price_cache:       PriceCache
        - state.last_snapshot_at:  float (monotonic clock)

    Uses time.monotonic() for the 60s threshold; datetime.now(UTC).isoformat() for
    the recorded_at column (Pitfall 6).
    """

    def observer() -> None:
        now = time.monotonic()
        if now - state.last_snapshot_at < 60.0:
            return
        total_value = compute_total_value(state.db, state.price_cache)
        state.db.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                DEFAULT_USER_ID,
                total_value,
                datetime.now(UTC).isoformat(),
            ),
        )
        state.db.commit()
        state.last_snapshot_at = now

    return observer
