import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';

const mockSeries = { setData: vi.fn(), update: vi.fn(), applyOptions: vi.fn() };
const mockChart = { addSeries: vi.fn(() => mockSeries), remove: vi.fn(), applyOptions: vi.fn() };
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => mockChart),
  LineSeries: 'LineSeries',
}));

import { usePriceStore } from '@/lib/price-store';
import type { RawPayload } from '@/lib/sse-types';
import { WatchlistRow } from './WatchlistRow';

function payload(ticker: string, price: number, prev = price): RawPayload {
  return {
    ticker, price, previous_price: prev, timestamp: 1_700_000_000,
    change: +(price - prev).toFixed(4),
    change_percent: prev ? +((price - prev) / prev * 100).toFixed(4) : 0,
    direction: price > prev ? 'up' : price < prev ? 'down' : 'flat',
  };
}

function wrap(node: ReactNode) {
  return <table><tbody>{node}</tbody></table>;
}

describe('<WatchlistRow />', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders em-dash when no tick has arrived', () => {
    render(wrap(<WatchlistRow ticker="AAPL" onSelect={() => {}} />));
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    const cells = screen.getAllByText('—');
    expect(cells.length).toBeGreaterThanOrEqual(2);
  });

  it('renders signed daily-% and $price after tick', () => {
    usePriceStore.getState().ingest({ AAPL: payload('AAPL', 200) });
    render(wrap(<WatchlistRow ticker="AAPL" onSelect={() => {}} />));
    expect(screen.getByText('+0.00%')).toBeInTheDocument();
    expect(screen.getByText('$200.00')).toBeInTheDocument();
  });

  it('applies bg-up/10 when flashDirection is "up"', () => {
    usePriceStore.getState().ingest({ AAPL: payload('AAPL', 200) });
    usePriceStore.getState().ingest({ AAPL: payload('AAPL', 210, 200) });
    const { container } = render(wrap(<WatchlistRow ticker="AAPL" onSelect={() => {}} />));
    const row = container.querySelector('tr');
    expect(row?.className).toContain('bg-up/10');
    expect(row?.className).toContain('transition-colors');
    expect(row?.className).toContain('duration-500');
  });

  it('applies bg-down/10 when flashDirection is "down"', () => {
    usePriceStore.getState().ingest({ AAPL: payload('AAPL', 200) });
    usePriceStore.getState().ingest({ AAPL: payload('AAPL', 190, 200) });
    const { container } = render(wrap(<WatchlistRow ticker="AAPL" onSelect={() => {}} />));
    const row = container.querySelector('tr');
    expect(row?.className).toContain('bg-down/10');
  });

  it('calls onSelect(ticker) on click', () => {
    const onSelect = vi.fn();
    const { container } = render(wrap(<WatchlistRow ticker="AAPL" onSelect={onSelect} />));
    const row = container.querySelector('tr')!;
    fireEvent.click(row);
    expect(onSelect).toHaveBeenCalledWith('AAPL');
  });

  it('daily-% = (price - session_start) / session_start * 100', () => {
    usePriceStore.getState().ingest({ AAPL: payload('AAPL', 100) });
    usePriceStore.getState().ingest({ AAPL: payload('AAPL', 105, 100) });
    render(wrap(<WatchlistRow ticker="AAPL" onSelect={() => {}} />));
    expect(screen.getByText('+5.00%')).toBeInTheDocument();
  });
});
