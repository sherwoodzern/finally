import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test-utils';
import { ChatThread } from './ChatThread';
import { usePriceStore } from '@/lib/price-store';
import { chatHistoryFixture } from '@/lib/fixtures/chat';

describe('<ChatThread />', () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders messages from /api/chat/history on mount (FE-09 D-09)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
      if (url === '/api/chat/history') {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(chatHistoryFixture) });
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
    }));
    renderWithQuery(<ChatThread />);
    await waitFor(() => {
      expect(screen.getByText('Buy 10 AAPL')).toBeInTheDocument();
      expect(screen.getByText('Bought 10 AAPL.')).toBeInTheDocument();
    });
  });

  it('shows ThinkingBubble while postChat is in flight (FE-09 D-08)', async () => {
    let resolveChat!: (value: unknown) => void;
    const pending = new Promise((r) => { resolveChat = r; });
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
      if (url === '/api/chat/history') {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ messages: [] }) });
      }
      if (url === '/api/chat') {
        return pending.then((v) => ({ ok: true, status: 200, json: () => Promise.resolve(v) }));
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
    }));

    renderWithQuery(<ChatThread />);
    await waitFor(() => expect(screen.queryByTestId('chat-thread-skeleton')).not.toBeInTheDocument());

    const textarea = screen.getByPlaceholderText('Ask me about your portfolio…');
    fireEvent.change(textarea, { target: { value: 'hello' } });
    fireEvent.submit(textarea.closest('form')!);

    await waitFor(() => {
      expect(screen.getByTestId('thinking-bubble')).toBeInTheDocument();
    });

    // resolve the pending mutation so the test exits cleanly
    resolveChat({
      id: 'a1', role: 'assistant', content: 'Hi.', created_at: '2026-04-25T10:00:00Z',
      trades: [], watchlist_changes: [],
    });
  });

  it('flashTrade("AAPL","up") fires for each executed trade in the response (FE-11 D-12)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
      if (url === '/api/chat/history') {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ messages: [] }) });
      }
      if (url === '/api/chat') {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({
          id: 'a1', role: 'assistant', content: 'Bought.', created_at: '2026-04-25T10:00:00Z',
          trades: [{ ticker: 'AAPL', side: 'buy', quantity: 1, status: 'executed', price: 200, executed_at: '2026-04-25T10:00:00Z' }],
          watchlist_changes: [],
        }) });
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
    }));

    renderWithQuery(<ChatThread />);
    const textarea = await screen.findByPlaceholderText('Ask me about your portfolio…');
    fireEvent.change(textarea, { target: { value: 'buy 1 AAPL' } });
    fireEvent.submit(textarea.closest('form')!);

    await waitFor(() => {
      expect(usePriceStore.getState().tradeFlash.AAPL).toBe('up');
    });
  });

  it('XSS guard: assistant content with <script> renders as plain text, not as DOM', async () => {
    const malicious = '<script>window.__pwned = true;</script>hello';
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({
        messages: [{ id: 'm1', role: 'assistant', content: malicious, created_at: '2026-04-25T10:00:00Z', actions: null }],
      }),
    }));
    renderWithQuery(<ChatThread />);
    await waitFor(() => {
      expect(screen.getByText(malicious)).toBeInTheDocument();
    });
    // global flag must NOT be set
    expect((window as unknown as { __pwned?: true }).__pwned).toBeUndefined();
  });
});
