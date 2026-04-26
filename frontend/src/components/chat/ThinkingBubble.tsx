'use client';

/**
 * 3-dot animated "thinking" bubble shown as the last assistant message
 * while POST /api/chat is in flight (D-08).
 * Decision refs: UI-SPEC §5.9 + §7; PATTERNS.md "ThinkingBubble.tsx".
 */

export function ThinkingBubble() {
  return (
    <div className="flex flex-col items-start" data-testid="thinking-bubble">
      <div
        className="bg-surface-alt border border-border-muted rounded-lg px-3 py-3 flex items-center gap-1"
        aria-label="Assistant is thinking"
        role="status"
      >
        <span className="thinking-dot" />
        <span className="thinking-dot" />
        <span className="thinking-dot" />
      </div>
    </div>
  );
}
