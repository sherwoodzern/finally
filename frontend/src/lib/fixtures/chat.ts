import type { HistoryResponse } from '@/lib/api/chat';

/** 4 messages (2 user, 2 assistant) covering all 6 action statuses. */
export const chatHistoryFixture: HistoryResponse = {
  messages: [
    { id: 'm1', role: 'user', content: 'Buy 10 AAPL', created_at: '2026-04-25T10:00:00Z', actions: null },
    {
      id: 'm2', role: 'assistant', content: 'Bought 10 AAPL.', created_at: '2026-04-25T10:00:01Z',
      actions: {
        watchlist_changes: [],
        trades: [
          { ticker: 'AAPL', side: 'buy', quantity: 10, status: 'executed', price: 200, executed_at: '2026-04-25T10:00:01Z' },
        ],
      },
    },
    { id: 'm3', role: 'user', content: 'Add PYPL, remove TSLA, sell 999 GOOGL', created_at: '2026-04-25T10:01:00Z', actions: null },
    {
      id: 'm4', role: 'assistant', content: 'Done some, failed others.', created_at: '2026-04-25T10:01:02Z',
      actions: {
        watchlist_changes: [
          { ticker: 'PYPL', action: 'add',    status: 'added' },
          { ticker: 'AAPL', action: 'add',    status: 'exists' },
          { ticker: 'TSLA', action: 'remove', status: 'removed' },
          { ticker: 'XXXX', action: 'remove', status: 'not_present' },
          { ticker: 'BAD$', action: 'add',    status: 'failed', error: 'invalid_ticker' },
        ],
        trades: [
          { ticker: 'GOOGL', side: 'sell', quantity: 999, status: 'failed', error: 'insufficient_shares' },
        ],
      },
    },
  ],
};
