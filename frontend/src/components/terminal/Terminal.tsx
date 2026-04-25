'use client';

/**
 * Three-column terminal layout. Desktop-first: min-width 1024px,
 * horizontal scroll below that. Composes all five FE-03/04/07/08/10 panels.
 * Decision refs: 07-UI-SPEC §5.1 Layout Grid.
 */

import { Watchlist } from './Watchlist';
import { Header } from './Header';
import { MainChart } from './MainChart';
import { PositionsTable } from './PositionsTable';
import { TradeBar } from './TradeBar';

export function Terminal() {
  return (
    <main className="min-h-screen min-w-[1024px] bg-surface text-foreground p-6">
      <div className="grid grid-cols-[320px_1fr_360px] gap-6">
        <div className="flex flex-col gap-4">
          <Watchlist />
        </div>
        <div className="flex flex-col gap-4 min-w-0">
          <Header />
          <MainChart />
        </div>
        <div className="flex flex-col gap-4">
          <PositionsTable />
          <TradeBar />
        </div>
      </div>
    </main>
  );
}
