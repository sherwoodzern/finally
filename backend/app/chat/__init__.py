"""Chat subsystem for FinAlly: LLM-driven auto-exec chat endpoint.

Public API:
    Models: ChatRequest, ChatResponse, StructuredResponse, TradeAction,
            WatchlistAction, TradeActionResult, WatchlistActionResult,
            ChatMessageOut, HistoryResponse
    Client: ChatClient (Protocol), LiveChatClient, MockChatClient,
            create_chat_client
    Prompts: SYSTEM_PROMPT, CHAT_HISTORY_WINDOW, build_portfolio_context,
             build_messages
    Service: run_turn, get_history, ChatTurnError
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
from .prompts import (
    CHAT_HISTORY_WINDOW,
    SYSTEM_PROMPT,
    build_messages,
    build_portfolio_context,
)
from .routes import create_chat_router
from .service import ChatTurnError, get_history, run_turn

__all__ = [
    "CHAT_HISTORY_WINDOW",
    "ChatClient",
    "ChatMessageOut",
    "ChatRequest",
    "ChatResponse",
    "ChatTurnError",
    "HistoryResponse",
    "LiveChatClient",
    "MockChatClient",
    "SYSTEM_PROMPT",
    "StructuredResponse",
    "TradeAction",
    "TradeActionResult",
    "WatchlistAction",
    "WatchlistActionResult",
    "build_messages",
    "build_portfolio_context",
    "create_chat_client",
    "create_chat_router",
    "get_history",
    "run_turn",
]
