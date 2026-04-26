'use client';

/**
 * Single chat bubble — user (right, bg-surface) or assistant (left, bg-surface-alt).
 * Renders <ActionCardList /> below assistant content when actions != null.
 * Content is rendered as plain JSX text only (React escapes by default; no raw HTML
 * injection, no markdown→HTML), preventing XSS via assistant content per threat T-08-12.
 * Decision refs: UI-SPEC §5.6; PATTERNS.md "ChatMessage.tsx".
 */

import type { ChatMessageOut } from '@/lib/api/chat';
import { ActionCardList } from './ActionCardList';

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

interface Props {
  message: ChatMessageOut;
  pulseActions?: boolean;
}

export function ChatMessage({ message, pulseActions }: Props) {
  const isUser = message.role === 'user';
  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`} data-testid={`chat-message-${message.role}`}>
      <div
        className={`max-w-[85%] border border-border-muted rounded-lg px-3 py-2 text-foreground whitespace-pre-wrap ${
          isUser ? 'bg-surface' : 'bg-surface-alt'
        }`}
      >
        {message.content}
      </div>
      {!isUser && message.actions && (
        <ActionCardList actions={message.actions} pulse={pulseActions} />
      )}
      <span className="text-xs text-foreground-muted mt-1">{formatTime(message.created_at)}</span>
    </div>
  );
}
