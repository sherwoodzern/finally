"""Chat service orchestration: run_turn + get_history + ChatTurnError (D-01..D-19)."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime

from app.market import MarketDataSource, PriceCache
from app.portfolio.service import (
    InsufficientCash,
    InsufficientShares,
    PriceUnavailable,
    UnknownTicker,
    execute_trade,
)
from app.watchlist.service import add_ticker, remove_ticker

from .client import ChatClient
from .models import (
    ChatMessageOut,
    ChatResponse,
    HistoryResponse,
    StructuredResponse,
    TradeAction,
    TradeActionResult,
    WatchlistAction,
    WatchlistActionResult,
)
from .prompts import build_messages

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"


class ChatTurnError(Exception):
    """Raised when the LLM call fails (transport, auth, rate limit, bad JSON).

    The route layer (Plan 03) translates this into HTTPException(502,
    detail={'error': 'llm_unavailable', 'message': str(exc)}). This is the
    ONLY broad try/except Exception boundary around client.complete() per
    D-14; per-action failures stay inside run_turn as status='failed' entries.
    """


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _persist_user_turn(conn: sqlite3.Connection, content: str) -> None:
    """INSERT user row with actions=NULL; commit (D-18 step 1)."""
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, NULL, ?)",
        (str(uuid.uuid4()), DEFAULT_USER_ID, "user", content, _now_iso()),
    )
    conn.commit()


def _persist_assistant_turn(
    conn: sqlite3.Connection,
    content: str,
    trade_results: list[TradeActionResult],
    watchlist_results: list[WatchlistActionResult],
) -> None:
    """INSERT assistant row with enriched actions JSON; commit (D-08, D-18 step 2)."""
    actions_json = json.dumps(
        {
            "trades": [r.model_dump(mode="json") for r in trade_results],
            "watchlist_changes": [
                r.model_dump(mode="json") for r in watchlist_results
            ],
        }
    )
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            DEFAULT_USER_ID,
            "assistant",
            content,
            actions_json,
            _now_iso(),
        ),
    )
    conn.commit()


def _run_one_trade(
    conn: sqlite3.Connection,
    cache: PriceCache,
    ta: TradeAction,
) -> TradeActionResult:
    """Execute one trade; translate exceptions per D-12. Never raises (D-10)."""
    try:
        tr = execute_trade(conn, cache, ta.ticker, ta.side, ta.quantity)
    except (
        InsufficientCash,
        InsufficientShares,
        UnknownTicker,
        PriceUnavailable,
    ) as exc:
        logger.info(
            "Chat auto-exec: trade %s %s x %s FAILED %s",
            ta.ticker,
            ta.side,
            ta.quantity,
            exc.code,
        )
        return TradeActionResult(
            ticker=ta.ticker,
            side=ta.side,
            quantity=ta.quantity,
            status="failed",
            error=exc.code,
            message=str(exc),
        )
    except ValueError as exc:
        # Pydantic ticker-normalization raised inside nested flow (rare --
        # StructuredResponse normally catches at parse time).
        return TradeActionResult(
            ticker=ta.ticker,
            side=ta.side,
            quantity=ta.quantity,
            status="failed",
            error="invalid_ticker",
            message=str(exc),
        )
    except Exception as exc:
        logger.warning(
            "Chat auto-exec: trade %s unexpected error",
            ta.ticker,
            exc_info=True,
        )
        return TradeActionResult(
            ticker=ta.ticker,
            side=ta.side,
            quantity=ta.quantity,
            status="failed",
            error="internal_error",
            message=str(exc),
        )

    logger.info(
        "Chat auto-exec: trade %s %s x %s executed",
        tr.ticker,
        tr.side,
        tr.quantity,
    )
    return TradeActionResult(
        ticker=tr.ticker,
        side=tr.side,
        quantity=tr.quantity,
        status="executed",
        price=tr.price,
        cash_balance=tr.cash_balance,
        executed_at=tr.executed_at,
    )


async def _run_one_watchlist(
    conn: sqlite3.Connection,
    source: MarketDataSource,
    wa: WatchlistAction,
) -> WatchlistActionResult:
    """Execute one watchlist mutation; mirror routes.py:55-64 choreography. Never raises (D-10)."""
    try:
        if wa.action == "add":
            result = add_ticker(conn, wa.ticker)
            if result.status == "added":
                try:
                    await source.add_ticker(wa.ticker)
                except Exception:
                    # D-11: DB is the reconciliation anchor; next restart heals.
                    logger.warning(
                        "Chat auto-exec: source.add_ticker(%s) raised after DB commit",
                        wa.ticker,
                        exc_info=True,
                    )
            logger.info(
                "Chat auto-exec: watchlist %s %s %s",
                wa.action,
                wa.ticker,
                result.status,
            )
            return WatchlistActionResult(
                ticker=wa.ticker, action=wa.action, status=result.status
            )

        # action == "remove"
        remove_result = remove_ticker(conn, wa.ticker)
        if remove_result.status == "removed":
            try:
                await source.remove_ticker(wa.ticker)
            except Exception:
                logger.warning(
                    "Chat auto-exec: source.remove_ticker(%s) raised after DB commit",
                    wa.ticker,
                    exc_info=True,
                )
        logger.info(
            "Chat auto-exec: watchlist %s %s %s",
            wa.action,
            wa.ticker,
            remove_result.status,
        )
        return WatchlistActionResult(
            ticker=wa.ticker, action=wa.action, status=remove_result.status
        )
    except ValueError as exc:
        return WatchlistActionResult(
            ticker=wa.ticker,
            action=wa.action,
            status="failed",
            error="invalid_ticker",
            message=str(exc),
        )
    except Exception as exc:
        logger.warning(
            "Chat auto-exec: watchlist %s unexpected error",
            wa.ticker,
            exc_info=True,
        )
        return WatchlistActionResult(
            ticker=wa.ticker,
            action=wa.action,
            status="failed",
            error="internal_error",
            message=str(exc),
        )


async def run_turn(
    conn: sqlite3.Connection,
    cache: PriceCache,
    source: MarketDataSource,
    client: ChatClient,
    user_message: str,
) -> ChatResponse:
    """One chat turn: persist user, call LLM, auto-exec (watchlist first), persist assistant.

    Returns a ChatResponse with per-action statuses (D-07). Raises ChatTurnError
    only when the LLM call itself fails (D-14). Per-action failures stay inside
    the returned ChatResponse as status='failed' entries (D-10).
    """
    _persist_user_turn(conn, user_message)

    messages = build_messages(conn, cache, user_message)

    try:
        structured: StructuredResponse = await client.complete(messages)
    except Exception as exc:
        logger.error("LLM call failed", exc_info=True)
        raise ChatTurnError(str(exc)) from exc

    # D-09: watchlist FIRST so "add X and buy X" can succeed in one turn.
    watchlist_results: list[WatchlistActionResult] = []
    for wa in structured.watchlist_changes:
        watchlist_results.append(await _run_one_watchlist(conn, source, wa))

    trade_results: list[TradeActionResult] = []
    for ta in structured.trades:
        trade_results.append(_run_one_trade(conn, cache, ta))

    _persist_assistant_turn(
        conn, structured.message, trade_results, watchlist_results
    )

    return ChatResponse(
        message=structured.message,
        trades=trade_results,
        watchlist_changes=watchlist_results,
    )


def get_history(
    conn: sqlite3.Connection,
    limit: int,
    user_id: str = DEFAULT_USER_ID,
) -> HistoryResponse:
    """Return the last `limit` chat_messages rows ordered ASC (D-19, Pitfall 8)."""
    rows = conn.execute(
        "SELECT id, role, content, actions, created_at FROM ("
        "  SELECT id, role, content, actions, created_at FROM chat_messages "
        "  WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
        ") ORDER BY created_at ASC",
        (user_id, limit),
    ).fetchall()

    messages: list[ChatMessageOut] = []
    for row in rows:
        actions_raw = row["actions"]
        actions = json.loads(actions_raw) if actions_raw is not None else None
        messages.append(
            ChatMessageOut(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                actions=actions,
                created_at=row["created_at"],
            )
        )
    return HistoryResponse(messages=messages)
