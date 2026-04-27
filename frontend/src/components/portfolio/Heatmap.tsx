'use client';

/**
 * FE-05 Portfolio Heatmap — Recharts Treemap, binary up/down coloring,
 * ticker+signed-P&L% labels, click-selects-ticker.
 * Decision refs: CONTEXT.md D-01, D-02, D-03; UI-SPEC §5.3; PATTERNS.md "Heatmap.tsx".
 */

import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, Tooltip, Treemap } from 'recharts';
import { useShallow } from 'zustand/react/shallow';
import { fetchPortfolio, type PositionOut } from '@/lib/api/portfolio';
import { usePriceStore } from '@/lib/price-store';
import { HeatmapCell } from './HeatmapCell';

interface TreeDatum {
  name: string;
  ticker: string;
  weight: number;
  pnlPct: number;
  isUp: boolean;
  isCold: boolean;
  [key: string]: string | number | boolean;
}

/**
 * Click handler exported so tests can invoke it directly without rendering Treemap
 * (jsdom geometry is fragile for SVG layouts). Reads `ticker` off the node Recharts
 * passes back and dispatches setSelectedTicker + setSelectedTab('chart').
 */
export function handleHeatmapCellClick(node: unknown): void {
  const t = (node as { ticker?: string } | null)?.ticker;
  if (typeof t === 'string' && t.length > 0) {
    usePriceStore.getState().setSelectedTicker(t);
    usePriceStore.getState().setSelectedTab('chart');
  }
}

export function buildTreeData(
  positions: PositionOut[],
  ticks: Record<string, number | undefined>,
): TreeDatum[] {
  return positions.map((p) => {
    const live = ticks[p.ticker];
    const isCold = live === undefined && p.current_price === 0;
    const price = live ?? (p.current_price > 0 ? p.current_price : p.avg_cost);
    const pnlPct =
      p.avg_cost > 0 ? ((price - p.avg_cost) / p.avg_cost) * 100 : 0;
    const weight = Math.max(p.quantity * price, 0.01);
    return {
      name: p.ticker,
      ticker: p.ticker,
      weight,
      pnlPct,
      isUp: pnlPct >= 0,
      isCold,
    };
  });
}

export function Heatmap() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['portfolio'],
    queryFn: fetchPortfolio,
    refetchInterval: 15_000,
  });
  const livePrices = usePriceStore(
    useShallow((s) => {
      const out: Record<string, number | undefined> = {};
      for (const p of data?.positions ?? []) {
        out[p.ticker] = s.prices[p.ticker]?.price;
      }
      return out;
    }),
  );

  const positions = data?.positions ?? [];

  if (isPending) {
    return (
      <section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
        <h2 className="text-xl font-semibold mb-3">Heatmap</h2>
        <div data-testid="heatmap-skeleton" className="flex-1 bg-border-muted/50 rounded animate-pulse" />
      </section>
    );
  }

  if (isError) {
    return (
      <section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
        <h2 className="text-xl font-semibold mb-3">Heatmap</h2>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-foreground-muted">Couldn&apos;t load portfolio. Retrying.</p>
        </div>
      </section>
    );
  }

  if (positions.length === 0) {
    return (
      <section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
        <h2 className="text-xl font-semibold mb-3">Heatmap</h2>
        <div className="flex-1 flex items-center justify-center text-center">
          <p className="text-sm text-foreground-muted max-w-xs">
            No positions yet — use the trade bar or ask the AI to buy something.
          </p>
        </div>
      </section>
    );
  }

  const treeData = buildTreeData(positions, livePrices);

  return (
    <section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
      <h2 className="text-xl font-semibold mb-3">Heatmap</h2>
      <div className="flex-1 w-full" data-testid="heatmap-treemap">
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={treeData}
            dataKey="weight"
            stroke="#30363d"
            content={<HeatmapCell />}
            isAnimationActive
            animationDuration={300}
            onClick={(node) => handleHeatmapCellClick(node)}
          >
            {/*
              Explicit Recharts Tooltip with wrapperStyle pointerEvents: 'none'.
              The default Treemap tooltip wrapper has pointer-events: auto and
              intercepts clicks on sibling tabs (10-VERIFICATION.md Mode A —
              failed all 3 browsers in 05-portfolio-viz). With pointerEvents:
              'none' the tooltip remains visible on hover but its wrapper no
              longer absorbs clicks targeted at neighbouring elements. This is
              also better production UX: a hover tooltip should never block a
              click on something else.
            */}
            <Tooltip wrapperStyle={{ pointerEvents: 'none' }} />
          </Treemap>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
