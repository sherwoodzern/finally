"""Unit tests for remove_ticker: delete + idempotent not_present invariants."""

from __future__ import annotations

from app.watchlist.service import RemoveResult, remove_ticker


def _count(conn, user_id: str = "default") -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


class TestRemoveTicker:
    def test_existing_ticker_deletes_row_and_returns_removed(self, fresh_db):
        before = _count(fresh_db)
        result = remove_ticker(fresh_db, "AAPL")
        assert result == RemoveResult(ticker="AAPL", status="removed")
        assert _count(fresh_db) == before - 1

        row = fresh_db.execute(
            "SELECT 1 FROM watchlist WHERE user_id = 'default' AND ticker = 'AAPL'"
        ).fetchone()
        assert row is None

    def test_missing_ticker_returns_not_present_without_error(self, fresh_db):
        """ZZZZ was never seeded; remove_ticker MUST NOT raise (SC#4, D-06)."""
        before = _count(fresh_db)
        result = remove_ticker(fresh_db, "ZZZZ")
        assert result == RemoveResult(ticker="ZZZZ", status="not_present")
        assert _count(fresh_db) == before

    def test_remove_then_remove_is_idempotent(self, fresh_db):
        remove_ticker(fresh_db, "AAPL")
        second = remove_ticker(fresh_db, "AAPL")
        assert second.status == "not_present"
