/**
 * Price store - single source of truth for ticker-keyed live price state.
 * Owns ONE EventSource for the app lifetime; managed by PriceStreamProvider.
 *
 * Analog of backend/app/market/cache.py (first-seen-price + idempotent lifecycle).
 * Decision refs: D-11, D-12, D-13, D-14, D-15, D-16, D-17, D-18, D-19.
 */

import { create } from 'zustand';
import type { ConnectionStatus, RawPayload, Tick } from './sse-types';

interface PriceStoreState {
  prices: Record<string, Tick>;
  status: ConnectionStatus;
  lastEventAt: number | null;
  connect: () => void;
  disconnect: () => void;
  ingest: (payload: Record<string, RawPayload>) => void;
  reset: () => void;
}

const SSE_URL = '/api/stream/prices'; // D-16: relative URL, same-origin in dev (via rewrites) and prod (via StaticFiles mount)

/** Injectable EventSource constructor so Plan 06-03 tests can swap in MockEventSource. */
let EventSourceCtor: typeof EventSource =
  typeof window !== 'undefined'
    ? window.EventSource
    : (undefined as unknown as typeof EventSource);

/** Test-only DI hook. Not called by product code. */
export function __setEventSource(ctor: typeof EventSource): void {
  EventSourceCtor = ctor;
}

let es: EventSource | null = null;

function isValidPayload(v: unknown): v is RawPayload {
  if (!v || typeof v !== 'object') return false;
  const p = v as Record<string, unknown>;
  return typeof p.ticker === 'string' && typeof p.price === 'number';
}

export const usePriceStore = create<PriceStoreState>()((set, get) => ({
  prices: {},
  status: 'disconnected',
  lastEventAt: null,

  ingest: (payload) => {
    const existing = get().prices;
    const next: Record<string, Tick> = { ...existing };
    for (const [ticker, raw] of Object.entries(payload)) {
      if (!isValidPayload(raw)) continue; // D-19: skip malformed entries silently
      const prior = next[ticker];
      next[ticker] = {
        ...raw,
        session_start_price: prior?.session_start_price ?? raw.price, // D-14: freeze first-seen
      };
    }
    set({ prices: next, lastEventAt: Date.now() });
  },

  connect: () => {
    // D-15: idempotent. No-op if a live EventSource exists (protects StrictMode double-invoke).
    if (es && es.readyState !== 2) return;
    es = new EventSourceCtor(SSE_URL);
    es.onopen = () => set({ status: 'connected' });
    es.onmessage = (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data) as Record<string, RawPayload>;
        get().ingest(parsed);
        if (get().status !== 'connected') set({ status: 'connected' });
      } catch (err) {
        // D-19: narrow try/catch at the wire boundary. Log + drop frame, do NOT rethrow.
        console.warn('sse parse failed', err, event.data);
      }
    };
    es.onerror = () => {
      if (!es) return;
      // D-18: EventSource state machine.
      if (es.readyState === 0) set({ status: 'reconnecting' }); // CONNECTING
      else if (es.readyState === 2) set({ status: 'disconnected' }); // CLOSED
    };
  },

  disconnect: () => {
    if (es) {
      es.close();
      es = null;
    }
    set({ status: 'disconnected' });
  },

  reset: () => set({ prices: {}, status: 'disconnected', lastEventAt: null }),
}));

/** Subscribe to a single ticker's Tick. Returns undefined before first tick. */
export const selectTick =
  (ticker: string) =>
  (s: PriceStoreState): Tick | undefined =>
    s.prices[ticker];

/** Subscribe to the connection status (for Phase 7 FE-10 header dot). */
export const selectConnectionStatus = (s: PriceStoreState) => s.status;
