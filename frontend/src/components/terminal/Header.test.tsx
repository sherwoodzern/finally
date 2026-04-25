import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test-utils';
import { Header } from './Header';
import { usePriceStore } from '@/lib/price-store';
import type { RawPayload } from '@/lib/sse-types';

function payload(ticker: string, price: number, prev = price): RawPayload {
  return {
    ticker, price, previous_price: prev, timestamp: 1_700_000_000,
    change: +(price - prev).toFixed(4),
    change_percent: prev ? +((price - prev) / prev * 100).toFixed(4) : 0,
    direction: price > prev ? 'up' : price < prev ? 'down' : 'flat',
  };
}

function stubPortfolio(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(body),
    }),
  );
}

describe('<Header />', () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders Total and Cash labels', async () => {
    stubPortfolio({ cash_balance: 10000, total_value: 10000, positions: [] });
    renderWithQuery(<Header />);
    await waitFor(() =>
      expect(screen.getByText('Total')).toBeInTheDocument(),
    );
    expect(screen.getByText('Cash')).toBeInTheDocument();
  });

  it('total = cash + Σ(qty * store_price) and updates on tick', async () => {
    stubPortfolio({
      cash_balance: 8000,
      total_value: 10000,
      positions: [
        {
          ticker: 'AAPL', quantity: 10, avg_cost: 190, current_price: 200,
          unrealized_pnl: 100, change_percent: 5,
        },
      ],
    });
    act(() => {
      usePriceStore.getState().ingest({ AAPL: payload('AAPL', 200) });
    });

    renderWithQuery(<Header />);
    await waitFor(() =>
      expect(screen.getByText('$10,000.00')).toBeInTheDocument(),
    );

    act(() => {
      usePriceStore.getState().ingest({ AAPL: payload('AAPL', 210, 200) });
    });
    await waitFor(() =>
      expect(screen.getByText('$10,100.00')).toBeInTheDocument(),
    );
  });

  it('cold-start fallback: uses avg_cost when no tick in store', async () => {
    stubPortfolio({
      cash_balance: 8000,
      total_value: 10000,
      positions: [
        {
          ticker: 'AAPL', quantity: 10, avg_cost: 200, current_price: 200,
          unrealized_pnl: 0, change_percent: 0,
        },
      ],
    });
    renderWithQuery(<Header />);
    await waitFor(() =>
      expect(screen.getByText('$10,000.00')).toBeInTheDocument(),
    );
  });

  it('renders ConnectionDot with bg-up when connected', async () => {
    stubPortfolio({ cash_balance: 0, total_value: 0, positions: [] });
    act(() => {
      usePriceStore.setState({ status: 'connected' });
    });
    const { container } = renderWithQuery(<Header />);
    await waitFor(() => {
      const span = container.querySelector('span[aria-label="SSE connected"]');
      expect(span).not.toBeNull();
      expect(span?.className).toContain('bg-up');
    });
  });

  it('renders ConnectionDot with bg-accent-yellow when reconnecting', async () => {
    stubPortfolio({ cash_balance: 0, total_value: 0, positions: [] });
    act(() => {
      usePriceStore.setState({ status: 'reconnecting' });
    });
    const { container } = renderWithQuery(<Header />);
    await waitFor(() => {
      const span = container.querySelector('span[aria-label="SSE reconnecting"]');
      expect(span).not.toBeNull();
      expect(span?.className).toContain('bg-accent-yellow');
    });
  });

  it('renders ConnectionDot with bg-down when disconnected', async () => {
    stubPortfolio({ cash_balance: 0, total_value: 0, positions: [] });
    act(() => {
      usePriceStore.setState({ status: 'disconnected' });
    });
    const { container } = renderWithQuery(<Header />);
    await waitFor(() => {
      const span = container.querySelector('span[aria-label="SSE disconnected"]');
      expect(span).not.toBeNull();
      expect(span?.className).toContain('bg-down');
    });
  });
});
