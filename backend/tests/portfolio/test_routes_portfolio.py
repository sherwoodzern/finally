"""Integration tests for GET /api/portfolio (PORT-01)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestGetPortfolio:
    """HTTP contract for GET /api/portfolio."""

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_returns_seeded_cash_balance_and_empty_positions(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_current_price_falls_back_to_avg_cost_when_cache_empty(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_positions_ordered_by_ticker_asc(self, db_path):
        ...
