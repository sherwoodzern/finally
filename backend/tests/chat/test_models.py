"""Unit tests for app.chat.models (Pydantic v2 schemas + StructuredResponse)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.chat.models import (
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    StructuredResponse,
    TradeAction,
    TradeActionResult,
    WatchlistAction,
    WatchlistActionResult,
)


class TestStructuredResponse:
    def test_parses_full_plan_md_schema(self):
        raw = (
            '{"message":"hi","trades":[{"ticker":"AAPL","side":"buy","quantity":10}],'
            '"watchlist_changes":[{"ticker":"PYPL","action":"add"}]}'
        )
        m = StructuredResponse.model_validate_json(raw)
        assert m.message == "hi"
        assert m.trades[0].ticker == "AAPL"
        assert m.watchlist_changes[0].ticker == "PYPL"

    def test_defaults_lists_to_empty(self):
        m = StructuredResponse.model_validate_json('{"message":"ok"}')
        assert m.trades == []
        assert m.watchlist_changes == []

    def test_rejects_extra_keys(self):
        with pytest.raises(ValidationError):
            StructuredResponse.model_validate_json(
                '{"message":"ok","bogus":1}'
            )

    def test_rejects_missing_message(self):
        with pytest.raises(ValidationError):
            StructuredResponse.model_validate_json('{}')


class TestTradeAction:
    def test_normalizes_ticker(self):
        t = TradeAction(ticker="  aapl ", side="buy", quantity=1)
        assert t.ticker == "AAPL"

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="buy", quantity=0)

    def test_rejects_bad_side(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="short", quantity=1)

    def test_rejects_extra_keys(self):
        with pytest.raises(ValidationError):
            TradeAction(
                ticker="AAPL", side="buy", quantity=1, extra=True
            )  # type: ignore[call-arg]


class TestWatchlistAction:
    def test_normalizes_ticker(self):
        w = WatchlistAction(ticker="pypl", action="add")
        assert w.ticker == "PYPL"

    def test_rejects_bad_action(self):
        with pytest.raises(ValidationError):
            WatchlistAction(ticker="PYPL", action="maybe")  # type: ignore[arg-type]

    def test_rejects_extra_keys(self):
        with pytest.raises(ValidationError):
            WatchlistAction(
                ticker="PYPL", action="add", bogus=1
            )  # type: ignore[call-arg]


class TestChatRequest:
    def test_rejects_empty_message(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_rejects_extra_keys(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="hi", bogus=1)  # type: ignore[call-arg]

    def test_enforces_max_length(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 8193)


class TestResults:
    def test_trade_action_result_executed_shape(self):
        r = TradeActionResult(
            ticker="AAPL", side="buy", quantity=10,
            status="executed", price=191.2, cash_balance=8087.8,
            executed_at="2026-04-21T00:00:00+00:00",
        )
        assert r.status == "executed"

    def test_trade_action_result_failed_shape(self):
        r = TradeActionResult(
            ticker="AAPL", side="buy", quantity=10,
            status="failed", error="insufficient_cash",
            message="Need $... have $...",
        )
        assert r.status == "failed"
        assert r.error == "insufficient_cash"

    def test_watchlist_action_result_all_statuses(self):
        for s in ("added", "exists", "removed", "not_present", "failed"):
            r = WatchlistActionResult(ticker="PYPL", action="add", status=s)  # type: ignore[arg-type]
            assert r.status == s


class TestChatResponse:
    def test_requires_lists_present_even_empty(self):
        r = ChatResponse(message="ok", trades=[], watchlist_changes=[])
        dumped = r.model_dump()
        assert dumped["trades"] == []
        assert dumped["watchlist_changes"] == []


class TestChatMessageOut:
    def test_accepts_dict_actions(self):
        m = ChatMessageOut(
            id="abc", role="assistant", content="hi",
            actions={"trades": [], "watchlist_changes": []},
            created_at="2026-04-21T00:00:00+00:00",
        )
        assert m.actions == {"trades": [], "watchlist_changes": []}

    def test_accepts_none_actions_for_user(self):
        m = ChatMessageOut(
            id="abc", role="user", content="hi",
            actions=None,
            created_at="2026-04-21T00:00:00+00:00",
        )
        assert m.actions is None


class TestHistoryResponse:
    def test_wraps_list(self):
        h = HistoryResponse(messages=[])
        assert h.messages == []
