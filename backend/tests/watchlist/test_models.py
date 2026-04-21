"""Unit tests for normalize_ticker and WatchlistAddRequest validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.watchlist.models import (
    WatchlistAddRequest,
    WatchlistMutationResponse,
    normalize_ticker,
)


class TestNormalizeTicker:
    def test_strips_and_uppercases(self):
        assert normalize_ticker("  aapl  ") == "AAPL"

    def test_accepts_dotted_class(self):
        assert normalize_ticker("brk.b") == "BRK.B"

    def test_accepts_ten_char_cap(self):
        assert normalize_ticker("abcdefghij") == "ABCDEFGHIJ"

    def test_rejects_leading_digit(self):
        with pytest.raises(ValueError, match="invalid ticker"):
            normalize_ticker("1X")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="invalid ticker"):
            normalize_ticker("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="invalid ticker"):
            normalize_ticker("   ")

    def test_rejects_special_chars(self):
        with pytest.raises(ValueError, match="invalid ticker"):
            normalize_ticker("AAPL!")

    def test_rejects_over_ten_chars(self):
        with pytest.raises(ValueError, match="invalid ticker"):
            normalize_ticker("ABCDEFGHIJK")


class TestWatchlistAddRequest:
    def test_normalizes_on_construction(self):
        req = WatchlistAddRequest(ticker="  aapl  ")
        assert req.ticker == "AAPL"

    def test_rejects_extra_keys(self):
        with pytest.raises(ValidationError):
            WatchlistAddRequest(ticker="AAPL", extra="x")

    def test_rejects_invalid_ticker(self):
        with pytest.raises(ValidationError):
            WatchlistAddRequest(ticker="1X")

    def test_rejects_missing_ticker(self):
        with pytest.raises(ValidationError):
            WatchlistAddRequest()


class TestWatchlistMutationResponse:
    @pytest.mark.parametrize("status", ["added", "exists", "removed", "not_present"])
    def test_accepts_all_four_statuses(self, status):
        resp = WatchlistMutationResponse(ticker="AAPL", status=status)
        assert resp.status == status

    def test_rejects_unknown_status(self):
        with pytest.raises(ValidationError):
            WatchlistMutationResponse(ticker="AAPL", status="pending")
