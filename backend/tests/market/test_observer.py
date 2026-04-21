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
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
        counter = {"n": 0}

        def bump():
            counter["n"] += 1

        source.register_tick_observer(bump)
        await source.start(["AAPL"])
        await asyncio.sleep(0.3)
        await source.stop()
        assert counter["n"] >= 1

    async def test_multiple_observers_all_fire(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
        counter_a = {"n": 0}
        counter_b = {"n": 0}

        def bump_a():
            counter_a["n"] += 1

        def bump_b():
            counter_b["n"] += 1

        source.register_tick_observer(bump_a)
        source.register_tick_observer(bump_b)
        await source.start(["AAPL"])
        await asyncio.sleep(0.3)
        await source.stop()
        assert counter_a["n"] >= 1
        assert counter_b["n"] >= 1

    async def test_observer_exception_does_not_kill_loop(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
        counter = {"n": 0}

        def boom():
            raise RuntimeError("boom")

        def bump():
            counter["n"] += 1

        source.register_tick_observer(boom)
        source.register_tick_observer(bump)
        initial_version = cache.version
        await source.start(["AAPL"])
        await asyncio.sleep(0.3)
        await source.stop()
        assert cache.version > initial_version
        assert counter["n"] >= 1


@pytest.mark.asyncio
class TestMassive:
    """MassiveDataSource observer behavior (D-04, D-08)."""

    async def test_observer_fires_after_successful_poll(self):
        pytest.skip("Wave 0 stub - implemented in Task 4")

    async def test_observer_exception_isolation(self):
        pytest.skip("Wave 0 stub - implemented in Task 4")
