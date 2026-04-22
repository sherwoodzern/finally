"""Unit tests for app.chat.service.run_turn - happy path + watchlist-first + no-op."""

from __future__ import annotations

from app.chat import MockChatClient
from app.chat.service import run_turn
from tests.chat.conftest import FakeSource


def _count_chat_messages(conn, user_id: str = "default") -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM chat_messages WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0]


def _get_cash(conn) -> float:
    row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = 'default'"
    ).fetchone()
    return float(row["cash_balance"])


def _watchlist_has(conn, ticker: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM watchlist WHERE user_id = 'default' AND ticker = ?",
        (ticker,),
    ).fetchone()
    return row is not None


class TestRunTurnHappyPath:
    async def test_buy_aapl_10(self, fresh_db, warmed_cache, fake_source):
        """MockChatClient 'buy AAPL 10' -> 1 executed trade, cash down, 2 chat rows."""
        client = MockChatClient()
        cash_before = _get_cash(fresh_db)

        response = await run_turn(
            fresh_db, warmed_cache, fake_source, client, "buy AAPL 10"
        )

        assert len(response.trades) == 1
        assert response.trades[0].status == "executed"
        assert response.trades[0].ticker == "AAPL"
        assert response.trades[0].side == "buy"
        assert response.trades[0].quantity == 10.0
        assert response.trades[0].price is not None
        assert response.trades[0].cash_balance is not None
        assert response.trades[0].cash_balance < cash_before
        assert response.watchlist_changes == []
        assert _count_chat_messages(fresh_db) == 2

    async def test_no_match_still_persists_two_rows(
        self, fresh_db, warmed_cache, fake_source
    ):
        """'hello' -> empty trades+watchlist; 2 chat rows still written."""
        client = MockChatClient()

        response = await run_turn(
            fresh_db, warmed_cache, fake_source, client, "hello"
        )

        assert response.trades == []
        assert response.watchlist_changes == []
        assert response.message == "mock response"
        assert _count_chat_messages(fresh_db) == 2


class TestRunTurnWatchlistFirst:
    async def test_add_then_buy_same_turn_cold_cache(
        self, fresh_db, warmed_cache, fake_source
    ):
        """'add PYPL and buy PYPL 10' -> watchlist added first; trade fails with price_unavailable (D-09, D-11)."""
        client = MockChatClient()

        response = await run_turn(
            fresh_db, warmed_cache, fake_source, client, "add PYPL and buy PYPL 10"
        )

        # Watchlist ran first
        assert len(response.watchlist_changes) == 1
        assert response.watchlist_changes[0].ticker == "PYPL"
        assert response.watchlist_changes[0].status == "added"
        # Trade ran AFTER watchlist and failed because cache had no PYPL tick
        assert len(response.trades) == 1
        assert response.trades[0].ticker == "PYPL"
        assert response.trades[0].status == "failed"
        assert response.trades[0].error == "price_unavailable"
        # Source saw the add
        assert "PYPL" in fake_source.added
        # Watchlist row exists
        assert _watchlist_has(fresh_db, "PYPL")


class TestRunTurnSourceFailureAfterAdd:
    async def test_source_add_raises_does_not_downgrade_watchlist_result(
        self, fresh_db, warmed_cache
    ):
        """Mirror watchlist/routes.py:55-64: DB-committed; source.add raise logs WARNING but status stays 'added'."""
        from tests.chat.conftest import FakeSource

        class BoomSource(FakeSource):
            async def add_ticker(self, ticker: str) -> None:
                raise RuntimeError("source exploded")

        client = MockChatClient()
        response = await run_turn(
            fresh_db, warmed_cache, BoomSource(), client, "add PYPL"
        )
        assert response.watchlist_changes[0].status == "added"  # DB wins
        assert _watchlist_has(fresh_db, "PYPL")
