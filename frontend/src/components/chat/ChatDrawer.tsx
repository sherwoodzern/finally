'use client';

/**
 * Right-edge collapsible drawer SHELL.
 * Open-state body is provided by the consumer via the `children` prop;
 * Plan 07 will wire the chat thread as children when mounting in Terminal.tsx.
 * Decision refs: CONTEXT.md D-07; UI-SPEC §5.5; PATTERNS.md.
 */

import { useState, type ReactNode } from 'react';
import { ChatHeader } from './ChatHeader';

interface ChatDrawerProps {
  /** Open-state body. Optional so the shell can render alone in tests. */
  children?: ReactNode;
}

export function ChatDrawer({ children }: ChatDrawerProps) {
  const [isOpen, setOpen] = useState<boolean>(true);
  return (
    <aside
      data-testid="chat-drawer"
      aria-label="AI assistant"
      className={`bg-surface-alt border-l border-border-muted flex flex-col transition-[width] duration-300 ease-out ${
        isOpen ? 'w-[380px]' : 'w-12'
      }`}
    >
      <ChatHeader isOpen={isOpen} onToggle={() => setOpen(!isOpen)} />
      {isOpen && children}
    </aside>
  );
}
