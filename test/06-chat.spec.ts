// test/06-chat.spec.ts
// PLAN.md §12 row 6 — mocked chat with visible trade execution.
// Phase 10 plan 10-04. D-08 ticker isolation: AMZN (not used by 02/03/04/05).
//
// Mock LLM trigger: backend/app/chat/mock.py:12 BUY regex matches
// `\bbuy\s+([A-Z][A-Z0-9.]{0,9})\s+(\d+(?:\.\d+)?)\b`. Sending the literal
// string "buy AMZN 1" produces a TradeAction that the chat service
// auto-executes through the same validation pipeline as a manual TradeBar
// trade. The resulting status is rendered as `data-testid=action-card-{status}`
// (ActionCard.tsx:98).
//
// IMPORTANT — Pitfall 4 / CONTEXT.md D-05:
// Do NOT assert on [data-testid=chat-message-assistant] text content. The
// frontend reads `res.id` / `res.content` / `res.created_at` from the chat
// response, but the backend ships `{message, trades, watchlist_changes}`. The
// resulting bubble renders empty. The stable signal that the auto-execute path
// worked is `[data-testid=action-card-executed]` plus the AMZN positions row.
// This is a documented Phase 5/8 bug surfaced as a Phase 10.1 candidate per
// 10-RESEARCH.md Pitfall 4.

import { test, expect } from '@playwright/test';

test('chat trade execution: mock buy AMZN 1 produces inline action card', async ({ page }) => {
  await page.goto('/');

  // ChatDrawer initial state is useState(true) (ChatDrawer.tsx:19) — drawer is
  // open on page load, so no Expand-chat click needed. If a future plan flips
  // the default, prepend `await page.getByLabel('Expand chat').click()` here.

  await page.getByLabel('Ask the assistant').fill('buy AMZN 1');
  await page.getByRole('button', { name: 'Send' }).click();

  // The mock client returns a TradeAction; the chat service auto-executes;
  // ActionCardList renders an action-card-executed once React Query refetches
  // /api/portfolio. Phase 5 UAT measured this end-to-end at <2s; 15s is
  // generous to absorb cold-start cache priming on WebKit.
  // KNOWN GAP — RESEARCH.md Pitfall 4 / CONTEXT.md D-05: assistant chat bubble
  // renders empty due to ChatResponse field-shape mismatch. DO NOT assert
  // bubble text. Stable signal is the action card.
  await expect(page.getByTestId('action-card-executed')).toBeVisible({
    timeout: 15_000,
  });

  // Bonus: the AMZN position row appears in the positions table — proves the
  // auto-execution path produced a real position, not just a UI confirmation.
  await expect(
    page.getByRole('button', { name: 'Select AMZN' }),
  ).toBeVisible({ timeout: 10_000 });
});
