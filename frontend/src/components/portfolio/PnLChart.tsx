'use client';

/**
 * FE-06 P&L Line Chart — Recharts LineChart over /api/portfolio/history,
 * dotted $10k reference line, stroke flips at break-even.
 * Decision refs: CONTEXT.md D-04, D-05, D-06; UI-SPEC §5.4; PATTERNS.md "PnLChart.tsx".
 */

import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getPortfolioHistory } from '@/lib/api/portfolio';
import { PnLTooltip } from './PnLTooltip';

function formatMoney(value: number): string {
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 });
}

function formatSignedMoney(delta: number): string {
  const sign = delta >= 0 ? '+' : '-';
  return `${sign}${formatMoney(Math.abs(delta))}`;
}

function tickTime(value: string): string {
  return new Date(value).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function tickMoney(value: number): string {
  return `$${Math.round(value).toLocaleString('en-US')}`;
}

export function PnLChart() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['portfolio', 'history'],
    queryFn: getPortfolioHistory,
    refetchInterval: 15_000,
  });

  const snapshots = data?.snapshots ?? [];
  const lastTotal = snapshots[snapshots.length - 1]?.total_value ?? 10000;
  const stroke = lastTotal >= 10000 ? 'var(--color-up)' : 'var(--color-down)';

  const panelChrome = (body: ReactNode) => (
    <section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
      <header className="flex items-baseline gap-4 mb-3">
        <h2 className="text-xl font-semibold">P&amp;L</h2>
        {snapshots.length > 0 && (
          <span
            className="font-mono tabular-nums text-sm text-foreground-muted"
            data-testid="pnl-summary"
          >
            {formatMoney(lastTotal)} ({formatSignedMoney(lastTotal - 10000)} vs $10k)
          </span>
        )}
      </header>
      {body}
    </section>
  );

  const skeleton = (
    <div data-testid="pnl-skeleton" className="flex-1 bg-border-muted/50 rounded animate-pulse" />
  );

  if (isPending) return panelChrome(skeleton);
  if (isError) {
    return panelChrome(
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-foreground-muted">Couldn&apos;t load P&amp;L history. Retrying in 15s.</p>
      </div>,
    );
  }
  if (snapshots.length === 0) return panelChrome(skeleton);
  if (snapshots.length === 1) {
    return panelChrome(
      <div className="flex-1 flex items-center justify-center text-center">
        <p className="text-sm text-foreground-muted max-w-xs">
          Building P&amp;L history… your first snapshot is in. The next one will arrive within 60s or right after your next trade.
        </p>
      </div>,
    );
  }

  return panelChrome(
    <div className="flex-1 w-full" data-testid="pnl-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={snapshots}>
          <CartesianGrid stroke="#30363d" strokeDasharray="2 2" />
          <XAxis dataKey="recorded_at" stroke="#8b949e" tickFormatter={tickTime} />
          <YAxis stroke="#8b949e" tickFormatter={tickMoney} domain={['auto', 'auto']} />
          <ReferenceLine
            y={10000}
            stroke="#8b949e"
            strokeDasharray="4 4"
            strokeOpacity={0.4}
          />
          <Tooltip content={<PnLTooltip />} />
          <Line
            type="monotone"
            dataKey="total_value"
            stroke={stroke}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>,
  );
}

export { formatMoney, formatSignedMoney };
