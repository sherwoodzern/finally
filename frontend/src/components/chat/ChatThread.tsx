'use client';

/**
 * Scrolling message list + auto-scroll. Owns the postChat useMutation;
 * appends user/assistant turns optimistically; flashes position rows for
 * each `executed` trade; invalidates ['portfolio'] on success.
 * Decision refs: CONTEXT.md D-08, D-09, D-12; UI-SPEC §5.5, §5.7, §5.8;
 * PATTERNS.md "ChatThread.tsx".
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLayoutEffect, useRef, useState } from 'react';
import { getChatHistory, postChat, type ChatMessageOut, type ChatResponse } from '@/lib/api/chat';
import { usePriceStore } from '@/lib/price-store';
import { ChatInput } from './ChatInput';
import { ChatMessage } from './ChatMessage';
import { ThinkingBubble } from './ThinkingBubble';

function localUserMessage(content: string): ChatMessageOut {
  return {
    id: `local-user-${Date.now()}`,
    role: 'user',
    content,
    created_at: new Date().toISOString(),
    actions: null,
  };
}

function assistantFromResponse(res: ChatResponse): ChatMessageOut {
  return {
    id: res.id,
    role: 'assistant',
    content: res.content,
    created_at: res.created_at,
    actions: { trades: res.trades, watchlist_changes: res.watchlist_changes },
  };
}

export function ChatThread() {
  const qc = useQueryClient();
  const [appended, setAppended] = useState<ChatMessageOut[]>([]);
  const [freshAssistantId, setFreshAssistantId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const historyQuery = useQuery({
    queryKey: ['chat', 'history'],
    queryFn: getChatHistory,
  });

  const mutation = useMutation({
    mutationFn: postChat,
    onSuccess: async (res: ChatResponse) => {
      const assistant = assistantFromResponse(res);
      setAppended((p) => [...p, assistant]);
      setFreshAssistantId(assistant.id);
      for (const t of res.trades) {
        if (t.status === 'executed') {
          usePriceStore.getState().flashTrade(t.ticker, 'up');
        }
      }
      await qc.invalidateQueries({ queryKey: ['portfolio'] });
      if (res.watchlist_changes.length > 0) {
        await qc.invalidateQueries({ queryKey: ['watchlist'] });
      }
      setSubmitError(null);
    },
    onError: (err: unknown) => {
      setSubmitError(err instanceof Error ? err.message : "Couldn't reach the assistant. Try again.");
    },
  });

  const submit = (content: string) => {
    const text = content.trim();
    if (!text) return;
    setAppended((p) => [...p, localUserMessage(text)]);
    mutation.mutate({ message: text });
  };

  const messages: ChatMessageOut[] = [
    ...(historyQuery.data?.messages ?? []),
    ...appended,
  ];

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length, mutation.isPending]);

  return (
    <>
      <div
        ref={scrollRef}
        data-testid="chat-thread"
        className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3"
      >
        {historyQuery.isPending && (
          <div data-testid="chat-thread-skeleton" className="flex flex-col gap-3">
            <div className="bg-border-muted/50 rounded animate-pulse h-12 w-48" />
            <div className="bg-border-muted/50 rounded animate-pulse h-12 w-32 self-end" />
            <div className="bg-border-muted/50 rounded animate-pulse h-12 w-56" />
          </div>
        )}
        {!historyQuery.isPending && messages.length === 0 && (
          <p className="text-sm text-foreground-muted mt-auto">
            Ask me about your portfolio or tell me to trade.
          </p>
        )}
        {messages.map((m) => (
          <ChatMessage
            key={m.id}
            message={m}
            pulseActions={m.id === freshAssistantId}
          />
        ))}
        {mutation.isPending && <ThinkingBubble />}
      </div>
      {submitError && (
        <p role="alert" className="px-4 text-sm text-down">{submitError}</p>
      )}
      <ChatInput onSubmit={submit} isPending={mutation.isPending} />
    </>
  );
}
