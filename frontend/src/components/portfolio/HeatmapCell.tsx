'use client';

/**
 * FE-05 HeatmapCell — Recharts Treemap content prop renderer.
 * Receives Recharts geometry (x,y,width,height) merged with our datum
 * (ticker, pnlPct, isUp, isCold). Pure SVG render-by-prop.
 * Decision refs: CONTEXT.md D-02, D-03; UI-SPEC §5.3; PATTERNS.md "HeatmapCell.tsx".
 */

interface HeatmapCellProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  ticker?: string;
  pnlPct?: number;
  isUp?: boolean;
  isCold?: boolean;
}

export function formatPct(pct: number): string {
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

export function HeatmapCell(props: HeatmapCellProps) {
  const {
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    ticker = '',
    pnlPct = 0,
    isUp = true,
    isCold = false,
  } = props;
  const fill = isCold
    ? 'var(--color-surface-alt)'
    : isUp
      ? 'var(--color-up)'
      : 'var(--color-down)';
  const showLabel = width >= 60 && height >= 32;
  return (
    <g cursor="pointer">
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke="#30363d" />
      {showLabel && (
        <>
          <text
            x={x + 8}
            y={y + 18}
            fill="#ffffff"
            fontFamily="ui-sans-serif, system-ui"
            fontWeight={600}
            fontSize={14}
          >
            {ticker}
          </text>
          <text
            x={x + 8}
            y={y + 36}
            fill="#ffffff"
            fontFamily="ui-monospace, SFMono-Regular, Menlo"
            fontSize={12}
          >
            {formatPct(pnlPct)}
          </text>
        </>
      )}
      <title>{`${ticker}: ${formatPct(pnlPct)}`}</title>
    </g>
  );
}
