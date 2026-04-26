import { afterEach, describe, expect, it, vi } from 'vitest';
import { cloneElement, type ReactElement } from 'react';
import { screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test-utils';
import { historyFixture } from '@/lib/fixtures/history';
import type { HistoryResponse } from '@/lib/api/portfolio';

/**
 * Mock Recharts <ResponsiveContainer> to a fixed 800x600 wrapper so the inner
 * chart actually renders in jsdom (jsdom has no layout engine; the real
 * ResponsiveContainer measures via ResizeObserver and returns -1×-1, which
 * makes Recharts skip rendering paths/lines). Matches RESEARCH.md Pitfall 5
 * "Concrete: mock Recharts ResponsiveContainer for tests".
 */
vi.mock('recharts', async () => {
  const original = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...original,
    ResponsiveContainer: ({ children }: { children: ReactElement }) =>
      cloneElement(children, { width: 800, height: 600 } as Record<string, unknown>),
  };
});

import { PnLChart } from './PnLChart';

function stubHistory(body: HistoryResponse | unknown, ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok,
      status: ok ? 200 : 500,
      json: () => Promise.resolve(body),
    }),
  );
}

describe('<PnLChart />', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders skeleton while pending (FE-11 D-13)', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    renderWithQuery(<PnLChart />);
    expect(screen.getByTestId('pnl-skeleton')).toBeInTheDocument();
  });

  it('1-snapshot empty state copy renders (FE-06 Discretion)', async () => {
    stubHistory({
      snapshots: [{ recorded_at: '2026-04-25T10:00:00Z', total_value: 10000 }],
    });
    renderWithQuery(<PnLChart />);
    await waitFor(() =>
      expect(
        screen.getByText(/Building P&L history… your first snapshot is in\./),
      ).toBeInTheDocument(),
    );
  });

  it('line stroke is var(--color-up) when latest total_value >= 10000 (FE-06 D-06)', async () => {
    stubHistory(historyFixture); // last value = 11000 > 10000
    const { container } = renderWithQuery(<PnLChart />);
    await waitFor(() => {
      expect(screen.getByTestId('pnl-chart')).toBeInTheDocument();
    });
    const allPaths = Array.from(container.querySelectorAll('path'));
    const strokes = allPaths.map((p) => p.getAttribute('stroke')).filter(Boolean);
    expect(strokes.some((s) => s === 'var(--color-up)')).toBe(true);
  });

  it('line stroke is var(--color-down) when latest total_value < 10000 (FE-06 D-06)', async () => {
    stubHistory({
      snapshots: [
        { recorded_at: '2026-04-25T10:00:00Z', total_value: 10000 },
        { recorded_at: '2026-04-25T10:05:00Z', total_value: 9800 },
        { recorded_at: '2026-04-25T10:10:00Z', total_value: 9500 },
      ],
    });
    const { container } = renderWithQuery(<PnLChart />);
    await waitFor(() => {
      expect(screen.getByTestId('pnl-chart')).toBeInTheDocument();
    });
    const allPaths = Array.from(container.querySelectorAll('path'));
    const strokes = allPaths.map((p) => p.getAttribute('stroke')).filter(Boolean);
    expect(strokes.some((s) => s === 'var(--color-down)')).toBe(true);
  });

  it('includes a <ReferenceLine y=10000> rendered as a dashed SVG line (FE-06 D-05)', async () => {
    stubHistory(historyFixture);
    const { container } = renderWithQuery(<PnLChart />);
    await waitFor(() => {
      expect(screen.getByTestId('pnl-chart')).toBeInTheDocument();
    });
    // Recharts ReferenceLine renders an SVG <line> with strokeDasharray="4 4".
    const dashedLines = Array.from(container.querySelectorAll('line')).filter(
      (l) => l.getAttribute('stroke-dasharray') === '4 4',
    );
    expect(dashedLines.length).toBeGreaterThan(0);
  });

  it('header summary shows latest total + signed delta vs $10k (FE-06)', async () => {
    stubHistory(historyFixture); // last value = 11000
    renderWithQuery(<PnLChart />);
    await waitFor(() => {
      const summary = screen.getByTestId('pnl-summary');
      expect(summary.textContent ?? '').toMatch(/\$11,000\.00/);
      expect(summary.textContent ?? '').toMatch(/\+\$1,000\.00 vs \$10k/);
    });
  });
});
