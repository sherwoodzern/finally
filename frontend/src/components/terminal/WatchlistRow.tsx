'use client';

/**
 * One watchlist row: ticker (bold) + daily-% (signed, colored) + price + sparkline.
 * Subscribes to three narrow selectors so unrelated tickers do not re-render.
 * Decision refs: D-01 (flash), D-02 (up/down colors), D-03 (sparkline buffer);
 * 07-UI-SPEC §5.2 row contract; 07-PATTERNS Pattern C narrow selector.
 */

import {
  selectFlash,
  selectSparkline,
  selectTick,
  usePriceStore,
} from '@/lib/price-store';
import { Sparkline } from './Sparkline';

export function WatchlistRow({
  ticker,
  onSelect,
}: {
  ticker: string;
  onSelect: (t: string) => void;
}) {
  const tick = usePriceStore(selectTick(ticker));
  const flash = usePriceStore(selectFlash(ticker));
  const buffer = usePriceStore(selectSparkline(ticker));

  const flashClass =
    flash === 'up'
      ? 'bg-up/10'
      : flash === 'down'
        ? 'bg-down/10'
        : '';

  const dailyPct = tick
    ? ((tick.price - tick.session_start_price) / tick.session_start_price) * 100
    : 0;
  const pctClass = dailyPct >= 0 ? 'text-up' : 'text-down';

  return (
    <tr
      onClick={() => onSelect(ticker)}
      tabIndex={0}
      role="button"
      aria-label={`Select ${ticker}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(ticker);
        }
      }}
      className={`h-14 border-b border-border-muted cursor-pointer transition-colors duration-500 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent-blue ${flashClass}`}
    >
      <td className="px-4 font-semibold">{ticker}</td>
      <td
        className={`px-2 font-mono tabular-nums text-right text-sm ${pctClass}`}
      >
        {tick ? `${dailyPct >= 0 ? '+' : ''}${dailyPct.toFixed(2)}%` : '—'}
      </td>
      <td className="px-2 font-mono tabular-nums text-right text-sm">
        {tick ? `$${tick.price.toFixed(2)}` : '—'}
      </td>
      <td className="px-2 w-[96px]">
        <Sparkline buffer={buffer} positive={dailyPct >= 0} />
      </td>
    </tr>
  );
}
