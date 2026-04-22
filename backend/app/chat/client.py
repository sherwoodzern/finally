"""LLM client contract + live LiteLLM wrapper + env-driven factory (D-03, D-04, D-05)."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Protocol

from litellm import completion

from .models import StructuredResponse

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}


class ChatClient(Protocol):
    """Chat client contract. Implementations: LiveChatClient, MockChatClient."""

    async def complete(self, messages: list[dict]) -> StructuredResponse:  # pragma: no cover - Protocol
        ...


class LiveChatClient:
    """Call LLM via LiteLLM -> OpenRouter -> Cerebras with structured output (D-04).

    The sync litellm.completion is wrapped in asyncio.to_thread to keep the event
    loop responsive, mirroring massive_client.py:97. LiveChatClient never reads
    OPENROUTER_API_KEY -- LiteLLM picks it up from the environment at call time.
    Missing key surfaces as AuthenticationError from completion(), which the chat
    service translates to HTTP 502 per D-14.
    """

    async def complete(self, messages: list[dict]) -> StructuredResponse:
        def _call() -> str:
            response = completion(
                model=MODEL,
                messages=messages,
                response_format=StructuredResponse,
                reasoning_effort="low",
                extra_body=EXTRA_BODY,
            )
            return response.choices[0].message.content

        raw = await asyncio.to_thread(_call)
        return StructuredResponse.model_validate_json(raw)


def create_chat_client() -> ChatClient:
    """Return MockChatClient when LLM_MOCK='true', else LiveChatClient (D-05).

    Mirrors app.market.factory.create_market_data_source's env check. Read once
    at lifespan entry; never read per-request (Pitfall 6).
    """
    if os.environ.get("LLM_MOCK", "").strip().lower() == "true":
        from .mock import MockChatClient
        logger.info("Chat client: MockChatClient (LLM_MOCK=true)")
        return MockChatClient()
    logger.info("Chat client: LiveChatClient (LiteLLM -> OpenRouter -> Cerebras)")
    return LiveChatClient()
