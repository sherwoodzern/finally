import type { HistoryResponse } from '@/lib/api/portfolio';

/** 5 snapshots crossing $10k — last value > 10k so PnLChart stroke is up. */
export const historyFixture: HistoryResponse = {
  snapshots: [
    { recorded_at: '2026-04-25T10:00:00Z', total_value: 10000 },
    { recorded_at: '2026-04-25T10:05:00Z', total_value: 9800  },
    { recorded_at: '2026-04-25T10:10:00Z', total_value: 10200 },
    { recorded_at: '2026-04-25T10:15:00Z', total_value: 10500 },
    { recorded_at: '2026-04-25T10:20:00Z', total_value: 11000 },
  ],
};
