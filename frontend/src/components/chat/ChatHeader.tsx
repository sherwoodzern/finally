'use client';

/**
 * Drawer header strip — title + toggle button.
 * Decision refs: UI-SPEC §5.5; PATTERNS.md "ChatHeader.tsx".
 * Glyphs: U+203A (›) open, U+2039 (‹) collapse — Unicode guillemets, NOT emoji.
 */

interface ChatHeaderProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function ChatHeader({ isOpen, onToggle }: ChatHeaderProps) {
  return (
    <header className="h-12 px-4 flex items-center justify-between border-b border-border-muted">
      {isOpen && <h2 className="text-xl font-semibold">Assistant</h2>}
      <button
        type="button"
        onClick={onToggle}
        aria-label={isOpen ? 'Collapse chat' : 'Expand chat'}
        aria-expanded={isOpen}
        className="w-8 h-8 rounded text-foreground-muted hover:text-foreground hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent-blue"
      >
        {isOpen ? '›' : '‹'}
      </button>
    </header>
  );
}
