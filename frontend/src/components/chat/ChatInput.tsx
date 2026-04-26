'use client';

/**
 * Textarea + Send button. Enter submits, Shift+Enter newline.
 * Disabled while mutation in flight.
 * Decision refs: UI-SPEC §5.8; PATTERNS.md "ChatInput.tsx".
 */

import { useRef, useState, type KeyboardEvent } from 'react';

interface Props {
  onSubmit: (content: string) => void;
  isPending: boolean;
}

export function ChatInput({ onSubmit, isPending }: Props) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const submit = () => {
    const t = text.trim();
    if (!t || isPending) return;
    onSubmit(t);
    setText('');
    inputRef.current?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== 'Enter') return;
    if (e.shiftKey) return; // newline
    e.preventDefault();
    submit();
  };

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); submit(); }}
      className="border-t border-border-muted p-3 flex gap-2 items-end"
    >
      <textarea
        ref={inputRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        rows={2}
        placeholder="Ask me about your portfolio…"
        disabled={isPending}
        aria-label="Ask the assistant"
        className="flex-1 resize-none px-3 py-2 bg-surface border border-border-muted rounded text-foreground font-sans text-base min-h-[64px] max-h-[160px] focus-visible:outline-2 focus-visible:outline-accent-blue disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={isPending || text.trim().length === 0}
        className="h-10 px-4 bg-accent-purple text-white font-semibold rounded hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent-blue"
      >
        Send
      </button>
    </form>
  );
}
