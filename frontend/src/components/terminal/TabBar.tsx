'use client';

/**
 * TabBar — three-tab switcher (Chart / Heatmap / P&L) for the center column.
 * Decision refs: UI-SPEC §5.2; PATTERNS.md "TabBar.tsx".
 */

import { selectSelectedTab, usePriceStore } from '@/lib/price-store';

type TabId = 'chart' | 'heatmap' | 'pnl';

const TABS: { id: TabId; label: string }[] = [
  { id: 'chart', label: 'Chart' },
  { id: 'heatmap', label: 'Heatmap' },
  { id: 'pnl', label: 'P&L' },
];

export function TabBar() {
  const selectedTab = usePriceStore(selectSelectedTab);
  return (
    <nav className="flex gap-2 border-b border-border-muted" aria-label="Center column tabs">
      {TABS.map((t) => {
        const active = selectedTab === t.id;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => usePriceStore.getState().setSelectedTab(t.id)}
            aria-pressed={active}
            className={`h-10 px-4 text-sm font-semibold border-b-2 -mb-px focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-blue ${
              active
                ? 'border-accent-blue text-foreground'
                : 'border-transparent text-foreground-muted hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        );
      })}
    </nav>
  );
}
