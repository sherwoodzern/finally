"""Unit tests for get_portfolio + compute_total_value."""

from __future__ import annotations

from app.portfolio import compute_total_value, execute_trade, get_portfolio


class TestGetPortfolio:
    """get_portfolio response shape + cache-fallback behavior."""

    def test_empty_positions_returns_cash_only(self, fresh_db, warmed_cache):
        """No positions: cash=10000, total_value=10000, positions=[]."""
        result = get_portfolio(fresh_db, warmed_cache)
        assert result.cash_balance == 10000.0
        assert result.total_value == 10000.0
        assert result.positions == []

    def test_positions_use_cached_price(self, fresh_db, warmed_cache):
        """Buy 5 AAPL at 190, cache ticks to 200: unrealized_pnl = (200-190)*5 = 50."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)
        warmed_cache.update(ticker="AAPL", price=200.0)

        result = get_portfolio(fresh_db, warmed_cache)
        assert len(result.positions) == 1
        pos = result.positions[0]
        assert pos.ticker == "AAPL"
        assert pos.current_price == 200.0
        assert pos.unrealized_pnl == 50.0

    def test_positions_fall_back_to_avg_cost_when_cache_empty(self, fresh_db, warmed_cache):
        """Buy 5 AAPL, remove from cache: current_price falls back to avg_cost, pnl=0."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)
        warmed_cache.remove("AAPL")

        result = get_portfolio(fresh_db, warmed_cache)
        pos = result.positions[0]
        assert pos.current_price == 190.0
        assert pos.unrealized_pnl == 0.0
        assert pos.change_percent == 0.0

    def test_total_value_matches_compute_helper(self, fresh_db, warmed_cache):
        """After a trade, get_portfolio.total_value equals round(compute_total_value, 2)."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)
        warmed_cache.update(ticker="AAPL", price=210.0)

        result = get_portfolio(fresh_db, warmed_cache)
        assert result.total_value == round(compute_total_value(fresh_db, warmed_cache), 2)


class TestComputeTotalValue:
    """compute_total_value standalone helper."""

    def test_compute_total_value_with_no_positions(self, fresh_db, warmed_cache):
        """No positions: total == cash == 10000.0."""
        assert compute_total_value(fresh_db, warmed_cache) == 10000.0

    def test_compute_total_value_with_mixed_cache_hits(self, fresh_db, warmed_cache):
        """AAPL in cache, GOOGL removed: total = cash + 5*AAPL_price + 2*GOOGL_avg_cost."""
        execute_trade(fresh_db, warmed_cache, "AAPL", "buy", 5.0)
        execute_trade(fresh_db, warmed_cache, "GOOGL", "buy", 2.0)

        # GOOGL seeded at 175.0 (its avg_cost); AAPL seeded at 190 (its avg_cost).
        warmed_cache.update(ticker="AAPL", price=220.0)
        warmed_cache.remove("GOOGL")

        cash = fresh_db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = 'default'"
        ).fetchone()["cash_balance"]

        # Expected: cash + 5*220 (AAPL cached) + 2*175 (GOOGL fallback to avg_cost)
        expected = cash + (5 * 220.0) + (2 * 175.0)
        assert abs(compute_total_value(fresh_db, warmed_cache) - expected) < 1e-6
