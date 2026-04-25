/**
 * Wire-boundary REST client for the watchlist API (seed-only for Phase 07).
 * Phase 07 does not add/remove tickers via UI — that's Phase 08 chat.
 */

export interface WatchlistItem {
  ticker: string;
  added_at: string;
  price: number | null;
  previous_price: number | null;
  change_percent: number | null;
  direction: 'up' | 'down' | 'flat' | null;
  timestamp: number | null;
}

export interface WatchlistResponse {
  items: WatchlistItem[];
}

/** GET /api/watchlist — used to seed the Watchlist panel row order. */
export async function fetchWatchlist(): Promise<WatchlistResponse> {
  const res = await fetch('/api/watchlist');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as WatchlistResponse;
}
