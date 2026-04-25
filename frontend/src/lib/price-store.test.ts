import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { __setEventSource, usePriceStore } from './price-store';
import type { RawPayload } from './sse-types';

// Reuse the Phase 06 harness shape.
class MockEventSource {
  static CONNECTING = 0 as const;
  static OPEN = 1 as const;
  static CLOSED = 2 as const;

  url: string;
  readyState: number = MockEventSource.CONNECTING;
  onopen: ((this: MockEventSource, ev: Event) => void) | null = null;
  onmessage: ((this: MockEventSource, ev: MessageEvent) => void) | null = null;
  onerror: ((this: MockEventSource, ev: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }
  close = () => {
    this.readyState = MockEventSource.CLOSED;
  };
  emitOpen() {
    this.readyState = MockEventSource.OPEN;
    this.onopen?.(new Event('open'));
  }
  emitMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }
  static instances: MockEventSource[] = [];
  static last() {
    return MockEventSource.instances[MockEventSource.instances.length - 1];
  }
  static reset() {
    MockEventSource.instances = [];
  }
}

function payload(ticker: string, price: number, prev = price): RawPayload {
  return {
    ticker,
    price,
    previous_price: prev,
    timestamp: 1_700_000_000,
    change: +(price - prev).toFixed(4),
    change_percent: prev ? +(((price - prev) / prev) * 100).toFixed(4) : 0,
    direction: price > prev ? 'up' : price < prev ? 'down' : 'flat',
  };
}

describe('price-store Phase 7 extensions', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    __setEventSource(MockEventSource as unknown as typeof EventSource);
    MockEventSource.reset();
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    vi.useRealTimers();
    usePriceStore.getState().disconnect();
  });

  it('flashDirection is set "up" when price rises', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) });
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 195, 190) });
    expect(usePriceStore.getState().flashDirection.AAPL).toBe('up');
  });

  it('flashDirection is set "down" when price falls', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) });
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 185, 190) });
    expect(usePriceStore.getState().flashDirection.AAPL).toBe('down');
  });

  it('flashDirection is cleared 500ms after a tick', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) });
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 195, 190) });
    expect(usePriceStore.getState().flashDirection.AAPL).toBe('up');
    vi.advanceTimersByTime(500);
    expect(usePriceStore.getState().flashDirection.AAPL).toBeUndefined();
  });

  it('sparklineBuffers appends price on each tick', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) });
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 195, 190) });
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 197, 195) });
    expect(usePriceStore.getState().sparklineBuffers.AAPL).toEqual([190, 195, 197]);
  });

  it('sparklineBuffers trims to the last 120 entries', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    for (let i = 0; i < 125; i++) {
      MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 100 + i, 100 + i - 1) });
    }
    const buf = usePriceStore.getState().sparklineBuffers.AAPL;
    expect(buf.length).toBe(120);
    // Oldest retained is tick index 5 (value 105); newest is index 124 (value 224).
    expect(buf[0]).toBe(105);
    expect(buf[119]).toBe(224);
  });

  it('setSelectedTicker updates the store; selectSelectedTicker reads it', () => {
    usePriceStore.getState().setSelectedTicker('AAPL');
    expect(usePriceStore.getState().selectedTicker).toBe('AAPL');
    usePriceStore.getState().setSelectedTicker(null);
    expect(usePriceStore.getState().selectedTicker).toBeNull();
  });

  it('reset() clears flash timers and zeroes new slices', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) });
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 195, 190) });
    usePriceStore.getState().setSelectedTicker('AAPL');
    usePriceStore.getState().reset();
    expect(usePriceStore.getState().flashDirection).toEqual({});
    expect(usePriceStore.getState().sparklineBuffers).toEqual({});
    expect(usePriceStore.getState().selectedTicker).toBeNull();
    // Advancing past the timer must not re-introduce any flash state.
    vi.advanceTimersByTime(1000);
    expect(usePriceStore.getState().flashDirection).toEqual({});
  });
});
