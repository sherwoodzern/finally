'use client';

/**
 * Shared skeleton-loader primitive (FE-11 D-13).
 * Pure-CSS pulsing block; consumer supplies sizing via className.
 * Decision refs: CONTEXT.md D-13; UI-SPEC §6; PATTERNS.md "SkeletonBlock.tsx".
 */

interface SkeletonBlockProps {
  className?: string;
}

export function SkeletonBlock({ className }: SkeletonBlockProps) {
  return (
    <div
      data-testid="skeleton-block"
      aria-hidden="true"
      className={`bg-border-muted/50 rounded animate-pulse ${className ?? ''}`}
    />
  );
}
