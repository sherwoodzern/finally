import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

/**
 * Recharts <ResponsiveContainer> calls ResizeObserver in jsdom; without this stub
 * it throws "ResizeObserver is not defined" and the chart silently collapses to 0x0,
 * breaking every Heatmap/PnLChart assertion. Phase 8 RESEARCH.md Pattern 9 / Pitfall 5.
 */
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub);
