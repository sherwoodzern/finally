"""Unit tests for app.chat.prompts: SYSTEM_PROMPT, build_portfolio_context, build_messages."""

from __future__ import annotations

import json
import uuid

from app.chat.prompts import (
    CHAT_HISTORY_WINDOW,
    DEFAULT_USER_ID,
    SYSTEM_PROMPT,
    build_messages,
    build_portfolio_context,
)


def _insert_chat_row(conn, role: str, content: str, created_at: str) -> None:
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, NULL, ?)",
        (str(uuid.uuid4()), "default", role, content, created_at),
    )
    conn.commit()


class TestConstants:
    def test_system_prompt_is_non_empty(self):
        assert isinstance(SYSTEM_PROMPT, str)
        assert "FinAlly" in SYSTEM_PROMPT
        assert "AI trading assistant" in SYSTEM_PROMPT.lower() or "trading" in SYSTEM_PROMPT.lower()

    def test_history_window_is_20(self):
        assert CHAT_HISTORY_WINDOW == 20

    def test_default_user_id(self):
        assert DEFAULT_USER_ID == "default"


class TestBuildPortfolioContext:
    def test_returns_expected_keys(self, fresh_db, warmed_cache):
        ctx = build_portfolio_context(fresh_db, warmed_cache)
        assert set(ctx.keys()) == {
            "cash_balance", "total_value", "positions", "watchlist"
        }

    def test_watchlist_entries_have_ticker_price_change_percent(
        self, fresh_db, warmed_cache
    ):
        ctx = build_portfolio_context(fresh_db, warmed_cache)
        assert len(ctx["watchlist"]) == 10
        sample = ctx["watchlist"][0]
        assert set(sample.keys()) == {"ticker", "price", "change_percent"}

    def test_is_json_serializable(self, fresh_db, warmed_cache):
        ctx = build_portfolio_context(fresh_db, warmed_cache)
        json.dumps(ctx)  # Must not raise


class TestBuildMessages:
    def test_order_system_portfolio_user(self, fresh_db, warmed_cache):
        msgs = build_messages(fresh_db, warmed_cache, "hi")
        assert msgs[0] == {"role": "system", "content": SYSTEM_PROMPT}
        assert msgs[1]["role"] == "system"
        assert msgs[1]["content"].startswith("# Current portfolio state\n")
        assert msgs[-1] == {"role": "user", "content": "hi"}

    def test_portfolio_message_is_json_suffix(self, fresh_db, warmed_cache):
        msgs = build_messages(fresh_db, warmed_cache, "hi")
        payload = msgs[1]["content"].split("\n", 1)[1]
        parsed = json.loads(payload)
        assert "cash_balance" in parsed

    def test_empty_history_has_3_messages(self, fresh_db, warmed_cache):
        """No prior chat_messages rows -> [system, system-portfolio, user]."""
        msgs = build_messages(fresh_db, warmed_cache, "hi")
        assert len(msgs) == 3

    def test_history_inserted_between_portfolio_and_user(
        self, fresh_db, warmed_cache
    ):
        _insert_chat_row(
            fresh_db, "user", "first", "2026-04-21T00:00:00+00:00"
        )
        _insert_chat_row(
            fresh_db, "assistant", "second", "2026-04-21T00:00:01+00:00"
        )
        msgs = build_messages(fresh_db, warmed_cache, "hi")
        assert msgs[0]["role"] == "system"  # SYSTEM_PROMPT
        assert msgs[1]["role"] == "system"  # portfolio
        assert msgs[2] == {"role": "user", "content": "first"}
        assert msgs[3] == {"role": "assistant", "content": "second"}
        assert msgs[4] == {"role": "user", "content": "hi"}

    def test_history_window_caps_at_20(self, fresh_db, warmed_cache):
        for i in range(30):
            _insert_chat_row(
                fresh_db, "user", f"msg-{i}",
                f"2026-04-21T00:00:{i:02d}+00:00",
            )
        msgs = build_messages(fresh_db, warmed_cache, "hi")
        # 2 leading system + 20 history + 1 trailing user = 23
        assert len(msgs) == 23
        # Oldest kept should be msg-10 (30 total, keep last 20)
        assert msgs[2]["content"] == "msg-10"
        assert msgs[21]["content"] == "msg-29"

    def test_history_filters_by_user_id(self, fresh_db, warmed_cache):
        """Rows with user_id != 'default' are NOT included (Pitfall 5)."""
        fresh_db.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, NULL, ?)",
            (str(uuid.uuid4()), "other", "user", "LEAK", "2026-04-21T00:00:00+00:00"),
        )
        fresh_db.commit()
        msgs = build_messages(fresh_db, warmed_cache, "hi")
        assert all("LEAK" not in str(m.get("content", "")) for m in msgs)
