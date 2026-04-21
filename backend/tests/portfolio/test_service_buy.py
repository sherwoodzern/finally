"""Unit tests for execute_trade BUY path."""

from __future__ import annotations

from app.portfolio import execute_trade


class TestBuy:
    """BUY path: new positions, weighted average cost, fractional quantities, writes."""

    def test_first_buy_new_position(self, fresh_db, warmed_cache):
        """Buy 5 AAPL at 190: cash -950, positions row with qty=5, avg_cost=190."""
        cash_before = fresh_db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = 'default'"
        ).fetchone()["cash_balance"]

        result = execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)

        cash_after = fresh_db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = 'default'"
        ).fetchone()["cash_balance"]
        assert cash_after == cash_before - (5.0 * 190.0)

        pos = fresh_db.execute(
            "SELECT quantity, avg_cost FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
        ).fetchone()
        assert pos is not None
        assert pos["quantity"] == 5.0
        assert pos["avg_cost"] == 190.0

        assert result.ticker == "AAPL"
        assert result.price == 190.0
        assert result.position_quantity == 5.0
        assert result.position_avg_cost == 190.0

    def test_buy_adds_to_existing_position_weighted_avg_cost(self, fresh_db, warmed_cache):
        """Buy 10 at 190, then buy 5 at 200: avg_cost = (10*190 + 5*200) / 15."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 10.0)

        warmed_cache.update(ticker="AAPL", price=200.0)
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)

        pos = fresh_db.execute(
            "SELECT quantity, avg_cost FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
        ).fetchone()
        expected_avg = ((10.0 * 190.0) + (5.0 * 200.0)) / 15.0
        assert pos["quantity"] == 15.0
        assert abs(pos["avg_cost"] - expected_avg) < 1e-6

    def test_fractional_quantity(self, fresh_db, warmed_cache):
        """Buy 1.5 AAPL: positions row holds fractional quantity."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 1.5)

        pos = fresh_db.execute(
            "SELECT quantity FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
        ).fetchone()
        assert pos["quantity"] == 1.5

    def test_writes_snapshot(self, fresh_db, warmed_cache):
        """Each trade appends one portfolio_snapshots row with total_value = new_cash + position_value."""
        assert fresh_db.execute(
            "SELECT COUNT(*) FROM portfolio_snapshots"
        ).fetchone()[0] == 0

        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)

        rows = fresh_db.execute(
            "SELECT total_value FROM portfolio_snapshots"
        ).fetchall()
        assert len(rows) == 1
        # cash_after = 10000 - 5*190 = 9050; position_value = 5*190 = 950; total = 10000.
        assert abs(rows[0]["total_value"] - 10000.0) < 1e-6

    def test_writes_trades_row(self, fresh_db, warmed_cache):
        """Each trade appends one trades row with side='buy', quantity + price matching."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)

        rows = fresh_db.execute(
            "SELECT ticker, side, quantity, price FROM trades"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["ticker"] == "AAPL"
        assert rows[0]["side"] == "buy"
        assert rows[0]["quantity"] == 5.0
        assert rows[0]["price"] == 190.0

    def test_commits_once(self, fresh_db, warmed_cache):
        """All four writes (cash, positions, trades, snapshot) land under a single commit."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 3.0)

        cash = fresh_db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = 'default'"
        ).fetchone()["cash_balance"]
        pos_count = fresh_db.execute(
            "SELECT COUNT(*) FROM positions WHERE ticker = 'AAPL'"
        ).fetchone()[0]
        trade_count = fresh_db.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        snap_count = fresh_db.execute("SELECT COUNT(*) FROM portfolio_snapshots").fetchone()[0]

        assert cash == 10000.0 - (3.0 * 190.0)
        assert pos_count == 1
        assert trade_count == 1
        assert snap_count == 1
