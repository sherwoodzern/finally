import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';

const mockSeries = { setData: vi.fn(), update: vi.fn(), applyOptions: vi.fn() };
const mockChart = {
  addSeries: vi.fn(() => mockSeries),
  remove: vi.fn(),
  applyOptions: vi.fn(),
};

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => mockChart),
  LineSeries: 'LineSeries',
}));

import { MainChart } from './MainChart';
import { usePriceStore } from '@/lib/price-store';
import type { RawPayload } from '@/lib/sse-types';
import * as lwc from 'lightweight-charts';

function payload(ticker: string, price: number, prev = price): RawPayload {
  return {
    ticker, price, previous_price: prev, timestamp: 1_700_000_000,
    change: +(price - prev).toFixed(4),
    change_percent: prev ? +((price - prev) / prev * 100).toFixed(4) : 0,
    direction: price > prev ? 'up' : price < prev ? 'down' : 'flat',
  };
}

describe('<MainChart />', () => {
  beforeEach(() => {
    mockSeries.setData.mockClear();
    mockSeries.update.mockClear();
    mockSeries.applyOptions.mockClear();
    mockChart.addSeries.mockClear();
    mockChart.remove.mockClear();
    (lwc.createChart as ReturnType<typeof vi.fn>).mockClear();
    usePriceStore.getState().reset();
  });

  it('renders empty-state copy when no ticker is selected', () => {
    render(<MainChart />);
    expect(
      screen.getByText(
        'Select a ticker from the watchlist to view its chart.',
      ),
    ).toBeInTheDocument();
    expect(lwc.createChart).not.toHaveBeenCalled();
  });

  it('creates chart + addSeries(LineSeries, ...) when a ticker is selected', () => {
    act(() => {
      usePriceStore.getState().setSelectedTicker('AAPL');
    });
    render(<MainChart />);
    expect(lwc.createChart).toHaveBeenCalledTimes(1);
    expect(mockChart.addSeries).toHaveBeenCalledTimes(1);
    const [firstArg, secondArg] = mockChart.addSeries.mock.calls[0];
    expect(firstArg).toBe('LineSeries');
    expect(secondArg).toMatchObject({ color: '#26a69a', lineWidth: 2 });
  });

  it('renders h2 "Chart: AAPL" when AAPL selected', () => {
    act(() => {
      usePriceStore.getState().setSelectedTicker('AAPL');
    });
    render(<MainChart />);
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(
      'Chart: AAPL',
    );
  });

  it('calls series.setData when buffer has data for selected ticker', () => {
    act(() => {
      usePriceStore.getState().ingest({ AAPL: payload('AAPL', 190) });
      usePriceStore.getState().ingest({ AAPL: payload('AAPL', 195, 190) });
      usePriceStore.getState().setSelectedTicker('AAPL');
    });
    render(<MainChart />);
    expect(mockSeries.setData).toHaveBeenCalled();
    const data = mockSeries.setData.mock.calls[0][0];
    expect(data.map((p: { value: number }) => p.value)).toEqual([190, 195]);
  });

  it('calls chart.remove on unmount', () => {
    act(() => {
      usePriceStore.getState().setSelectedTicker('AAPL');
    });
    const { unmount } = render(<MainChart />);
    expect(mockChart.remove).not.toHaveBeenCalled();
    unmount();
    expect(mockChart.remove).toHaveBeenCalledTimes(1);
  });
});
