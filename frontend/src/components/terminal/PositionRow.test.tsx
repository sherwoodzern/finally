import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PositionRow } from './PositionRow';
import { usePriceStore } from '@/lib/price-store';
import type { PositionOut } from '@/lib/api/portfolio';

const POSITION: PositionOut = {
  ticker: 'AAPL',
  quantity: 10,
  avg_cost: 150,
  current_price: 200,
  unrealized_pnl: 500,
  change_percent: 33.33,
};

function renderRow() {
  return render(
    <table>
      <tbody>
        <PositionRow position={POSITION} />
      </tbody>
    </table>,
  );
}

describe('<PositionRow /> — Phase 8 trade-flash + non-interference', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('applies bg-up/20 for ~800ms after flashTrade("AAPL","up") (FE-11 D-12)', () => {
    usePriceStore.getState().flashTrade('AAPL', 'up');
    renderRow();
    const row = screen.getByRole('button', { name: 'Select AAPL' });
    expect(row.className).toContain('bg-up/20');
    // After 800ms, slice clears.
    vi.advanceTimersByTime(801);
    expect(usePriceStore.getState().tradeFlash.AAPL).toBeUndefined();
  });

  it('500ms price-flash and 800ms trade-flash co-exist on the same row without interference (FE-11 D-12 distinctness)', () => {
    // Manually set both slices via the store to simulate concurrent flashes.
    usePriceStore.setState({
      flashDirection: { AAPL: 'up' },
      tradeFlash: { AAPL: 'up' },
    });
    renderRow();
    const row = screen.getByRole('button', { name: 'Select AAPL' });
    expect(row.className).toContain('bg-up/10'); // Phase 7 price flash
    expect(row.className).toContain('bg-up/20'); // Phase 8 trade flash
  });
});
