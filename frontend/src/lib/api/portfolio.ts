/**
 * Wire-boundary REST client for the portfolio + trading API.
 * Phase 03 contract (03-CONTEXT.md D-10): failures return 400 with
 * detail = { error, message }. The key is `detail.error`, NOT `detail.code`.
 */

export interface TradeBody {
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
}

export interface PositionOut {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  change_percent: number;
}

export interface PortfolioResponse {
  cash_balance: number;
  total_value: number;
  positions: PositionOut[];
}

export interface TradeResponse {
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  cash_balance: number;
  position_quantity: number;
  position_avg_cost: number;
  executed_at: string;
}

/** Thrown by postTrade on any non-OK response. Code maps to D-07 copy. */
export class TradeError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = 'TradeError';
    this.code = code;
  }
}

/** GET /api/portfolio — called by useQuery(['portfolio']). */
export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch('/api/portfolio');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as PortfolioResponse;
}

/** POST /api/portfolio/trade — called by useMutation in TradeBar. */
export async function postTrade(body: TradeBody): Promise<TradeResponse> {
  const res = await fetch('/api/portfolio/trade', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const j = (await res.json().catch(() => ({}))) as {
      detail?: { error?: string; message?: string };
    };
    throw new TradeError(j?.detail?.error ?? 'unknown', j?.detail?.message ?? '');
  }
  return (await res.json()) as TradeResponse;
}
