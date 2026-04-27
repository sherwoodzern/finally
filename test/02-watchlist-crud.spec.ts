// test/02-watchlist-crud.spec.ts
// PLAN.md §12 row 2 — watchlist add+remove via REST through the running container.
// Uses Playwright's `request` fixture (NOT `page`) — no browser process spawned.
// PYPL chosen per D-08: NOT in the default seed (AAPL, GOOGL, MSFT, AMZN, TSLA,
// NVDA, META, JPM, V, NFLX) and not used by any other §12 spec.

import { test, expect } from '@playwright/test';

test('watchlist CRUD: add then remove PYPL via REST', async ({ request }) => {
  // POST /api/watchlist -> { ticker: 'PYPL', status: 'added' | 'exists' }
  const add = await request.post('/api/watchlist', { data: { ticker: 'PYPL' } });
  expect(add.ok()).toBeTruthy();
  const addBody = await add.json();
  expect(addBody.status).toMatch(/^(added|exists)$/);

  // GET /api/watchlist -> verify PYPL appears in items[].ticker
  const list = await request.get('/api/watchlist');
  expect(list.ok()).toBeTruthy();
  const listBody = await list.json();
  const tickers = (listBody.items as Array<{ ticker: string }>).map((i) => i.ticker);
  expect(tickers).toContain('PYPL');

  // DELETE /api/watchlist/PYPL -> { ticker: 'PYPL', status: 'removed' | 'not_present' }
  const del = await request.delete('/api/watchlist/PYPL');
  expect(del.ok()).toBeTruthy();
  const delBody = await del.json();
  expect(delBody.status).toMatch(/^(removed|not_present)$/);
});
