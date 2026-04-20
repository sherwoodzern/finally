"""Tests for default seed: users_profile + 10-ticker watchlist (DB-02)."""

import sqlite3

from app.db import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    get_watchlist_tickers,
    init_database,
    seed_defaults,
)
from app.market.seed_prices import SEED_PRICES


class TestSeed:
    """Unit tests for seed_defaults + get_watchlist_tickers."""

    def _fresh(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_database(conn)
        return conn

    def test_fresh_db_gets_seeded(self):
        """seed_defaults on an empty DB produces 1 users_profile + 10 watchlist rows."""
        conn = self._fresh()
        seed_defaults(conn)
        users = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        wl = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        assert users == 1
        assert wl == 10

    def test_cash_balance_defaults_to_10000(self):
        """Seeded users_profile row has id='default' and cash_balance=10000.0."""
        conn = self._fresh()
        seed_defaults(conn)
        row = conn.execute(
            "SELECT id, cash_balance FROM users_profile WHERE id = ?",
            (DEFAULT_USER_ID,),
        ).fetchone()
        assert row["id"] == "default"
        assert row["cash_balance"] == DEFAULT_CASH_BALANCE == 10000.0

    def test_watchlist_matches_seed_prices_keys(self):
        """Seeded watchlist tickers == set(SEED_PRICES.keys()) - D-04 single source of truth."""
        conn = self._fresh()
        seed_defaults(conn)
        tickers = get_watchlist_tickers(conn)
        assert set(tickers) == set(SEED_PRICES)
        assert len(tickers) == len(SEED_PRICES) == 10

    def test_reseed_is_noop(self):
        """Calling seed_defaults twice leaves counts unchanged and does not raise."""
        conn = self._fresh()
        seed_defaults(conn)
        seed_defaults(conn)  # Second call.
        users = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        wl = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        assert users == 1
        assert wl == 10

    def test_reseed_does_not_re_add_deleted_ticker(self):
        """COUNT(*) guard: if the user deletes a ticker, re-seed does NOT restore it.

        This is the forward-compatibility decision for when Phase 4 ships the
        watchlist API. The contract: seed only when the watchlist is fully empty.
        """
        conn = self._fresh()
        seed_defaults(conn)
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (DEFAULT_USER_ID, "NFLX"),
        )
        conn.commit()

        seed_defaults(conn)  # Should be a no-op on a non-empty watchlist.

        tickers = get_watchlist_tickers(conn)
        assert "NFLX" not in tickers
        assert len(tickers) == 9

    def test_get_watchlist_tickers_empty(self):
        """get_watchlist_tickers on an unseeded DB returns an empty list, not None."""
        conn = self._fresh()
        assert get_watchlist_tickers(conn) == []
