/**
 * Type contracts for the SSE price stream.
 * Mirrors backend/app/market/models.py PriceUpdate.to_dict() (lines 39-49).
 */

export type Direction = 'up' | 'down' | 'flat';
export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

/** Shape of each value in the SSE dict, matching backend PriceUpdate.to_dict() */
export interface RawPayload {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: Direction;
}

/** Client-side extension: session_start_price frozen on first-seen (D-14). */
export interface Tick extends RawPayload {
  /** First price observed for this ticker since page load; never overwritten (D-14). */
  session_start_price: number;
}
