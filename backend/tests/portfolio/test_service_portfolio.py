"""Unit tests for get_portfolio + compute_total_value (Wave 0 stubs — filled in Task 4)."""

from __future__ import annotations

import pytest


class TestGetPortfolio:
    """get_portfolio response shape + cache-fallback behavior."""

    def test_empty_positions_returns_cash_only(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")

    def test_positions_use_cached_price(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")

    def test_positions_fall_back_to_avg_cost_when_cache_empty(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")

    def test_total_value_matches_compute_helper(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")


class TestComputeTotalValue:
    """compute_total_value standalone helper."""

    def test_compute_total_value_with_no_positions(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")

    def test_compute_total_value_with_mixed_cache_hits(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")
