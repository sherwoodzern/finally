import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';

const mockSeries = { setData: vi.fn(), update: vi.fn(), applyOptions: vi.fn() };
const mockChart = {
  addSeries: vi.fn(() => mockSeries),
  remove: vi.fn(),
  applyOptions: vi.fn(),
};

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => mockChart),
  LineSeries: 'LineSeries',
}));

import { Sparkline } from './Sparkline';
import * as lwc from 'lightweight-charts';

describe('<Sparkline />', () => {
  beforeEach(() => {
    mockSeries.setData.mockClear();
    mockSeries.update.mockClear();
    mockSeries.applyOptions.mockClear();
    mockChart.addSeries.mockClear();
    mockChart.remove.mockClear();
    (lwc.createChart as ReturnType<typeof vi.fn>).mockClear();
  });

  it('calls createChart and addSeries(LineSeries, ...) on mount', () => {
    render(<Sparkline buffer={[1, 2, 3]} positive={true} />);
    expect(lwc.createChart).toHaveBeenCalledTimes(1);
    expect(mockChart.addSeries).toHaveBeenCalledTimes(1);
    const [firstArg, secondArg] = mockChart.addSeries.mock.calls[0];
    expect(firstArg).toBe('LineSeries');
    expect(secondArg).toMatchObject({
      color: '#26a69a',
      lineWidth: 1,
    });
  });

  it('uses the down color when positive=false', () => {
    render(<Sparkline buffer={[3, 2, 1]} positive={false} />);
    const [, secondArg] = mockChart.addSeries.mock.calls[0];
    expect(secondArg).toMatchObject({ color: '#ef5350' });
  });

  it('calls series.setData with buffer data when buffer is provided', () => {
    render(<Sparkline buffer={[100, 101, 102]} positive={true} />);
    expect(mockSeries.setData).toHaveBeenCalledTimes(1);
    const data = mockSeries.setData.mock.calls[0][0];
    expect(data).toHaveLength(3);
    expect(data.map((p: { value: number }) => p.value)).toEqual([100, 101, 102]);
  });

  it('does not call setData when buffer is undefined', () => {
    render(<Sparkline buffer={undefined} positive={true} />);
    expect(mockSeries.setData).not.toHaveBeenCalled();
  });

  it('calls chart.remove on unmount', () => {
    const { unmount } = render(<Sparkline buffer={[1, 2, 3]} positive={true} />);
    expect(mockChart.remove).not.toHaveBeenCalled();
    unmount();
    expect(mockChart.remove).toHaveBeenCalledTimes(1);
  });
});
