import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { __setEventSource, usePriceStore } from './price-store';
import type { RawPayload } from './sse-types';

class MockEventSource {
  static CONNECTING = 0 as const;
  static OPEN = 1 as const;
  static CLOSED = 2 as const;

  url: string;
  readyState = MockEventSource.CONNECTING;
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
  emitErrorConnecting() {
    this.readyState = MockEventSource.CONNECTING;
    this.onerror?.(new Event('error'));
  }
  emitErrorClosed() {
    this.readyState = MockEventSource.CLOSED;
    this.onerror?.(new Event('error'));
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
    change_percent: prev ? +((price - prev) / prev * 100).toFixed(4) : 0,
    direction: price > prev ? 'up' : price < prev ? 'down' : 'flat',
  };
}

describe('price-store SSE lifecycle', () => {
  beforeEach(() => {
    __setEventSource(MockEventSource as unknown as typeof EventSource);
    MockEventSource.reset();
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    usePriceStore.getState().disconnect();
  });

  it('onopen sets status connected', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    expect(usePriceStore.getState().status).toBe('connected');
  });

  it('first event sets session_start_price per ticker', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) });
    expect(usePriceStore.getState().prices.AAPL.session_start_price).toBe(190);
    expect(usePriceStore.getState().prices.AAPL.price).toBe(190);
  });

  it('subsequent events update price but NOT session_start_price', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) });
    // Nyquist: assert mid-stream before the next emit
    expect(usePriceStore.getState().prices.AAPL.session_start_price).toBe(190);
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 195, 190) });
    const tick = usePriceStore.getState().prices.AAPL;
    expect(tick.price).toBe(195);
    expect(tick.previous_price).toBe(190);
    expect(tick.direction).toBe('up');
    expect(tick.session_start_price).toBe(190); // frozen - D-14
  });

  it('onerror CONNECTING sets status reconnecting', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitErrorConnecting();
    expect(usePriceStore.getState().status).toBe('reconnecting');
  });

  it('onerror CLOSED sets status disconnected', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitErrorClosed();
    expect(usePriceStore.getState().status).toBe('disconnected');
  });

  it('connect is idempotent', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    usePriceStore.getState().connect();
    expect(MockEventSource.instances.length).toBe(1);
  });

  it('malformed payload is logged and dropped; store unchanged', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().onmessage?.(
      new MessageEvent('message', { data: 'not-json' })
    );
    expect(usePriceStore.getState().prices).toEqual({});
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it('selector subscribe fires on store changes', () => {
    let renders = 0;
    const unsub = usePriceStore.subscribe(() => {
      renders++;
    });
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 100) });
    MockEventSource.last().emitMessage({ GOOGL: payload('GOOGL', 170) });
    expect(renders).toBeGreaterThan(0);
    unsub();
  });
});
