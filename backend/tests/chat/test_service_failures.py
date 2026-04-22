"""Unit tests for app.chat.service auto-exec failure translation (D-12) + ChatTurnError."""

from __future__ import annotations

import pytest

from app.chat import StructuredResponse, TradeAction, WatchlistAction
from app.chat.service import ChatTurnError, run_turn
from tests.chat.conftest import FakeChatClient, RaisingChatClient


def _db_counts(conn) -> tuple[float, int, int]:
    cash = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = 'default'"
    ).fetchone()["cash_balance"]
    positions = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    trades = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    return cash, positions, trades


class TestAutoExecFailureTranslation:
    async def test_insufficient_cash(self, fresh_db, warmed_cache, fake_source):
        """Buy 100000 AAPL -> status='failed', error='insufficient_cash'. DB unchanged."""
        client = FakeChatClient(
            StructuredResponse(
                message="ok",
                trades=[TradeAction(ticker="AAPL", side="buy", quantity=100000)],
            )
        )
        before = _db_counts(fresh_db)
        response = await run_turn(fresh_db, warmed_cache, fake_source, client, "x")
        assert response.trades[0].status == "failed"
        assert response.trades[0].error == "insufficient_cash"
        assert _db_counts(fresh_db) == before

    async def test_insufficient_shares(self, fresh_db, warmed_cache, fake_source):
        """Sell 10 AAPL with no position -> error='insufficient_shares'."""
        client = FakeChatClient(
            StructuredResponse(
                message="ok",
                trades=[TradeAction(ticker="AAPL", side="sell", quantity=10)],
            )
        )
        response = await run_turn(fresh_db, warmed_cache, fake_source, client, "x")
        assert response.trades[0].status == "failed"
        assert response.trades[0].error == "insufficient_shares"

    async def test_unknown_ticker(self, fresh_db, warmed_cache, fake_source):
        """Trade a ticker not in watchlist -> error='unknown_ticker'."""
        client = FakeChatClient(
            StructuredResponse(
                message="ok",
                trades=[TradeAction(ticker="XYZ", side="buy", quantity=1)],
            )
        )
        response = await run_turn(fresh_db, warmed_cache, fake_source, client, "x")
        assert response.trades[0].status == "failed"
        assert response.trades[0].error == "unknown_ticker"

    async def test_price_unavailable(self, fresh_db, warmed_cache, fake_source):
        """Cache miss for AAPL -> error='price_unavailable'."""
        warmed_cache.remove("AAPL")
        client = FakeChatClient(
            StructuredResponse(
                message="ok",
                trades=[TradeAction(ticker="AAPL", side="buy", quantity=1)],
            )
        )
        response = await run_turn(fresh_db, warmed_cache, fake_source, client, "x")
        assert response.trades[0].status == "failed"
        assert response.trades[0].error == "price_unavailable"


class TestContinueOnFailure:
    async def test_mid_list_failure_does_not_abort(
        self, fresh_db, warmed_cache, fake_source
    ):
        """[BAD buy, GOOD buy] -> one failed + one executed; loop did NOT abort (D-10)."""
        client = FakeChatClient(
            StructuredResponse(
                message="ok",
                trades=[
                    TradeAction(ticker="AAPL", side="buy", quantity=100000),  # insufficient_cash
                    TradeAction(ticker="MSFT", side="buy", quantity=1),        # ok
                ],
            )
        )
        response = await run_turn(fresh_db, warmed_cache, fake_source, client, "x")
        assert len(response.trades) == 2
        statuses = [t.status for t in response.trades]
        assert "failed" in statuses
        assert "executed" in statuses


class TestWatchlistFirst:
    async def test_watchlist_runs_before_trades(
        self, fresh_db, warmed_cache, fake_source
    ):
        """Watchlist-add for ticker not in watchlist, then trade for the same ticker -> both ran in order (D-09)."""
        client = FakeChatClient(
            StructuredResponse(
                message="ok",
                trades=[TradeAction(ticker="PYPL", side="buy", quantity=1)],
                watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
            )
        )
        response = await run_turn(fresh_db, warmed_cache, fake_source, client, "x")
        # Watchlist succeeded (happened first)
        assert response.watchlist_changes[0].status == "added"
        # Trade failed with price_unavailable (ran AFTER add, but cache still cold)
        assert response.trades[0].status == "failed"
        assert response.trades[0].error == "price_unavailable"


class TestInternalErrorFallback:
    async def test_unexpected_exception_becomes_internal_error(
        self, fresh_db, warmed_cache, fake_source, monkeypatch, caplog
    ):
        """Any other Exception during auto-exec -> status='failed', error='internal_error', WARNING logged."""
        import logging

        import app.chat.service as svc

        def _boom(*args, **kwargs):
            raise KeyError("boom")

        monkeypatch.setattr(svc, "execute_trade", _boom)

        client = FakeChatClient(
            StructuredResponse(
                message="ok",
                trades=[TradeAction(ticker="AAPL", side="buy", quantity=1)],
            )
        )
        with caplog.at_level(logging.WARNING):
            response = await run_turn(
                fresh_db, warmed_cache, fake_source, client, "x"
            )
        assert response.trades[0].status == "failed"
        assert response.trades[0].error == "internal_error"
        assert any("unexpected" in rec.message.lower() for rec in caplog.records)


class TestChatTurnErrorBoundary:
    async def test_llm_raise_becomes_chat_turn_error(
        self, fresh_db, warmed_cache, fake_source
    ):
        """client.complete() raising -> run_turn raises ChatTurnError (D-14)."""
        client = RaisingChatClient(RuntimeError("connection refused"))
        with pytest.raises(ChatTurnError) as exc_info:
            await run_turn(fresh_db, warmed_cache, fake_source, client, "x")
        assert "connection refused" in str(exc_info.value)
