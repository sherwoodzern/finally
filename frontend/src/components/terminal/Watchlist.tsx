'use client';

/**
 * Left-column panel: fetches the ticker list once via GET /api/watchlist
 * (authoritative row order) and renders one WatchlistRow per ticker.
 * Row clicks dispatch setSelectedTicker so the MainChart re-renders.
 * Decision refs: 07-UI-SPEC §5.2; 07-RESEARCH Open Question #4.
 */

import { useQuery } from '@tanstack/react-query';
import { fetchWatchlist } from '@/lib/api/watchlist';
import { usePriceStore } from '@/lib/price-store';
import { WatchlistRow } from './WatchlistRow';

export function Watchlist() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['watchlist'],
    queryFn: fetchWatchlist,
  });

  const tickers = (data?.items ?? []).map((it) => it.ticker);
  const setSelectedTicker = usePriceStore((s) => s.setSelectedTicker);

  return (
    <aside className="flex-1 bg-surface border border-border-muted rounded overflow-hidden flex flex-col">
      <h2 className="text-xl font-semibold px-4 py-3 border-b border-border-muted">
        Watchlist
      </h2>
      <div className="overflow-y-auto">
        <table className="w-full border-collapse">
          <tbody>
            {isPending ? (
              <tr>
                <td className="px-4 py-6 text-sm text-foreground-muted">
                  Loading watchlist…
                </td>
              </tr>
            ) : isError ? (
              <tr>
                <td className="px-4 py-6 text-sm text-foreground-muted">
                  Could not load watchlist.
                </td>
              </tr>
            ) : (
              tickers.map((ticker) => (
                <WatchlistRow
                  key={ticker}
                  ticker={ticker}
                  onSelect={setSelectedTicker}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </aside>
  );
}
