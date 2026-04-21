"""Unit tests for execute_trade SELL path."""

from __future__ import annotations

from app.portfolio import execute_trade


class TestSell:
    """SELL path: partial/full decrement, epsilon-delete, writes."""

    def test_partial_sell_decrements_quantity(self, fresh_db, warmed_cache):
        """Buy 10, sell 3: positions.quantity == 7."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 10.0)
        execute_trade(fresh_db, warmed_cache, "AAPL", "sell", 3.0)

        pos = fresh_db.execute(
            "SELECT quantity FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
        ).fetchone()
        assert pos["quantity"] == 7.0

    def test_partial_sell_leaves_avg_cost_unchanged(self, fresh_db, warmed_cache):
        """Buy 10 at 190, mutate cache to 200, sell 3: avg_cost still 190 (D-16)."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 10.0)

        warmed_cache.update(ticker="AAPL", price=200.0)
        execute_trade(fresh_db, warmed_cache, "AAPL", "sell", 3.0)

        pos = fresh_db.execute(
            "SELECT avg_cost FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
        ).fetchone()
        assert pos["avg_cost"] == 190.0

    def test_full_sell_deletes_position_row(self, fresh_db, warmed_cache):
        """Buy 10, sell 10: positions row is deleted (D-15)."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 10.0)
        execute_trade(fresh_db, warmed_cache, "AAPL", "sell", 10.0)

        count = fresh_db.execute(
            "SELECT COUNT(*) FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
        ).fetchone()[0]
        assert count == 0

    def test_full_sell_epsilon_handles_float_residual(self, fresh_db, warmed_cache):
        """Buy 0.1 + 0.2 (IEEE 754 residual), sell 0.3: position row deleted."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 0.1)
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 0.2)
        execute_trade(fresh_db, warmed_cache, "AAPL", "sell", 0.3)

        count = fresh_db.execute(
            "SELECT COUNT(*) FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
        ).fetchone()[0]
        assert count == 0

    def test_writes_snapshot_on_sell(self, fresh_db, warmed_cache):
        """Each sell appends a portfolio_snapshots row."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)
        count_before = fresh_db.execute(
            "SELECT COUNT(*) FROM portfolio_snapshots"
        ).fetchone()[0]

        execute_trade(fresh_db, warmed_cache, "AAPL", "sell", 2.0)

        count_after = fresh_db.execute(
            "SELECT COUNT(*) FROM portfolio_snapshots"
        ).fetchone()[0]
        assert count_after == count_before + 1

    def test_writes_trades_row_on_sell(self, fresh_db, warmed_cache):
        """Each sell appends one trades row with side='sell'."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)
        execute_trade(fresh_db, warmed_cache, "AAPL", "sell", 2.0)

        rows = fresh_db.execute(
            "SELECT side, quantity FROM trades WHERE ticker = 'AAPL' ORDER BY executed_at"
        ).fetchall()
        assert len(rows) == 2
        assert rows[1]["side"] == "sell"
        assert rows[1]["quantity"] == 2.0
