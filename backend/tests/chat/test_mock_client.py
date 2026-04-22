"""Unit tests for app.chat.mock.MockChatClient keyword regex map (D-06)."""

from __future__ import annotations

from app.chat.mock import MockChatClient


def _last_user(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


class TestBuyPattern:
    async def test_simple_buy(self):
        result = await MockChatClient().complete(_last_user("buy AAPL 10"))
        assert len(result.trades) == 1
        assert result.trades[0].ticker == "AAPL"
        assert result.trades[0].side == "buy"
        assert result.trades[0].quantity == 10.0

    async def test_buy_fractional(self):
        result = await MockChatClient().complete(_last_user("buy AAPL 0.5"))
        assert result.trades[0].quantity == 0.5

    async def test_buyout_is_not_a_buy(self):
        """Word-boundary anchoring prevents 'buyout AAPL' from matching (Pitfall 7)."""
        result = await MockChatClient().complete(_last_user("buyout AAPL 10"))
        assert result.trades == []


class TestSellPattern:
    async def test_simple_sell(self):
        result = await MockChatClient().complete(_last_user("sell TSLA 5"))
        assert len(result.trades) == 1
        assert result.trades[0].side == "sell"


class TestAddRemovePattern:
    async def test_add(self):
        result = await MockChatClient().complete(_last_user("add PYPL"))
        assert len(result.watchlist_changes) == 1
        assert result.watchlist_changes[0].action == "add"
        assert result.watchlist_changes[0].ticker == "PYPL"

    async def test_remove(self):
        result = await MockChatClient().complete(_last_user("remove PYPL"))
        assert result.watchlist_changes[0].action == "remove"

    async def test_drop_alias(self):
        result = await MockChatClient().complete(_last_user("drop PYPL"))
        assert result.watchlist_changes[0].action == "remove"


class TestCombinations:
    async def test_add_and_buy(self):
        result = await MockChatClient().complete(
            _last_user("add PYPL and buy PYPL 10")
        )
        assert len(result.watchlist_changes) == 1
        assert len(result.trades) == 1


class TestNoMatch:
    async def test_hello(self):
        result = await MockChatClient().complete(_last_user("hello"))
        assert result.message == "mock response"
        assert result.trades == []
        assert result.watchlist_changes == []


class TestCaseInsensitive:
    async def test_uppercase_command(self):
        result = await MockChatClient().complete(_last_user("BUY AAPL 5"))
        assert len(result.trades) == 1


class TestLastUserMessage:
    async def test_uses_last_user_over_assistant(self):
        """Mock reads the LAST user message, ignoring earlier turns / assistant rows."""
        messages = [
            {"role": "user", "content": "buy AAPL 1"},
            {"role": "assistant", "content": "done"},
            {"role": "user", "content": "sell TSLA 2"},
        ]
        result = await MockChatClient().complete(messages)
        assert len(result.trades) == 1
        assert result.trades[0].side == "sell"
        assert result.trades[0].ticker == "TSLA"


class TestDeterministicMessage:
    async def test_mock_message_format(self):
        result = await MockChatClient().complete(_last_user("buy AAPL 10"))
        assert result.message.startswith("Mock: executing")
        assert "buy" in result.message.lower()
        assert "AAPL" in result.message
