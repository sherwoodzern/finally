'use client';

/**
 * One positions table row. Client-side P&L from store tick; backend
 * unrealized_pnl/change_percent used only when the store has no tick yet
 * (cold start). Click selects the ticker in the MainChart.
 * Decision refs: CONTEXT.md "Claude's Discretion" Portfolio data flow;
 * 07-UI-SPEC §5.4; 07-PATTERNS.md §PositionRow.
 */

import { selectFlash, selectTick, selectTradeFlash, usePriceStore } from '@/lib/price-store';
import type { PositionOut } from '@/lib/api/portfolio';

export function PositionRow({ position }: { position: PositionOut }) {
  const tick = usePriceStore(selectTick(position.ticker));
  const flash = usePriceStore(selectFlash(position.ticker));
  const tradeFlash = usePriceStore(selectTradeFlash(position.ticker));

  const price = tick?.price ?? position.current_price;
  const pnl = tick
    ? (tick.price - position.avg_cost) * position.quantity
    : position.unrealized_pnl;
  const pct = tick
    ? ((tick.price - position.avg_cost) / position.avg_cost) * 100
    : position.change_percent;

  const flashClass =
    flash === 'up'
      ? 'bg-up/10'
      : flash === 'down'
        ? 'bg-down/10'
        : '';
  const tradeFlashClass =
    tradeFlash === 'up'
      ? 'bg-up/20'
      : tradeFlash === 'down'
        ? 'bg-down/20'
        : '';
  const pnlColor = pnl >= 0 ? 'text-up' : 'text-down';

  return (
    <tr
      onClick={() =>
        usePriceStore.getState().setSelectedTicker(position.ticker)
      }
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          usePriceStore.getState().setSelectedTicker(position.ticker);
        }
      }}
      tabIndex={0}
      role="button"
      aria-label={`Select ${position.ticker}`}
      className={`h-12 border-b border-border-muted cursor-pointer hover:bg-surface-alt transition-colors duration-500 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent-blue ${flashClass} ${tradeFlashClass}`}
    >
      <td className="px-4 font-semibold">{position.ticker}</td>
      <td className="px-2 font-mono tabular-nums text-right text-sm">
        {position.quantity}
      </td>
      <td className="px-2 font-mono tabular-nums text-right text-sm">
        ${position.avg_cost.toFixed(2)}
      </td>
      <td className="px-2 font-mono tabular-nums text-right text-sm">
        ${price.toFixed(2)}
      </td>
      <td
        className={`px-2 font-mono tabular-nums text-right text-sm ${pnlColor}`}
      >
        {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
      </td>
      <td
        className={`px-4 font-mono tabular-nums text-right text-sm ${pnlColor}`}
      >
        {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
      </td>
    </tr>
  );
}
