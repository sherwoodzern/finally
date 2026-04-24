'use client';

import { useEffect } from 'react';
import { usePriceStore } from './price-store';

/**
 * Owns the single EventSource for the app lifetime.
 * Mount once in the root layout (D-11). StrictMode-safe via the store's
 * idempotent connect() (D-15) - double-invoke is a no-op.
 *
 * Conceptual analog: backend/app/market/simulator.py SimulatorDataSource.start()/stop()
 * - one long-running task, cancelled on stop, idempotent guard on the lifecycle op.
 */
export function PriceStreamProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const { connect, disconnect } = usePriceStore.getState();
    connect();
    return () => disconnect();
  }, []);

  return <>{children}</>;
}
