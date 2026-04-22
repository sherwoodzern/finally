"""Shared fixtures for chat service + route tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from app.chat import MockChatClient, StructuredResponse
from app.db import init_database, seed_defaults
from app.market import PriceCache
from app.market.seed_prices import SEED_PRICES


@pytest.fixture
def fresh_db() -> Iterator[sqlite3.Connection]:
    """Yield a seeded in-memory sqlite3.Connection with sqlite3.Row row factory."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    seed_defaults(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def warmed_cache() -> PriceCache:
    """Return a PriceCache pre-populated with seed prices for the 10 default tickers."""
    cache = PriceCache()
    for ticker, price in SEED_PRICES.items():
        cache.update(ticker=ticker, price=price)
    return cache


@pytest.fixture
def mock_chat_client() -> MockChatClient:
    """Return a fresh MockChatClient for per-test isolation (D-06)."""
    return MockChatClient()


class FakeChatClient:
    """Test double that returns a caller-specified StructuredResponse once.

    Used to force specific branches of the D-12 exception translation table
    without depending on the mock client's regex.
    """

    def __init__(self, response: StructuredResponse) -> None:
        self._response = response

    async def complete(self, messages: list[dict]) -> StructuredResponse:
        return self._response


class RaisingChatClient:
    """Test double whose .complete() raises a caller-specified exception.

    Used to verify the D-14 LLM-failure boundary (run_turn -> ChatTurnError) and
    D-18 persistence ordering (user row written before the LLM call).
    """

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    async def complete(self, messages: list[dict]) -> StructuredResponse:
        raise self._exc


class FakeSource:
    """In-memory MarketDataSource stand-in for service unit tests.

    Records every await on add_ticker / remove_ticker for later assertions
    without running a real GBM loop. Plan 03 integration tests exercise the
    real SimulatorDataSource via LifespanManager.
    """

    def __init__(self) -> None:
        self.added: list[str] = []
        self.removed: list[str] = []

    async def add_ticker(self, ticker: str) -> None:
        self.added.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self.removed.append(ticker)


@pytest.fixture
def fake_source() -> FakeSource:
    """Return a fresh FakeSource per test."""
    return FakeSource()
