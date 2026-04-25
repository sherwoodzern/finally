'use client';

/**
 * 80x32 Lightweight Charts v5 micro-chart for a watchlist row.
 * Stroke color flips on sign-flip via applyOptions (no chart recreation).
 * Decision refs: D-04; 07-UI-SPEC §7; 07-RESEARCH §3 Pattern 3 + Pattern 4.
 */

import { useEffect, useRef } from 'react';
import {
  createChart, LineSeries,
  type IChartApi, type ISeriesApi, type UTCTimestamp,
} from 'lightweight-charts';

export function Sparkline({
  buffer,
  positive,
}: {
  buffer: number[] | undefined;
  positive: boolean;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: 'solid', color: 'transparent' } as never,
        textColor: 'transparent',
      },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: false },
      timeScale: { visible: false, borderVisible: false },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      crosshair: {
        horzLine: { visible: false },
        vertLine: { visible: false },
      },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addSeries(LineSeries, {
      color: positive ? '#26a69a' : '#ef5350',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    seriesRef.current?.applyOptions({
      color: positive ? '#26a69a' : '#ef5350',
    });
  }, [positive]);

  useEffect(() => {
    const s = seriesRef.current;
    if (!s || !buffer || buffer.length === 0) return;
    const now = Math.floor(Date.now() / 1000);
    const data = buffer.map((v, i) => ({
      time: (now - (buffer.length - 1 - i)) as UTCTimestamp,
      value: v,
    }));
    s.setData(data);
  }, [buffer]);

  return <div ref={containerRef} className="h-8 w-20" />;
}
