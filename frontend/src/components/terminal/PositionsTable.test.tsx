import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test-utils';
import { PositionsTable } from './PositionsTable';
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

function stubPortfolio(body: unknown, ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok,
      status: ok ? 200 : 500,
      json: () => Promise.resolve(body),
    }),
  );
}

describe('<PositionsTable />', () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders loading state initially', () => {
    stubPortfolio({ cash_balance: 0, total_value: 0, positions: [] });
    renderWithQuery(<PositionsTable />);
    expect(screen.getByText('Loading positions…')).toBeInTheDocument();
  });

  it('renders empty state when no positions returned', async () => {
    stubPortfolio({ cash_balance: 10000, total_value: 10000, positions: [] });
    renderWithQuery(<PositionsTable />);
    await waitFor(() =>
      expect(
        screen.getByText('No positions yet — use the trade bar to buy shares.'),
      ).toBeInTheDocument(),
    );
  });

  it('renders error state on non-OK response', async () => {
    stubPortfolio({}, false);
    renderWithQuery(<PositionsTable />);
    await waitFor(() =>
      expect(
        screen.getByText("Couldn't load positions. Retrying in 15s."),
      ).toBeInTheDocument(),
    );
  });

  it('renders one row per position with client-side P&L from store tick', async () => {
    stubPortfolio({
      cash_balance: 8000,
      total_value: 10000,
      positions: [
        {
          ticker: 'AAPL',
          quantity: 10,
          avg_cost: 190,
          current_price: 190,
          unrealized_pnl: 0,
          change_percent: 0,
        },
      ],
    });
    usePriceStore.getState().ingest({ AAPL: payload('AAPL', 195) });

    renderWithQuery(<PositionsTable />);

    await waitFor(() =>
      expect(screen.getByText('AAPL')).toBeInTheDocument(),
    );
    expect(screen.getByText('+$50.00')).toBeInTheDocument();
    expect(screen.getByText(/\+2\.63%/)).toBeInTheDocument();
    expect(screen.getByText('$195.00')).toBeInTheDocument();
  });

  it('cold-start fallback uses backend unrealized_pnl when store has no tick', async () => {
    stubPortfolio({
      cash_balance: 8000,
      total_value: 10000,
      positions: [
        {
          ticker: 'AAPL',
          quantity: 10,
          avg_cost: 190,
          current_price: 190.5,
          unrealized_pnl: 5.0,
          change_percent: 0.2631,
        },
      ],
    });
    renderWithQuery(<PositionsTable />);

    await waitFor(() =>
      expect(screen.getByText('AAPL')).toBeInTheDocument(),
    );
    expect(screen.getByText('+$5.00')).toBeInTheDocument();
    expect(screen.getByText('$190.50')).toBeInTheDocument();
  });

  it('sorts rows by weight descending (qty * current_price)', async () => {
    stubPortfolio({
      cash_balance: 0,
      total_value: 10000,
      positions: [
        { ticker: 'AAPL',  quantity: 1,   avg_cost: 100, current_price: 100, unrealized_pnl: 0, change_percent: 0 },
        { ticker: 'GOOGL', quantity: 10,  avg_cost: 100, current_price: 100, unrealized_pnl: 0, change_percent: 0 },
        { ticker: 'MSFT',  quantity: 5,   avg_cost: 100, current_price: 100, unrealized_pnl: 0, change_percent: 0 },
      ],
    });
    const { container } = renderWithQuery(<PositionsTable />);
    await waitFor(() =>
      expect(screen.getByText('GOOGL')).toBeInTheDocument(),
    );
    const rows = container.querySelectorAll('tbody tr');
    const firstCells = Array.from(rows).map(
      (tr) => tr.querySelector('td:first-child')?.textContent,
    );
    expect(firstCells).toEqual(['GOOGL', 'MSFT', 'AAPL']);
  });
});
