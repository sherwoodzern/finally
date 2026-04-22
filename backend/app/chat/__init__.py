"""Chat subsystem for FinAlly: LLM-driven auto-exec chat endpoint.

Public API:
    Models: ChatRequest, ChatResponse, StructuredResponse, TradeAction,
            WatchlistAction, TradeActionResult, WatchlistActionResult,
            ChatMessageOut, HistoryResponse
    Client: ChatClient (Protocol), LiveChatClient, MockChatClient,
            create_chat_client
    Prompts: (added in Task 4)
"""

from __future__ import annotations

from .client import ChatClient, LiveChatClient, create_chat_client
from .mock import MockChatClient
from .models import (
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

__all__ = [
    "ChatClient",
    "ChatMessageOut",
    "ChatRequest",
    "ChatResponse",
    "HistoryResponse",
    "LiveChatClient",
    "MockChatClient",
    "StructuredResponse",
    "TradeAction",
    "TradeActionResult",
    "WatchlistAction",
    "WatchlistActionResult",
    "create_chat_client",
]
