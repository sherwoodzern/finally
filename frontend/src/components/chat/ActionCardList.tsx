'use client';

/**
 * Renders watchlist_changes BEFORE trades (Phase 5 D-09 order).
 * Decision refs: CONTEXT.md D-10; UI-SPEC §5.7; PATTERNS.md "ActionCardList.tsx".
 */

import type { ActionsBlock } from '@/lib/api/chat';
import { ActionCard } from './ActionCard';

interface Props {
  actions: ActionsBlock;
  pulse?: boolean;
}

export function ActionCardList({ actions, pulse }: Props) {
  const items = [
    ...actions.watchlist_changes.map((a) => ({ kind: 'watchlist' as const, action: a })),
    ...actions.trades.map((a) => ({ kind: 'trade' as const, action: a })),
  ];
  if (items.length === 0) return null;
  return (
    <div data-testid="action-card-list" className="mt-2 flex flex-col">
      {items.map((item, i) =>
        item.kind === 'trade'
          ? <ActionCard key={`t-${i}-${item.action.ticker}`} kind="trade" action={item.action} pulse={pulse} />
          : <ActionCard key={`w-${i}-${item.action.ticker}`} kind="watchlist" action={item.action} pulse={pulse} />
      )}
    </div>
  );
}
