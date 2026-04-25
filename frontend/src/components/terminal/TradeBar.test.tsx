import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { useQuery } from '@tanstack/react-query';
import { renderWithQuery } from '@/test-utils';
import { TradeBar } from './TradeBar';

function stubFetch(impl: (url: string, init?: RequestInit) => Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn(impl));
  return fetch as unknown as ReturnType<typeof vi.fn>;
}

function fillAndClick(ticker: string, qty: string, side: 'Buy' | 'Sell') {
  const tickerInput = screen.getByPlaceholderText('AAPL') as HTMLInputElement;
  const qtyInput = screen.getByPlaceholderText('1') as HTMLInputElement;
  fireEvent.change(tickerInput, { target: { value: ticker } });
  fireEvent.change(qtyInput, { target: { value: qty } });
  fireEvent.click(screen.getByRole('button', { name: side }));
}

describe('<TradeBar />', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('renders Ticker + Quantity inputs + Buy + Sell buttons', () => {
    renderWithQuery(<TradeBar />);
    expect(screen.getByPlaceholderText('AAPL')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Buy' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sell' })).toBeInTheDocument();
  });

  it('rejects ticker not matching regex BEFORE fetching (unknown_ticker)', () => {
    const fetchMock = stubFetch(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response),
    );
    renderWithQuery(<TradeBar />);
    fillAndClick('hello world', '10', 'Buy');
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('No such ticker.');
  });

  it('POSTs {ticker, side, quantity} to /api/portfolio/trade on Buy', async () => {
    const fetchMock = stubFetch(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            ticker: 'AAPL', side: 'buy', quantity: 10, price: 190,
            cash_balance: 8100, position_quantity: 10, position_avg_cost: 190,
            executed_at: '2026-04-24T00:00:00+00:00',
          }),
      } as Response),
    );
    renderWithQuery(<TradeBar />);
    fillAndClick('AAPL', '10', 'Buy');
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/portfolio/trade');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(init!.body as string)).toEqual({
      ticker: 'AAPL', side: 'buy', quantity: 10,
    });
  });

  it('POSTs with side=sell on Sell click', async () => {
    const fetchMock = stubFetch(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            ticker: 'AAPL', side: 'sell', quantity: 5, price: 190,
            cash_balance: 10900, position_quantity: 5, position_avg_cost: 190,
            executed_at: '2026-04-24T00:00:00+00:00',
          }),
      } as Response),
    );
    renderWithQuery(<TradeBar />);
    fillAndClick('AAPL', '5', 'Sell');
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init!.body as string).side).toBe('sell');
  });

  it('maps insufficient_cash → "Not enough cash for that order."', async () => {
    stubFetch(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({
            detail: { error: 'insufficient_cash', message: 'not enough' },
          }),
      } as Response),
    );
    renderWithQuery(<TradeBar />);
    fillAndClick('AAPL', '1000', 'Buy');
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Not enough cash for that order.',
      ),
    );
  });

  it('maps insufficient_shares → "You don\'t have that many shares to sell."', async () => {
    stubFetch(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({
            detail: { error: 'insufficient_shares', message: 'nope' },
          }),
      } as Response),
    );
    renderWithQuery(<TradeBar />);
    fillAndClick('AAPL', '1000', 'Sell');
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        "You don't have that many shares to sell.",
      ),
    );
  });

  it('maps unknown_ticker → "No such ticker."', async () => {
    stubFetch(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({
            detail: { error: 'unknown_ticker', message: 'no' },
          }),
      } as Response),
    );
    renderWithQuery(<TradeBar />);
    fillAndClick('AAPL', '1', 'Buy');
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('No such ticker.'),
    );
  });

  it('maps price_unavailable → "Price unavailable right now — try again."', async () => {
    stubFetch(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({
            detail: { error: 'price_unavailable', message: 'cold' },
          }),
      } as Response),
    );
    renderWithQuery(<TradeBar />);
    fillAndClick('AAPL', '1', 'Buy');
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Price unavailable right now — try again.',
      ),
    );
  });

  it('falls back to default copy on unmapped code', async () => {
    stubFetch(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({
            detail: { error: 'some_new_code', message: '' },
          }),
      } as Response),
    );
    renderWithQuery(<TradeBar />);
    fillAndClick('AAPL', '1', 'Buy');
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Something went wrong. Try again.',
      ),
    );
  });

  it('on success: clears inputs and returns focus to ticker', async () => {
    stubFetch(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            ticker: 'AAPL', side: 'buy', quantity: 10, price: 190,
            cash_balance: 8100, position_quantity: 10, position_avg_cost: 190,
            executed_at: '2026-04-24T00:00:00+00:00',
          }),
      } as Response),
    );
    renderWithQuery(<TradeBar />);
    fillAndClick('AAPL', '10', 'Buy');

    const tickerInput = screen.getByPlaceholderText('AAPL') as HTMLInputElement;
    const qtyInput = screen.getByPlaceholderText('1') as HTMLInputElement;

    await waitFor(() => expect(tickerInput.value).toBe(''));
    expect(qtyInput.value).toBe('');
    expect(document.activeElement).toBe(tickerInput);
  });

  it('on success: invalidates ["portfolio"] (triggers re-fetch)', async () => {
    let portfolioCalls = 0;
    stubFetch((url) => {
      if (url === '/api/portfolio') {
        portfolioCalls += 1;
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({ cash_balance: 10000, total_value: 10000, positions: [] }),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            ticker: 'AAPL', side: 'buy', quantity: 10, price: 190,
            cash_balance: 8100, position_quantity: 10, position_avg_cost: 190,
            executed_at: '2026-04-24T00:00:00+00:00',
          }),
      } as Response);
    });

    function Primer() {
      useQuery({
        queryKey: ['portfolio'],
        queryFn: () => fetch('/api/portfolio').then((r) => r.json()),
      });
      return null;
    }

    renderWithQuery(
      <>
        <Primer />
        <TradeBar />
      </>,
    );

    await waitFor(() => expect(portfolioCalls).toBeGreaterThanOrEqual(1));
    const before = portfolioCalls;

    fillAndClick('AAPL', '10', 'Buy');
    await waitFor(() => expect(portfolioCalls).toBeGreaterThan(before));
  });
});
