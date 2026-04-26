'use client';

/**
 * Custom tooltip for PnLChart: date + total + delta vs $10k.
 * Decision refs: UI-SPEC §5.4 + §8.3; PATTERNS.md "PnLTooltip.tsx".
 *
 * Typed with a small local props interface rather than Recharts 3.x
 * `TooltipContentProps` to stay portable across patch versions; the
 * interface mirrors the runtime shape Recharts passes to a custom
 * tooltip's `content` prop.
 */

import { formatMoney, formatSignedMoney } from './PnLChart';

interface PnLTooltipPayload {
  payload?: { recorded_at: string; total_value: number };
}

interface PnLTooltipProps {
  active?: boolean;
  payload?: PnLTooltipPayload[];
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function PnLTooltip({ active, payload }: PnLTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const datum = payload[0]?.payload;
  if (!datum) return null;
  const delta = datum.total_value - 10000;
  const deltaClass = delta >= 0 ? 'text-up' : 'text-down';
  return (
    <div className="bg-surface-alt border border-border-muted rounded p-2 text-sm">
      <div className="text-foreground-muted">{formatTimestamp(datum.recorded_at)}</div>
      <div className="font-mono tabular-nums text-foreground">{formatMoney(datum.total_value)}</div>
      <div className={`font-mono tabular-nums ${deltaClass}`}>
        {formatSignedMoney(delta)} vs $10k
      </div>
    </div>
  );
}
