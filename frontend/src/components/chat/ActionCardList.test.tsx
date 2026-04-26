import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { ActionCardList } from './ActionCardList';

describe('<ActionCardList />', () => {
  it('renders watchlist_changes BEFORE trades (D-09 / D-10 order)', () => {
    const { container } = render(
      <ActionCardList
        actions={{
          watchlist_changes: [{ ticker: 'PYPL', action: 'add', status: 'added' }],
          trades: [{ ticker: 'AAPL', side: 'buy', quantity: 1, status: 'executed', price: 200 }],
        }}
      />,
    );
    // Filter to per-card testids only — the list wrapper also has testid="action-card-list"
    // which would match the prefix `action-card-` selector.
    const cards = Array.from(
      container.querySelectorAll<HTMLElement>('[data-testid^="action-card-"]'),
    ).filter((el) => el.dataset.testid !== 'action-card-list');
    expect(cards).toHaveLength(2);
    // First card should be the watchlist add (PYPL); second the trade (AAPL).
    expect(cards[0].textContent ?? '').toContain('Add');
    expect(cards[0].textContent ?? '').toContain('PYPL');
    expect(cards[1].textContent ?? '').toContain('Buy');
    expect(cards[1].textContent ?? '').toContain('AAPL');
  });

  it('renders nothing when both arrays are empty', () => {
    const { container } = render(<ActionCardList actions={{ watchlist_changes: [], trades: [] }} />);
    expect(container.querySelector('[data-testid="action-card-list"]')).toBeNull();
  });
});
