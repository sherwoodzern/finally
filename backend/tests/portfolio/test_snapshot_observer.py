"""Tests for make_snapshot_observer + lifespan observer registration (PORT-05)."""

from __future__ import annotations

import pytest


class TestSnapshotObserver:
    """60s cadence, trade-reset clock, and observer exception isolation."""

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 3")
    def test_60s_threshold_writes_snapshot(self):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 3")
    def test_noop_under_threshold(self):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 3")
    def test_boot_time_initial_snapshot(self):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 3")
    def test_writes_recorded_at_iso_utc_string(self):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 3")
    @pytest.mark.asyncio
    async def test_trade_resets_clock(self, db_path):
        ...

    @pytest.mark.skip(reason="Wave 0 stub - implemented in Task 3")
    @pytest.mark.asyncio
    async def test_raising_observer_does_not_kill_tick_loop(self, db_path):
        ...
