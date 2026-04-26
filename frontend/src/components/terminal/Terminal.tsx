'use client';

/**
 * Three-column terminal layout, wrapped in a flex row to host the right-edge
 * chat drawer (Plan 06/07 mounts <ChatDrawer />). Center column is now tabbed
 * (Chart / Heatmap / P&L) per UI-SPEC §5.1.
 * Decision refs: 07-UI-SPEC §5.1; 08-UI-SPEC §5.1; 08-CONTEXT.md D-07.
 */

import { Heatmap } from '@/components/portfolio/Heatmap';
import { PnLChart } from '@/components/portfolio/PnLChart';
import { selectSelectedTab, usePriceStore } from '@/lib/price-store';
import { Header } from './Header';
import { MainChart } from './MainChart';
import { PositionsTable } from './PositionsTable';
import { TabBar } from './TabBar';
import { TradeBar } from './TradeBar';
import { Watchlist } from './Watchlist';

export function Terminal() {
  const selectedTab = usePriceStore(selectSelectedTab);
  return (
    <main className="flex flex-row min-h-screen min-w-[1024px] bg-surface text-foreground">
      <div className="flex-1 min-w-0 p-6">
        <div className="grid grid-cols-[320px_1fr_360px] gap-6">
          <div className="flex flex-col gap-4">
            <Watchlist />
          </div>
          <div className="flex flex-col gap-4 min-w-0">
            <Header />
            <TabBar />
            {selectedTab === 'chart' && <MainChart />}
            {selectedTab === 'heatmap' && <Heatmap />}
            {selectedTab === 'pnl' && <PnLChart />}
          </div>
          <div className="flex flex-col gap-4">
            <PositionsTable />
            <TradeBar />
          </div>
        </div>
      </div>
      {/* Plan 06/07 will replace this slot with <ChatDrawer />. Kept as a placeholder
          so the flex row exists and the visual layout already accounts for it. */}
      <aside
        data-testid="chat-drawer-slot"
        className="w-12 bg-surface-alt border-l border-border-muted flex flex-col"
        aria-label="Chat drawer placeholder"
      />
    </main>
  );
}
