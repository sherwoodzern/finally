import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ActionCard } from './ActionCard';

describe('<ActionCard />', () => {
  it('executed trade: green border + text-up (D-11)', () => {
    const { getByTestId } = render(
      <ActionCard kind="trade" action={{ ticker: 'AAPL', side: 'buy', quantity: 10, status: 'executed', price: 200 }} />,
    );
    const card = getByTestId('action-card-executed');
    expect(card.className).toContain('border-l-up');
    expect(screen.getByText('executed').className).toContain('text-up');
  });

  it('failed trade: red border + text-down + mapped error string (D-11)', () => {
    const { getByTestId } = render(
      <ActionCard kind="trade" action={{ ticker: 'GOOGL', side: 'sell', quantity: 999, status: 'failed', error: 'insufficient_shares' }} />,
    );
    const card = getByTestId('action-card-failed');
    expect(card.className).toContain('border-l-down');
    expect(screen.getByText('failed').className).toContain('text-down');
    expect(screen.getByText("You don't have that many shares to sell.")).toBeInTheDocument();
  });

  it('exists / not_present: muted gray border (D-11 idempotent)', () => {
    const { getByTestId, rerender } = render(
      <ActionCard kind="watchlist" action={{ ticker: 'AAPL', action: 'add', status: 'exists' }} />,
    );
    let card = getByTestId('action-card-exists');
    expect(card.className).toContain('border-l-foreground-muted');
    expect(screen.getByText('already there').className).toContain('text-foreground-muted');

    rerender(<ActionCard kind="watchlist" action={{ ticker: 'XXXX', action: 'remove', status: 'not_present' }} />);
    card = getByTestId('action-card-not_present');
    expect(card.className).toContain('border-l-foreground-muted');
    expect(screen.getByText("wasn't there")).toBeInTheDocument();
  });

  it('failed unknown error code → DEFAULT_ERROR string', () => {
    render(
      <ActionCard kind="trade" action={{ ticker: 'AAPL', side: 'buy', quantity: 1, status: 'failed', error: 'mystery_code' }} />,
    );
    expect(screen.getByText('Something went wrong. Try again.')).toBeInTheDocument();
  });
});
