import { afterEach, describe, expect, it, vi } from 'vitest';
import { TradeError, fetchPortfolio, postTrade } from './portfolio';

describe('fetchPortfolio', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('returns parsed JSON on 200', async () => {
    const body = {
      cash_balance: 10000,
      total_value: 10234.56,
      positions: [
        {
          ticker: 'AAPL', quantity: 10, avg_cost: 190, current_price: 190.12,
          unrealized_pnl: 1.2, change_percent: 0.06,
        },
      ],
    };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(body),
    }));

    const data = await fetchPortfolio();
    expect(data.cash_balance).toBe(10000);
    expect(data.positions[0].ticker).toBe('AAPL');
    expect(fetch).toHaveBeenCalledWith('/api/portfolio');
  });

  it('throws Error on non-OK', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 500, json: () => Promise.resolve({}),
    }));
    await expect(fetchPortfolio()).rejects.toThrow('HTTP 500');
  });
});

describe('postTrade', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('POSTs JSON body and returns parsed TradeResponse on 200', async () => {
    const tradeResponse = {
      ticker: 'AAPL', side: 'buy', quantity: 10, price: 190.12,
      cash_balance: 8098.80, position_quantity: 10, position_avg_cost: 190.12,
      executed_at: '2026-04-24T16:30:00.000000+00:00',
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: () => Promise.resolve(tradeResponse),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await postTrade({ ticker: 'AAPL', side: 'buy', quantity: 10 });
    expect(result.cash_balance).toBe(8098.80);

    expect(fetchMock).toHaveBeenCalledWith('/api/portfolio/trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker: 'AAPL', side: 'buy', quantity: 10 }),
    });
  });

  it('throws TradeError with code from detail.error on 400', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 400,
      json: () => Promise.resolve({
        detail: { error: 'insufficient_cash', message: 'Need $1901.20, have $1500.00' },
      }),
    }));

    await expect(
      postTrade({ ticker: 'AAPL', side: 'buy', quantity: 100 }),
    ).rejects.toMatchObject({
      name: 'TradeError',
      code: 'insufficient_cash',
      message: 'Need $1901.20, have $1500.00',
    });
  });

  it('throws TradeError with code="unknown" when body is malformed', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 400,
      json: () => Promise.reject(new Error('not json')),
    }));

    await expect(
      postTrade({ ticker: 'AAPL', side: 'buy', quantity: 1 }),
    ).rejects.toMatchObject({ name: 'TradeError', code: 'unknown' });
  });

  it('TradeError exposes code field (not just message)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 400,
      json: () => Promise.resolve({
        detail: { error: 'price_unavailable', message: '' },
      }),
    }));
    try {
      await postTrade({ ticker: 'AAPL', side: 'buy', quantity: 1 });
      expect.fail('expected throw');
    } catch (err) {
      expect(err).toBeInstanceOf(TradeError);
      expect((err as TradeError).code).toBe('price_unavailable');
    }
  });
});
