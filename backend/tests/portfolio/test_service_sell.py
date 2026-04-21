"""Unit tests for execute_trade SELL path (Wave 0 stubs — filled in Task 3)."""

from __future__ import annotations

import pytest


class TestSell:
    """SELL path: partial/full decrement, epsilon-delete, writes."""

    def test_partial_sell_decrements_quantity(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 3")

    def test_partial_sell_leaves_avg_cost_unchanged(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 3")

    def test_full_sell_deletes_position_row(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 3")

    def test_full_sell_epsilon_handles_float_residual(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 3")

    def test_writes_snapshot_on_sell(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 3")

    def test_writes_trades_row_on_sell(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 3")
