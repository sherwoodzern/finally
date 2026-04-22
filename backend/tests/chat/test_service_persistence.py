"""Unit tests for app.chat.service persistence ordering (D-18) + get_history (D-19)."""

from __future__ import annotations

import json
import uuid

import pytest

from app.chat import MockChatClient
from app.chat.service import ChatTurnError, get_history, run_turn
from tests.chat.conftest import RaisingChatClient


def _chat_rows(conn, user_id: str = "default") -> list:
    return conn.execute(
        "SELECT id, role, content, actions, created_at "
        "FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC",
        (user_id,),
    ).fetchall()


class TestUserTurnBeforeLLM:
    async def test_user_row_persisted_even_if_llm_raises(
        self, fresh_db, warmed_cache, fake_source
    ):
        """D-18: user turn persisted BEFORE client.complete(). LLM raise -> 1 row, NULL actions."""
        client = RaisingChatClient(RuntimeError("network down"))
        with pytest.raises(ChatTurnError):
            await run_turn(fresh_db, warmed_cache, fake_source, client, "hi")
        rows = _chat_rows(fresh_db)
        assert len(rows) == 1
        assert rows[0]["role"] == "user"
        assert rows[0]["content"] == "hi"
        assert rows[0]["actions"] is None


class TestAssistantTurnAfterAutoExec:
    async def test_assistant_row_actions_column_is_enriched_json(
        self, fresh_db, warmed_cache, fake_source
    ):
        """D-08: assistant.actions = JSON({trades:[...], watchlist_changes:[...]}) with enriched statuses."""
        client = MockChatClient()
        await run_turn(fresh_db, warmed_cache, fake_source, client, "buy AAPL 10")
        rows = _chat_rows(fresh_db)
        assert len(rows) == 2
        assert rows[0]["role"] == "user"
        assert rows[0]["actions"] is None
        assert rows[1]["role"] == "assistant"
        assert rows[1]["actions"] is not None
        parsed = json.loads(rows[1]["actions"])
        assert "trades" in parsed
        assert "watchlist_changes" in parsed
        assert parsed["trades"][0]["status"] == "executed"

    async def test_assistant_actions_empty_on_no_match(
        self, fresh_db, warmed_cache, fake_source
    ):
        """No match -> actions JSON is {trades:[], watchlist_changes:[]}, not NULL."""
        client = MockChatClient()
        await run_turn(fresh_db, warmed_cache, fake_source, client, "hello")
        rows = _chat_rows(fresh_db)
        assert rows[1]["actions"] is not None
        parsed = json.loads(rows[1]["actions"])
        assert parsed == {"trades": [], "watchlist_changes": []}


class TestChatMessagesUserIdFilter:
    async def test_other_user_rows_do_not_pollute_history(
        self, fresh_db, warmed_cache, fake_source
    ):
        """get_history filters by user_id='default' (Pitfall 5)."""
        fresh_db.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, NULL, ?)",
            (str(uuid.uuid4()), "other", "user", "LEAK", "2026-04-21T00:00:00+00:00"),
        )
        fresh_db.commit()
        history = get_history(fresh_db, limit=50)
        assert all(m.content != "LEAK" for m in history.messages)


class TestGetHistory:
    async def test_returns_rows_asc(self, fresh_db, warmed_cache, fake_source):
        """Two run_turns produce [user hello, assistant reply, user world, assistant reply] ASC."""
        client = MockChatClient()
        await run_turn(fresh_db, warmed_cache, fake_source, client, "hello")
        await run_turn(fresh_db, warmed_cache, fake_source, client, "world")
        history = get_history(fresh_db, limit=50)
        assert len(history.messages) == 4
        assert history.messages[0].role == "user"
        assert history.messages[0].content == "hello"
        # Second user turn (third row) carries the "world" content.
        assert history.messages[2].role == "user"
        assert history.messages[2].content == "world"
        assert history.messages[-1].role == "assistant"

    async def test_parses_actions_json_or_none(
        self, fresh_db, warmed_cache, fake_source
    ):
        client = MockChatClient()
        await run_turn(fresh_db, warmed_cache, fake_source, client, "buy AAPL 1")
        history = get_history(fresh_db, limit=50)
        user_row = next(m for m in history.messages if m.role == "user")
        assistant_row = next(m for m in history.messages if m.role == "assistant")
        assert user_row.actions is None
        assert isinstance(assistant_row.actions, dict)
        assert "trades" in assistant_row.actions

    async def test_limit_returns_tail_asc(self, fresh_db, warmed_cache, fake_source):
        """limit=2 over 6 rows -> last 2 ordered ASC (two-level subquery, Pitfall 8)."""
        for i in range(3):
            fresh_db.execute(
                "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
                "VALUES (?, ?, ?, ?, NULL, ?)",
                (str(uuid.uuid4()), "default", "user", f"msg-{i}",
                 f"2026-04-21T00:00:{i:02d}+00:00"),
            )
        fresh_db.commit()
        history = get_history(fresh_db, limit=2)
        assert len(history.messages) == 2
        assert history.messages[0].content == "msg-1"
        assert history.messages[1].content == "msg-2"


class TestCommitCount:
    async def test_two_commits_per_successful_turn(
        self, fresh_db, warmed_cache, fake_source
    ):
        """Successful turn: one commit for user row, one for assistant row (D-18)."""
        client = MockChatClient()
        before = fresh_db.total_changes
        await run_turn(fresh_db, warmed_cache, fake_source, client, "hello")
        after = fresh_db.total_changes
        # At minimum 2 row-mutations (user insert + assistant insert); auto-exec
        # may add more for matched patterns. For 'hello' there are no matches,
        # so only the 2 chat_messages inserts occur.
        assert after - before == 2

    async def test_one_commit_on_llm_failure(
        self, fresh_db, warmed_cache, fake_source
    ):
        """LLM failure: only the user row commit happens."""
        client = RaisingChatClient(RuntimeError("x"))
        before = fresh_db.total_changes
        with pytest.raises(ChatTurnError):
            await run_turn(fresh_db, warmed_cache, fake_source, client, "hi")
        after = fresh_db.total_changes
        assert after - before == 1
