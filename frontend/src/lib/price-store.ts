/**
 * Price store - single source of truth for ticker-keyed live price state.
 * Owns ONE EventSource for the app lifetime; managed by PriceStreamProvider.
 *
 * Analog of backend/app/market/cache.py (first-seen-price + idempotent lifecycle).
 * Decision refs: D-11, D-12, D-13, D-14, D-15, D-16, D-17, D-18, D-19,
 * Phase 7: D-01 (flash), D-03 (sparkline buffer).
 */

import { create } from 'zustand';
import type { ConnectionStatus, RawPayload, Tick } from './sse-types';

interface PriceStoreState {
  prices: Record<string, Tick>;
  status: ConnectionStatus;
  lastEventAt: number | null;
  sparklineBuffers: Record<string, number[]>;
  flashDirection: Record<string, 'up' | 'down'>;
  selectedTicker: string | null;
  selectedTab: 'chart' | 'heatmap' | 'pnl';
  tradeFlash: Record<string, 'up' | 'down'>;
  connect: () => void;
  disconnect: () => void;
  ingest: (payload: Record<string, RawPayload>) => void;
  reset: () => void;
  setSelectedTicker: (t: string | null) => void;
  setSelectedTab: (t: 'chart' | 'heatmap' | 'pnl') => void;
  flashTrade: (ticker: string, dir: 'up' | 'down') => void;
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

const flashTimers = new Map<string, ReturnType<typeof setTimeout>>();
const FLASH_MS = 500;
const tradeFlashTimers = new Map<string, ReturnType<typeof setTimeout>>();
const TRADE_FLASH_MS = 800;
const SPARKLINE_WINDOW = 120; // ~60s at 500ms tick cadence (D-03)

function isValidPayload(v: unknown): v is RawPayload {
  if (!v || typeof v !== 'object') return false;
  const p = v as Record<string, unknown>;
  return typeof p.ticker === 'string' && typeof p.price === 'number';
}

export const usePriceStore = create<PriceStoreState>()((set, get) => ({
  prices: {},
  status: 'disconnected',
  lastEventAt: null,
  sparklineBuffers: {},
  flashDirection: {},
  selectedTicker: null,
  selectedTab: 'chart',
  tradeFlash: {},

  ingest: (payload) => {
    const state = get();
    const next: Record<string, Tick> = { ...state.prices };
    const nextSparklines: Record<string, number[]> = { ...state.sparklineBuffers };
    const nextFlash: Record<string, 'up' | 'down'> = { ...state.flashDirection };
    const newFlashes: string[] = [];

    for (const [ticker, raw] of Object.entries(payload)) {
      if (!isValidPayload(raw)) continue; // D-19: skip malformed entries silently
      const prior = next[ticker];
      next[ticker] = {
        ...raw,
        session_start_price: prior?.session_start_price ?? raw.price, // D-14: freeze first-seen
      };

      // D-01 flash direction
      if (prior && raw.price !== prior.price) {
        nextFlash[ticker] = raw.price > prior.price ? 'up' : 'down';
        newFlashes.push(ticker);
      }

      // D-03 sparkline buffer (append; trim to SPARKLINE_WINDOW)
      const priorBuf = nextSparklines[ticker] ?? [];
      nextSparklines[ticker] =
        priorBuf.length >= SPARKLINE_WINDOW
          ? [...priorBuf.slice(priorBuf.length - SPARKLINE_WINDOW + 1), raw.price]
          : [...priorBuf, raw.price];
    }

    set({
      prices: next,
      sparklineBuffers: nextSparklines,
      flashDirection: nextFlash,
      lastEventAt: Date.now(),
    });

    // Schedule per-ticker clear AFTER the set() so the render sees the flash first.
    for (const ticker of newFlashes) {
      const prevTimer = flashTimers.get(ticker);
      if (prevTimer) clearTimeout(prevTimer);
      const handle = setTimeout(() => {
        set((s) => {
          const cleared = { ...s.flashDirection };
          delete cleared[ticker];
          return { flashDirection: cleared };
        });
        flashTimers.delete(ticker);
      }, FLASH_MS);
      flashTimers.set(ticker, handle);
    }
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
    flashTimers.forEach(clearTimeout);
    flashTimers.clear();
    tradeFlashTimers.forEach(clearTimeout);
    tradeFlashTimers.clear();
    set({ status: 'disconnected', flashDirection: {}, tradeFlash: {}, selectedTab: 'chart' });
  },

  reset: () => {
    flashTimers.forEach(clearTimeout);
    flashTimers.clear();
    tradeFlashTimers.forEach(clearTimeout);
    tradeFlashTimers.clear();
    set({
      prices: {},
      status: 'disconnected',
      lastEventAt: null,
      sparklineBuffers: {},
      flashDirection: {},
      selectedTicker: null,
      selectedTab: 'chart',
      tradeFlash: {},
    });
  },

  setSelectedTicker: (t) => set({ selectedTicker: t }),

  setSelectedTab: (t) => set({ selectedTab: t }),

  flashTrade: (ticker, dir) => {
    set((s) => ({ tradeFlash: { ...s.tradeFlash, [ticker]: dir } }));
    const prev = tradeFlashTimers.get(ticker);
    if (prev) clearTimeout(prev);
    const handle = setTimeout(() => {
      set((s) => {
        const cleared = { ...s.tradeFlash };
        delete cleared[ticker];
        return { tradeFlash: cleared };
      });
      tradeFlashTimers.delete(ticker);
    }, TRADE_FLASH_MS);
    tradeFlashTimers.set(ticker, handle);
  },
}));

/** Subscribe to a single ticker's Tick. Returns undefined before first tick. */
export const selectTick =
  (ticker: string) =>
  (s: PriceStoreState): Tick | undefined =>
    s.prices[ticker];

/** Subscribe to the connection status (for Phase 7 FE-10 header dot). */
export const selectConnectionStatus = (s: PriceStoreState) => s.status;

/** Subscribe to a single ticker's sparkline buffer. Returns undefined before first tick. */
export const selectSparkline =
  (ticker: string) =>
  (s: PriceStoreState): number[] | undefined =>
    s.sparklineBuffers[ticker];

/** Subscribe to a single ticker's transient flash direction. Undefined when no flash active. */
export const selectFlash =
  (ticker: string) =>
  (s: PriceStoreState): 'up' | 'down' | undefined =>
    s.flashDirection[ticker];

/** Subscribe to the user-selected ticker for the MainChart panel. */
export const selectSelectedTicker = (s: PriceStoreState): string | null => s.selectedTicker;

/** Subscribe to a single ticker's transient trade flash (separate from price flash). 800ms duration. */
export const selectTradeFlash =
  (ticker: string) =>
  (s: PriceStoreState): 'up' | 'down' | undefined =>
    s.tradeFlash[ticker];

/** Subscribe to the user-selected center-column tab (Chart / Heatmap / P&L). */
export const selectSelectedTab = (s: PriceStoreState): 'chart' | 'heatmap' | 'pnl' => s.selectedTab;
