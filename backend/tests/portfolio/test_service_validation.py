"""Unit tests for execute_trade validation — domain exceptions with zero DB writes."""

from __future__ import annotations

import pytest

from app.portfolio import (
    InsufficientCash,
    InsufficientShares,
    PriceUnavailable,
    UnknownTicker,
    execute_trade,
)


def _db_counts(conn) -> tuple[float, int, int, int]:
    """Snapshot cash + row counts for positions, trades, portfolio_snapshots."""
    cash = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = 'default'"
    ).fetchone()["cash_balance"]
    pos = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    tr = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    snap = conn.execute("SELECT COUNT(*) FROM portfolio_snapshots").fetchone()[0]
    return cash, pos, tr, snap


class TestValidation:
    """Domain-exception rejection: zero DB writes on any validation failure."""

    def test_rejects_unknown_ticker_and_writes_nothing(self, fresh_db, warmed_cache):
        """ZZZZ is not in the watchlist: raises UnknownTicker, leaves DB unchanged."""
        before = _db_counts(fresh_db)

        with pytest.raises(UnknownTicker):
            execute_trade(fresh_db, warmed_cache, "ZZZZ", "buy", 1.0)

        assert _db_counts(fresh_db) == before

    def test_rejects_price_unavailable_and_writes_nothing(self, fresh_db, warmed_cache):
        """Cache miss for AAPL raises PriceUnavailable, leaves DB unchanged."""
        warmed_cache.remove("AAPL")
        before = _db_counts(fresh_db)

        with pytest.raises(PriceUnavailable):
            execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 1.0)

        assert _db_counts(fresh_db) == before

    def test_rejects_insufficient_cash_and_writes_nothing(self, fresh_db, warmed_cache):
        """Buying 1M AAPL raises InsufficientCash, leaves DB unchanged."""
        before = _db_counts(fresh_db)

        with pytest.raises(InsufficientCash):
            execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 1_000_000.0)

        assert _db_counts(fresh_db) == before

    def test_rejects_insufficient_shares_and_writes_nothing(self, fresh_db, warmed_cache):
        """Selling 10 AAPL with no position raises InsufficientShares, DB unchanged."""
        before = _db_counts(fresh_db)

        with pytest.raises(InsufficientShares):
            execute_trade(fresh_db, warmed_cache, "AAPL", "sell", 10.0)

        assert _db_counts(fresh_db) == before

    def test_insufficient_cash_message_contains_numbers(self, fresh_db, warmed_cache):
        """InsufficientCash message includes the cash_balance numeric with a dollar sign."""
        with pytest.raises(InsufficientCash) as exc_info:
            execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 1_000_000.0)
        msg = str(exc_info.value)
        assert "$" in msg
        assert "10000.00" in msg

    def test_insufficient_shares_message_contains_numbers(self, fresh_db, warmed_cache):
        """InsufficientShares message includes requested + held quantities."""
        with pytest.raises(InsufficientShares) as exc_info:
            execute_trade(fresh_db, warmed_cache, "AAPL", "sell", 10.0)
        msg = str(exc_info.value)
        assert "10" in msg
        assert "0" in msg
