'use client';

/**
 * Right-column top panel: positions table driven by useQuery(['portfolio']).
 * Rows are sorted by weight descending (quantity * current_price) on every render.
 * Shares the cache with Header and is invalidated by TradeBar on successful trades.
 * Decision refs: 07-UI-SPEC §5.4; CONTEXT.md "Claude's Discretion" Portfolio data flow.
 */

import { useQuery } from '@tanstack/react-query';
import { fetchPortfolio } from '@/lib/api/portfolio';
import { PositionRow } from './PositionRow';

export function PositionsTable() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['portfolio'],
    queryFn: fetchPortfolio,
    refetchInterval: 15_000,
  });

  const positions = data?.positions ?? [];
  const sorted = [...positions].sort(
    (a, b) =>
      b.quantity * b.current_price - a.quantity * a.current_price,
  );

  return (
    <section
      className="flex-1 bg-surface border border-border-muted rounded overflow-hidden flex flex-col min-h-[240px]"
      data-testid="positions-table"
    >
      <h2 className="text-xl font-semibold px-4 py-3 border-b border-border-muted">
        Positions
      </h2>
      <div className="overflow-y-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-sm text-foreground-muted">
              <th className="text-left px-4 py-2 border-b border-border-muted">
                Ticker
              </th>
              <th className="text-right px-2 py-2 border-b border-border-muted">
                Qty
              </th>
              <th className="text-right px-2 py-2 border-b border-border-muted">
                Avg Cost
              </th>
              <th className="text-right px-2 py-2 border-b border-border-muted">
                Price
              </th>
              <th className="text-right px-2 py-2 border-b border-border-muted">
                P&amp;L
              </th>
              <th className="text-right px-4 py-2 border-b border-border-muted">
                %
              </th>
            </tr>
          </thead>
          <tbody>
            {isPending ? (
              <tr>
                <td
                  colSpan={6}
                  className="text-center py-6 text-sm text-foreground-muted"
                >
                  Loading positions…
                </td>
              </tr>
            ) : isError ? (
              <tr>
                <td
                  colSpan={6}
                  className="text-center py-6 text-sm text-foreground-muted"
                >
                  Couldn&apos;t load positions. Retrying in 15s.
                </td>
              </tr>
            ) : sorted.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="text-center py-6 text-sm text-foreground-muted"
                >
                  No positions yet — use the trade bar to buy shares.
                </td>
              </tr>
            ) : (
              sorted.map((p) => <PositionRow key={p.ticker} position={p} />)
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
