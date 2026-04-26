import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { TabBar } from './TabBar';
import { usePriceStore } from '@/lib/price-store';

describe('<TabBar />', () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    usePriceStore.getState().reset();
  });

  it('renders Chart, Heatmap, and P&L tabs in order', () => {
    render(<TabBar />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.map((b) => b.textContent)).toEqual(['Chart', 'Heatmap', 'P&L']);
  });

  it('default selectedTab is "chart" — Chart button is aria-pressed="true"', () => {
    render(<TabBar />);
    const chart = screen.getByRole('button', { name: 'Chart' });
    const heatmap = screen.getByRole('button', { name: 'Heatmap' });
    expect(chart).toHaveAttribute('aria-pressed', 'true');
    expect(heatmap).toHaveAttribute('aria-pressed', 'false');
  });

  it('clicking Heatmap dispatches setSelectedTab("heatmap")', () => {
    render(<TabBar />);
    fireEvent.click(screen.getByRole('button', { name: 'Heatmap' }));
    expect(usePriceStore.getState().selectedTab).toBe('heatmap');
  });

  it('active tab has border-accent-blue; inactive tabs have text-foreground-muted', () => {
    usePriceStore.getState().setSelectedTab('pnl');
    render(<TabBar />);
    const pnl = screen.getByRole('button', { name: 'P&L' });
    const chart = screen.getByRole('button', { name: 'Chart' });
    expect(pnl.className).toContain('border-accent-blue');
    expect(chart.className).toContain('text-foreground-muted');
  });
});
