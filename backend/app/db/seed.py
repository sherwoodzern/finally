"""Idempotent seed for users_profile + 10-ticker default watchlist."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import UTC, datetime

from app.db.schema import SCHEMA_STATEMENTS
from app.market.seed_prices import SEED_PRICES

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0


def init_database(conn: sqlite3.Connection) -> None:
    """Create all six PLAN.md section 7 tables if they don't exist. Idempotent (DB-01)."""
    for ddl in SCHEMA_STATEMENTS:
        conn.execute(ddl)
    conn.commit()


def seed_defaults(conn: sqlite3.Connection) -> None:
    """Insert the default user row and 10-ticker watchlist when missing (DB-02).

    users_profile uses INSERT OR IGNORE keyed on the primary key `id='default'` -
    safe to call on every boot.

    watchlist uses a `COUNT(*) = 0` guard (not INSERT OR IGNORE) so that once
    Phase 4 ships the watchlist API, a user-deleted ticker is NOT silently
    re-inserted on the next restart. Fresh volumes get the 10 defaults; any
    non-empty watchlist is left untouched.
    """
    now = datetime.now(UTC).isoformat()

    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) "
        "VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )

    existing = conn.execute(
        "SELECT COUNT(*) FROM watchlist WHERE user_id = ?",
        (DEFAULT_USER_ID,),
    ).fetchone()[0]

    if existing == 0:
        for ticker in SEED_PRICES:
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) "
                "VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now),
            )
        logger.info("Seeded default watchlist with %d tickers", len(SEED_PRICES))

    conn.commit()


def get_watchlist_tickers(conn: sqlite3.Connection) -> list[str]:
    """Return watchlist tickers for the default user (D-05).

    Used by the lifespan to drive `source.start(tickers)` in place of
    `list(SEED_PRICES.keys())`. Ordered by `added_at, ticker` for determinism -
    seed rows all share one `added_at`, so `ticker` is the stable tiebreaker.
    """
    rows = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, ticker",
        (DEFAULT_USER_ID,),
    ).fetchall()
    return [row["ticker"] for row in rows]
