/**
 * Wire-shape regression test for postChat / getChatHistory.
 *
 * Pins the JSON body shape against the backend ChatRequest contract
 * (backend/app/chat/models.py — `message: str`, `extra="forbid"`).
 * Component tests mock postChat directly, so without this we lose
 * coverage of the field name on the wire — exactly how the
 * `{content: ...}` 422 bug shipped originally (08-HUMAN-UAT test 3).
 */

import { describe, expect, it, vi, afterEach } from 'vitest';
import { postChat, getChatHistory } from './chat';

afterEach(() => vi.restoreAllMocks());

describe('postChat wire body', () => {
  it('serializes the body as {"message": "..."} so backend ChatRequest accepts it', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: '1',
          role: 'assistant',
          content: 'ok',
          created_at: '2026-04-26T00:00:00Z',
          trades: [],
          watchlist_changes: [],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    await postChat({ message: 'hello' });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/chat');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({ message: 'hello' });
  });

  it('throws backend detail.message on non-2xx', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: { error: 'invalid', message: 'too short' } }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    await expect(postChat({ message: 'x' })).rejects.toThrow('too short');
  });
});

describe('getChatHistory', () => {
  it('GETs /api/chat/history and returns the parsed body', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ messages: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getChatHistory();
    expect(fetchSpy).toHaveBeenCalledWith('/api/chat/history');
    expect(r).toEqual({ messages: [] });
  });
});
