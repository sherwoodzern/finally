'use client';

/**
 * Status dot for the header strip. Colors driven by selectConnectionStatus.
 * Passive display in Phase 7 (no click behavior).
 * Decision refs: 07-UI-SPEC §5.7; 07-RESEARCH §9.
 */

import type { ConnectionStatus } from '@/lib/sse-types';
import { selectConnectionStatus, usePriceStore } from '@/lib/price-store';

const CLASSES: Record<ConnectionStatus, string> = {
  connected: 'bg-up',
  reconnecting: 'bg-accent-yellow',
  disconnected: 'bg-down',
};

const TITLES: Record<ConnectionStatus, string> = {
  connected: 'Live',
  reconnecting: 'Reconnecting…',
  disconnected: 'Disconnected',
};

export function ConnectionDot() {
  const status = usePriceStore(selectConnectionStatus);
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${CLASSES[status]}`}
      title={TITLES[status]}
      aria-label={`SSE ${status}`}
    />
  );
}
