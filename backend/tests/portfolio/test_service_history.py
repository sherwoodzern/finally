"""Unit tests for get_history — portfolio_snapshots read with ordering + limit."""

from __future__ import annotations

import uuid

from app.portfolio import get_history


def _insert_snapshot(conn, recorded_at: str, total_value: float = 10000.0) -> None:
    """Helper: insert one portfolio_snapshots row for the default user."""
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
        "VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), "default", total_value, recorded_at),
    )
    conn.commit()


class TestHistory:
    """portfolio_snapshots read: empty, ordering, limit."""

    def test_empty_history_returns_empty_list(self, fresh_db):
        """Fresh DB has zero portfolio_snapshots: returns HistoryResponse(snapshots=[])."""
        result = get_history(fresh_db)
        assert result.snapshots == []

    def test_history_ordered_by_recorded_at_asc(self, fresh_db):
        """Rows inserted out of order return sorted ascending by recorded_at."""
        _insert_snapshot(fresh_db, "2024-01-02T00:00:00+00:00", 10010.0)
        _insert_snapshot(fresh_db, "2024-01-01T00:00:00+00:00", 10000.0)
        _insert_snapshot(fresh_db, "2024-01-03T00:00:00+00:00", 10020.0)

        result = get_history(fresh_db)
        recorded = [s.recorded_at for s in result.snapshots]
        assert recorded == sorted(recorded)
        assert result.snapshots[0].recorded_at == "2024-01-01T00:00:00+00:00"
        assert result.snapshots[-1].recorded_at == "2024-01-03T00:00:00+00:00"

    def test_history_respects_limit_param(self, fresh_db):
        """limit=2 returns only the first two snapshots in ASC order."""
        for i in range(5):
            _insert_snapshot(
                fresh_db,
                f"2024-01-0{i + 1}T00:00:00+00:00",
                10000.0 + i,
            )

        result = get_history(fresh_db, limit=2)
        assert len(result.snapshots) == 2
        assert result.snapshots[0].recorded_at == "2024-01-01T00:00:00+00:00"
        assert result.snapshots[1].recorded_at == "2024-01-02T00:00:00+00:00"
