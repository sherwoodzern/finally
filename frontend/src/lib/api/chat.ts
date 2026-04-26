/**
 * Wire-boundary REST client for /api/chat. Verified against backend/app/chat/models.py.
 * Mirrors portfolio.ts shape (PATTERNS.md "frontend/src/lib/api/chat.ts").
 * Phase 5 D-07 response shape: per-action `status` + optional `error`.
 */

export type TradeStatus = 'executed' | 'failed';
export type WatchlistStatus = 'added' | 'removed' | 'exists' | 'not_present' | 'failed';
export type ActionStatus = TradeStatus | WatchlistStatus;

export interface TradeActionResult {
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  status: TradeStatus;
  price?: number;
  executed_at?: string;
  error?: string;
}

export interface WatchlistActionResult {
  ticker: string;
  action: 'add' | 'remove';
  status: WatchlistStatus;
  error?: string;
}

export interface ActionsBlock {
  trades: TradeActionResult[];
  watchlist_changes: WatchlistActionResult[];
}

export interface ChatResponse {
  id: string;
  role: 'assistant';
  content: string;
  created_at: string;
  trades: TradeActionResult[];
  watchlist_changes: WatchlistActionResult[];
}

export interface ChatMessageOut {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  actions: ActionsBlock | null;
}

export interface HistoryResponse {
  messages: ChatMessageOut[];
}

/** GET /api/chat/history — called by useQuery(['chat','history']) on drawer mount. */
export async function getChatHistory(): Promise<HistoryResponse> {
  const res = await fetch('/api/chat/history');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as HistoryResponse;
}

/** POST /api/chat — called by useMutation in ChatInput.
 * Phase 5 D-12 transport errors return 502; throw plain Error (not custom class). */
export async function postChat(body: { message: string }): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const j = (await res.json().catch(() => ({}))) as {
      detail?: { error?: string; message?: string };
    };
    throw new Error(j?.detail?.message ?? `HTTP ${res.status}`);
  }
  return (await res.json()) as ChatResponse;
}
