'use client';

/**
 * Main chart panel: shows the currently selected ticker as a line series.
 * When selectedTicker is null, renders an empty-state message instead.
 * Decision refs: 07-UI-SPEC §5.3; 07-RESEARCH §3 Pattern 3;
 * CONTEXT.md "Claude's Discretion" — main chart content.
 */

import { useEffect, useRef } from 'react';
import {
  createChart, LineSeries,
  type IChartApi, type ISeriesApi, type UTCTimestamp,
} from 'lightweight-charts';
import {
  selectSelectedTicker,
  usePriceStore,
} from '@/lib/price-store';

export function MainChart() {
  const selectedTicker = usePriceStore(selectSelectedTicker);
  const buffer = usePriceStore((s) =>
    selectedTicker ? s.sparklineBuffers[selectedTicker] : undefined,
  );
  const tick = usePriceStore((s) =>
    selectedTicker ? s.prices[selectedTicker] : undefined,
  );

  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!selectedTicker || !containerRef.current || chartRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: 'solid', color: '#0d1117' } as never,
        textColor: '#e6edf3',
      },
      grid: {
        vertLines: { color: '#30363d' },
        horzLines: { color: '#30363d' },
      },
    });
    const series = chart.addSeries(LineSeries, {
      color: '#26a69a',
      lineWidth: 2,
    });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [selectedTicker]);

  useEffect(() => {
    const s = seriesRef.current;
    if (!s || !selectedTicker || !buffer || buffer.length === 0) return;
    const now = Math.floor(Date.now() / 1000);
    const data = buffer.map((v, i) => ({
      time: (now - (buffer.length - 1 - i)) as UTCTimestamp,
      value: v,
    }));
    s.setData(data);
  }, [selectedTicker, buffer]);

  useEffect(() => {
    const s = seriesRef.current;
    if (!s || !tick) return;
    const positive = tick.price >= tick.session_start_price;
    s.applyOptions({ color: positive ? '#26a69a' : '#ef5350' });
  }, [tick]);

  if (!selectedTicker) {
    return (
      <section className="flex-1 bg-surface border border-border-muted rounded p-4 min-h-[400px] flex items-center justify-center">
        <p className="text-sm text-foreground-muted text-center">
          Select a ticker from the watchlist to view its chart.
        </p>
      </section>
    );
  }

  return (
    <section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
      <header className="flex items-baseline gap-4 mb-3">
        <h2 className="text-xl font-semibold">Chart: {selectedTicker}</h2>
        {tick && (
          <span className="font-mono tabular-nums text-sm text-foreground-muted">
            ${tick.price.toFixed(2)}
          </span>
        )}
      </header>
      <div ref={containerRef} className="flex-1 w-full" />
    </section>
  );
}
