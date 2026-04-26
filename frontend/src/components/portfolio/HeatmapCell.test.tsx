import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { HeatmapCell, formatPct } from './HeatmapCell';

function renderCell(props: Parameters<typeof HeatmapCell>[0]) {
  // Wrap in <svg> so SVG children mount correctly under jsdom.
  return render(
    <svg width="200" height="200">
      <HeatmapCell {...props} />
    </svg>,
  );
}

describe('<HeatmapCell />', () => {
  it('formatPct: signed, 2 decimals (TEST-02 P&L %)', () => {
    expect(formatPct(2.4)).toBe('+2.40%');
    expect(formatPct(-1.1)).toBe('-1.10%');
    expect(formatPct(0)).toBe('+0.00%');
  });

  it('cold-cache renders neutral surface-alt fill (FE-05 fallback)', () => {
    const { container } = renderCell({
      x: 0, y: 0, width: 100, height: 100,
      ticker: 'NVDA', pnlPct: 0, isUp: true, isCold: true,
    });
    const rect = container.querySelector('rect');
    expect(rect?.getAttribute('fill')).toBe('var(--color-surface-alt)');
  });

  it('up renders var(--color-up); down renders var(--color-down) (FE-05 D-02)', () => {
    const up = renderCell({
      x: 0, y: 0, width: 100, height: 100,
      ticker: 'AAPL', pnlPct: 2.4, isUp: true, isCold: false,
    });
    expect(up.container.querySelector('rect')?.getAttribute('fill')).toBe('var(--color-up)');

    const down = renderCell({
      x: 0, y: 0, width: 100, height: 100,
      ticker: 'GOOGL', pnlPct: -1.1, isUp: false, isCold: false,
    });
    expect(down.container.querySelector('rect')?.getAttribute('fill')).toBe('var(--color-down)');
  });

  it('renders ticker bold + signed P&L % when width and height are large enough (FE-05 D-03)', () => {
    const { container } = renderCell({
      x: 0, y: 0, width: 100, height: 100,
      ticker: 'AAPL', pnlPct: 2.4, isUp: true, isCold: false,
    });
    const texts = Array.from(container.querySelectorAll('text')).map((t) => t.textContent);
    expect(texts).toContain('AAPL');
    expect(texts).toContain('+2.40%');
  });

  it('hides labels when width < 60 (FE-05 threshold)', () => {
    const { container } = renderCell({
      x: 0, y: 0, width: 50, height: 100,
      ticker: 'AAPL', pnlPct: 2.4, isUp: true, isCold: false,
    });
    const texts = Array.from(container.querySelectorAll('text')).map((t) => t.textContent);
    expect(texts).not.toContain('AAPL');
    expect(texts).not.toContain('+2.40%');
  });

  it('hides labels when height < 32 (FE-05 threshold)', () => {
    const { container } = renderCell({
      x: 0, y: 0, width: 100, height: 20,
      ticker: 'AAPL', pnlPct: 2.4, isUp: true, isCold: false,
    });
    const texts = Array.from(container.querySelectorAll('text')).map((t) => t.textContent);
    expect(texts).not.toContain('AAPL');
  });
});
