"""Integration tests for POST /api/portfolio/trade (PORT-02, PORT-03)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestBuy:
    """Happy-path BUY contract."""

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_buy_happy_path(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_buy_fractional(self, db_path):
        ...


@pytest.mark.asyncio
class TestSell:
    """SELL behavior: avg_cost preservation + full-sell row delete."""

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_partial_sell_keeps_avg_cost(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_full_sell_deletes_row(self, db_path):
        ...


@pytest.mark.asyncio
class TestErrors:
    """400 errors for the four domain exceptions."""

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_insufficient_cash(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_insufficient_shares(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_unknown_ticker(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_price_unavailable(self, db_path):
        ...


@pytest.mark.asyncio
class TestSchema:
    """Pydantic 422 rejections for malformed bodies."""

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_rejects_malformed_body(self, db_path):
        ...
