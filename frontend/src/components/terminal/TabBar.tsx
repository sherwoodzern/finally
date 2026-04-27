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
    <div
      role="tablist"
      aria-label="Center column tabs"
      className="flex gap-2 border-b border-border-muted"
    >
      {TABS.map((t) => {
        const active = selectedTab === t.id;
        return (
          <button
            key={t.id}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={active}
            aria-controls={`panel-${t.id}`}
            tabIndex={active ? 0 : -1}
            onClick={() => usePriceStore.getState().setSelectedTab(t.id)}
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
    </div>
  );
}
