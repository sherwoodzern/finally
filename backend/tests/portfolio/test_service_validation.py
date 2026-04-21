"""Unit tests for execute_trade validation (Wave 0 stubs — filled in Task 4)."""

from __future__ import annotations

import pytest


class TestValidation:
    """Domain-exception rejection: zero DB writes on any validation failure."""

    def test_rejects_unknown_ticker_and_writes_nothing(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")

    def test_rejects_price_unavailable_and_writes_nothing(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")

    def test_rejects_insufficient_cash_and_writes_nothing(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")

    def test_rejects_insufficient_shares_and_writes_nothing(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")

    def test_insufficient_cash_message_contains_numbers(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")

    def test_insufficient_shares_message_contains_numbers(self, fresh_db, warmed_cache):
        pytest.skip("Wave 0 stub — filled in Task 4")
