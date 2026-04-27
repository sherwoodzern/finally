'use client';

/**
 * Header strip: connection dot + live total portfolio value + cash balance.
 * Total recomputes on every store tick: cash + sum(qty * store_price).
 * Shares the ['portfolio'] cache with PositionsTable.
 * Decision refs: 07-UI-SPEC §5.6; CONTEXT.md "Claude's Discretion" Header live totals.
 */

import { useQuery } from '@tanstack/react-query';
import { fetchPortfolio } from '@/lib/api/portfolio';
import { usePriceStore } from '@/lib/price-store';
import { ConnectionDot } from './ConnectionDot';

function formatMoney(v: number): string {
  return `$${v.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function Header() {
  const { data } = useQuery({
    queryKey: ['portfolio'],
    queryFn: fetchPortfolio,
    refetchInterval: 15_000,
  });
  const prices = usePriceStore((s) => s.prices);

  const cashBalance = data?.cash_balance ?? 0;
  const totalValue =
    cashBalance +
    (data?.positions ?? []).reduce(
      (sum, p) => sum + p.quantity * (prices[p.ticker]?.price ?? p.avg_cost),
      0,
    );

  return (
    <header className="h-16 bg-surface-alt border border-border-muted rounded px-4 flex items-center gap-6">
      <ConnectionDot />
      <div className="flex items-baseline gap-2">
        <span className="text-sm text-foreground-muted">Total</span>
        <span className="font-mono tabular-nums text-lg" data-testid="header-total">
          {formatMoney(totalValue)}
        </span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-sm text-foreground-muted">Cash</span>
        <span className="font-mono tabular-nums text-lg" data-testid="header-cash">
          {formatMoney(cashBalance)}
        </span>
      </div>
    </header>
  );
}
