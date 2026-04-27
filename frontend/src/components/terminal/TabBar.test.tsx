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

  it('renders a tablist with Chart, Heatmap, and P&L tabs in order', () => {
    render(<TabBar />);
    expect(screen.getByRole('tablist')).toHaveAttribute('aria-label', 'Center column tabs');
    const tabs = screen.getAllByRole('tab');
    expect(tabs.map((b) => b.textContent)).toEqual(['Chart', 'Heatmap', 'P&L']);
  });

  it('default selectedTab is "chart" — Chart tab is aria-selected="true"', () => {
    render(<TabBar />);
    const chart = screen.getByRole('tab', { name: 'Chart' });
    const heatmap = screen.getByRole('tab', { name: 'Heatmap' });
    expect(chart).toHaveAttribute('aria-selected', 'true');
    expect(heatmap).toHaveAttribute('aria-selected', 'false');
    expect(chart).toHaveAttribute('aria-controls', 'panel-chart');
    expect(chart).toHaveAttribute('id', 'tab-chart');
    expect(chart).toHaveAttribute('tabindex', '0');
    expect(heatmap).toHaveAttribute('tabindex', '-1');
  });

  it('clicking Heatmap dispatches setSelectedTab("heatmap")', () => {
    render(<TabBar />);
    fireEvent.click(screen.getByRole('tab', { name: 'Heatmap' }));
    expect(usePriceStore.getState().selectedTab).toBe('heatmap');
  });

  it('active tab has border-accent-blue; inactive tabs have text-foreground-muted', () => {
    usePriceStore.getState().setSelectedTab('pnl');
    render(<TabBar />);
    const pnl = screen.getByRole('tab', { name: 'P&L' });
    const chart = screen.getByRole('tab', { name: 'Chart' });
    expect(pnl.className).toContain('border-accent-blue');
    expect(chart.className).toContain('text-foreground-muted');
  });
});
