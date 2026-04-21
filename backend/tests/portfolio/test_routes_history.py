"""Integration tests for GET /api/portfolio/history (PORT-04)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestGetHistory:
    """HTTP contract for GET /api/portfolio/history."""

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_empty_history_on_fresh_db(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_snapshots_ordered_asc(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 2")
    async def test_limit_param(self, db_path):
        ...
