'use client';

/**
 * One action confirmation card. Status-driven styling per UI-SPEC §5.7 table.
 * Pulses ~800ms on first mount when `pulse` prop is set (D-12 fresh card).
 * Decision refs: CONTEXT.md D-10, D-11, D-12; UI-SPEC §5.7, §8.5;
 * PATTERNS.md "ActionCard.tsx".
 */

import { useEffect, useState } from 'react';
import type {
  TradeActionResult,
  WatchlistActionResult,
} from '@/lib/api/chat';

type Status =
  | 'executed'
  | 'failed'
  | 'added'
  | 'removed'
  | 'exists'
  | 'not_present';

interface StatusStyle {
  borderClass: string;
  textClass: string;
  label: string;
}

const STATUS_STYLE: Record<Status, StatusStyle> = {
  executed:    { borderClass: 'border-l-4 border-l-up border border-up/30',                       textClass: 'text-up',                label: 'executed' },
  added:       { borderClass: 'border-l-4 border-l-up border border-up/30',                       textClass: 'text-up',                label: 'added' },
  removed:     { borderClass: 'border-l-4 border-l-up border border-up/30',                       textClass: 'text-up',                label: 'removed' },
  failed:      { borderClass: 'border-l-4 border-l-down border border-down/40',                   textClass: 'text-down',              label: 'failed' },
  exists:      { borderClass: 'border-l-4 border-l-foreground-muted border border-border-muted',  textClass: 'text-foreground-muted',  label: 'already there' },
  not_present: { borderClass: 'border-l-4 border-l-foreground-muted border border-border-muted',  textClass: 'text-foreground-muted',  label: "wasn't there" },
};

const ERROR_COPY: Record<string, string> = {
  insufficient_cash: 'Not enough cash for that order.',
  insufficient_shares: "You don't have that many shares to sell.",
  unknown_ticker: 'No such ticker.',
  price_unavailable: 'Price unavailable right now — try again.',
  invalid_ticker: "That ticker symbol isn't valid.",
  internal_error: 'Something went wrong on our side. Try again.',
};
const DEFAULT_ERROR = 'Something went wrong. Try again.';

type Props =
  | { kind: 'trade';     action: TradeActionResult;     pulse?: boolean }
  | { kind: 'watchlist'; action: WatchlistActionResult; pulse?: boolean };

function tradeVerb(side: 'buy' | 'sell'): string {
  return side === 'buy' ? 'Buy' : 'Sell';
}
function watchlistVerb(act: 'add' | 'remove'): string {
  return act === 'add' ? 'Add' : 'Remove';
}

function formatPrice(p: number): string {
  return `$${p.toFixed(2)}`;
}

export function ActionCard(props: Props) {
  const status = props.action.status as Status;
  const style = STATUS_STYLE[status] ?? STATUS_STYLE.failed;
  const verb = props.kind === 'trade'
    ? tradeVerb(props.action.side)
    : watchlistVerb(props.action.action);

  const [pulseClass, setPulseClass] = useState<string>(() => {
    if (!props.pulse) return '';
    if (status === 'executed') return 'action-pulse-up';
    if (status === 'failed') return 'action-pulse-down';
    return '';
  });

  useEffect(() => {
    if (!pulseClass) return;
    const t = setTimeout(() => setPulseClass(''), 800);
    return () => clearTimeout(t);
  }, [pulseClass]);

  const errorString =
    status === 'failed'
      ? ERROR_COPY[props.action.error ?? ''] ?? DEFAULT_ERROR
      : null;

  const detail =
    props.kind === 'trade' && status === 'executed' && typeof props.action.price === 'number'
      ? `${props.action.quantity} @ ${formatPrice(props.action.price)}`
      : props.kind === 'trade'
        ? `${props.action.quantity}`
        : null;

  return (
    <div
      data-testid={`action-card-${status}`}
      className={`bg-surface rounded px-3 py-2 mt-2 ${style.borderClass} ${pulseClass}`}
    >
      <div className="flex items-baseline justify-between gap-2 min-w-0">
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="text-sm font-semibold">{verb}</span>
          <span className="font-semibold">{props.action.ticker}</span>
          {detail && (
            <span className="font-mono tabular-nums text-sm text-foreground-muted">
              {detail}
            </span>
          )}
        </div>
        <span className={`text-sm font-semibold ${style.textClass}`}>
          {style.label}
        </span>
      </div>
      {errorString && (
        <p className="text-sm text-down mt-1">{errorString}</p>
      )}
    </div>
  );
}

export { STATUS_STYLE, ERROR_COPY, DEFAULT_ERROR };
