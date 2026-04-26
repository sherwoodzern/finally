import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test-utils';
import { Heatmap, buildTreeData, handleHeatmapCellClick } from './Heatmap';
import { usePriceStore } from '@/lib/price-store';
import { portfolioFixture } from '@/lib/fixtures/portfolio';
import type { PortfolioResponse } from '@/lib/api/portfolio';

function stubPortfolio(body: PortfolioResponse | unknown, ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok,
      status: ok ? 200 : 500,
      json: () => Promise.resolve(body),
    }),
  );
}

describe('<Heatmap />', () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('builds one TreeDatum per position with binary coloring (FE-05)', () => {
    const data = buildTreeData(portfolioFixture.positions, {});
    expect(data).toHaveLength(3);
    const aapl = data.find((d) => d.ticker === 'AAPL');
    const googl = data.find((d) => d.ticker === 'GOOGL');
    expect(aapl?.isUp).toBe(true);
    expect(googl?.isUp).toBe(false);
  });

  it('weight = quantity * current_price (TEST-02 portfolio calculation)', () => {
    const data = buildTreeData(portfolioFixture.positions, {});
    const aapl = data.find((d) => d.ticker === 'AAPL');
    // AAPL: 10 * 200 = 2000
    expect(aapl?.weight).toBeCloseTo(2000, 5);
  });

  it('renders empty-state copy when positions.length === 0', async () => {
    stubPortfolio({ cash_balance: 10000, total_value: 10000, positions: [] });
    renderWithQuery(<Heatmap />);
    await waitFor(() =>
      expect(
        screen.getByText(/No positions yet — use the trade bar or ask the AI to buy something\./),
      ).toBeInTheDocument(),
    );
  });

  it('renders skeleton while query is pending (FE-11 D-13 + TEST-02)', () => {
    // never-resolving fetch
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    renderWithQuery(<Heatmap />);
    expect(screen.getByTestId('heatmap-skeleton')).toBeInTheDocument();
  });

  it('handleHeatmapCellClick(node) dispatches setSelectedTicker AND setSelectedTab("chart") (FE-05 click-to-select)', () => {
    handleHeatmapCellClick({ ticker: 'AAPL' });
    expect(usePriceStore.getState().selectedTicker).toBe('AAPL');
    expect(usePriceStore.getState().selectedTab).toBe('chart');
  });

  it('handleHeatmapCellClick ignores nodes with no ticker (defensive guard)', () => {
    usePriceStore.getState().setSelectedTab('heatmap'); // pre-set to a non-default
    handleHeatmapCellClick({});
    handleHeatmapCellClick(null);
    expect(usePriceStore.getState().selectedTab).toBe('heatmap');
    expect(usePriceStore.getState().selectedTicker).toBe(null);
  });

  it('buildTreeData detects cold-cache when live===undefined && current_price===0 (FE-05 cold-cache integration)', () => {
    const data = buildTreeData(portfolioFixture.positions, {});
    const nvda = data.find((d) => d.ticker === 'NVDA');
    expect(nvda?.isCold).toBe(true);
    // Cold-cache fallback price = avg_cost (520); weight = quantity * fallback price = 2 * 520 = 1040.
    expect(nvda?.weight).toBeCloseTo(1040, 5);
  });
});
