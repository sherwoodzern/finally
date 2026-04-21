"""Tests for MarketDataSource.register_tick_observer (D-04, D-08)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.market import MarketDataSource, PriceCache
from app.market.massive_client import MassiveDataSource
from app.market.simulator import SimulatorDataSource


class TestABC:
    """ABC-level contract: register_tick_observer is abstract."""

    def test_register_tick_observer_is_abstract(self):
        class Incomplete(MarketDataSource):
            async def start(self, tickers):
                pass

            async def stop(self):
                pass

            async def add_ticker(self, ticker):
                pass

            async def remove_ticker(self, ticker):
                pass

            def get_tickers(self):
                return []

        with pytest.raises(TypeError):
            Incomplete()


@pytest.mark.asyncio
class TestSimulator:
    """SimulatorDataSource observer behavior (D-04, D-08)."""

    async def test_observer_fires_on_tick(self):
        pytest.skip("Wave 0 stub - implemented in Task 3")

    async def test_multiple_observers_all_fire(self):
        pytest.skip("Wave 0 stub - implemented in Task 3")

    async def test_observer_exception_does_not_kill_loop(self):
        pytest.skip("Wave 0 stub - implemented in Task 3")


@pytest.mark.asyncio
class TestMassive:
    """MassiveDataSource observer behavior (D-04, D-08)."""

    async def test_observer_fires_after_successful_poll(self):
        pytest.skip("Wave 0 stub - implemented in Task 4")

    async def test_observer_exception_isolation(self):
        pytest.skip("Wave 0 stub - implemented in Task 4")
