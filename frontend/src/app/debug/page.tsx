'use client';

/**
 * /debug - developer diagnostic view of the SSE price stream.
 *
 * Subscribes to the Zustand store via hooks so the table re-renders on every
 * tick. No styling beyond dark-theme tokens; no color semantics, no sort, no
 * filter, no interactions. Layout matches UI-SPEC section 5.2 exactly.
 *
 * Decision refs: D-20 (debug route), D-23 (src/app/debug/page.tsx path).
 */

import { usePriceStore } from '@/lib/price-store';

/** Format backend Unix-seconds timestamp as UTC HH:MM:SS.sss (UI-SPEC section 5.2). */
function formatTimestamp(sec: number): string {
  const d = new Date(sec * 1000);
  const hh = String(d.getUTCHours()).padStart(2, '0');
  const mm = String(d.getUTCMinutes()).padStart(2, '0');
  const ss = String(d.getUTCSeconds()).padStart(2, '0');
  const ms = String(d.getUTCMilliseconds()).padStart(3, '0');
  return `${hh}:${mm}:${ss}.${ms}`;
}

/** Format the store's lastEventAt epoch-ms as an ISO string, or em-dash if null. */
function formatLastEvent(ms: number | null): string {
  if (ms === null) return '—';
  return new Date(ms).toISOString();
}

export default function DebugPage() {
  const prices = usePriceStore((s) => s.prices);
  const status = usePriceStore((s) => s.status);
  const lastEventAt = usePriceStore((s) => s.lastEventAt);

  const rows = Object.values(prices).sort((a, b) => a.ticker.localeCompare(b.ticker));
  const tickerCount = rows.length;

  return (
    <main className="min-h-screen p-6">
      <h1 className="text-xl font-semibold">Price Stream Debug</h1>
      <div className="mt-2 border-b border-border-muted" />

      <div className="mt-4 text-sm text-foreground-muted">
        <span className="px-2">Status: {status}</span>
        <span className="px-2">|</span>
        <span className="px-2">Tickers: {tickerCount}</span>
        <span className="px-2">|</span>
        <span className="px-2">Last tick: {formatLastEvent(lastEventAt)}</span>
      </div>

      <table className="mt-4 w-full border-collapse font-mono text-sm">
        <thead>
          <tr>
            <th className="text-left px-2 py-2 border-b border-border-muted text-foreground-muted">Ticker</th>
            <th className="text-right px-2 py-2 border-b border-border-muted text-foreground-muted">Price</th>
            <th className="text-right px-2 py-2 border-b border-border-muted text-foreground-muted">Prev</th>
            <th className="text-right px-2 py-2 border-b border-border-muted text-foreground-muted">Change</th>
            <th className="text-right px-2 py-2 border-b border-border-muted text-foreground-muted">Δ%</th>
            <th className="text-left px-2 py-2 border-b border-border-muted text-foreground-muted">Direction</th>
            <th className="text-right px-2 py-2 border-b border-border-muted text-foreground-muted">Session Start</th>
            <th className="text-left px-2 py-2 border-b border-border-muted text-foreground-muted">Last Tick</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={8} className="text-center py-4 text-foreground-muted">
                Awaiting first price tick...
              </td>
            </tr>
          ) : (
            rows.map((t) => (
              <tr key={t.ticker} className="border-b border-border-muted">
                <td className="px-2 py-2 text-foreground">{t.ticker}</td>
                <td className="text-right px-2 py-2 text-foreground">{t.price.toFixed(4)}</td>
                <td className="text-right px-2 py-2 text-foreground">{t.previous_price.toFixed(4)}</td>
                <td className="text-right px-2 py-2 text-foreground">{t.change.toFixed(4)}</td>
                <td className="text-right px-2 py-2 text-foreground">{t.change_percent.toFixed(4)}</td>
                <td className="px-2 py-2 text-foreground">{t.direction}</td>
                <td className="text-right px-2 py-2 text-foreground">{t.session_start_price.toFixed(4)}</td>
                <td className="px-2 py-2 text-foreground">{formatTimestamp(t.timestamp)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {status === 'disconnected' || status === 'reconnecting' ? (
        <p className="mt-2 text-sm text-foreground-muted">Connection lost. Reconnecting...</p>
      ) : null}
    </main>
  );
}
