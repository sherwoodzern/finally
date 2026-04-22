"""Unit tests for app.chat.client.LiveChatClient call-shape (patches litellm.completion)."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

from app.chat.client import EXTRA_BODY, MODEL, LiveChatClient, create_chat_client
from app.chat.mock import MockChatClient
from app.chat.models import StructuredResponse


def _fake_completion_response(json_str: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json_str))]
    )


class TestLiveChatClientCallShape:
    async def test_completion_call_shape_matches_cerebras_skill(self):
        """LiveChatClient.complete passes model, response_format, reasoning_effort, extra_body per the cerebras skill."""
        client = LiveChatClient()
        messages = [{"role": "user", "content": "hi"}]
        with patch("app.chat.client.completion") as mock_completion:
            mock_completion.return_value = _fake_completion_response(
                '{"message":"ok"}'
            )
            result = await client.complete(messages)
        mock_completion.assert_called_once()
        kwargs = mock_completion.call_args.kwargs
        assert kwargs["model"] == "openrouter/openai/gpt-oss-120b"
        assert kwargs["response_format"] is StructuredResponse
        assert kwargs["reasoning_effort"] == "low"
        assert kwargs["extra_body"] == {"provider": {"order": ["cerebras"]}}
        assert kwargs["messages"] is messages
        assert isinstance(result, StructuredResponse)
        assert result.message == "ok"

    async def test_parses_structured_response_content(self):
        client = LiveChatClient()
        with patch("app.chat.client.completion") as mock_completion:
            mock_completion.return_value = _fake_completion_response(
                '{"message":"hello","trades":[{"ticker":"AAPL","side":"buy","quantity":5}]}'
            )
            result = await client.complete([])
        assert result.trades[0].ticker == "AAPL"

    def test_module_constants_match_cerebras_skill(self):
        """MODEL + EXTRA_BODY constants must match the cerebras skill verbatim."""
        assert MODEL == "openrouter/openai/gpt-oss-120b"
        assert EXTRA_BODY == {"provider": {"order": ["cerebras"]}}


class TestCreateChatClientFactory:
    def test_llm_mock_true_returns_mock(self):
        with patch.dict(os.environ, {"LLM_MOCK": "true"}, clear=False):
            client = create_chat_client()
        assert isinstance(client, MockChatClient)

    def test_llm_mock_absent_returns_live(self):
        env = {k: v for k, v in os.environ.items() if k != "LLM_MOCK"}
        with patch.dict(os.environ, env, clear=True):
            client = create_chat_client()
        assert isinstance(client, LiveChatClient)

    def test_llm_mock_other_value_returns_live(self):
        with patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False):
            client = create_chat_client()
        assert isinstance(client, LiveChatClient)
