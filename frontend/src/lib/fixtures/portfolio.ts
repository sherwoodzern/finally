import type { PortfolioResponse } from '@/lib/api/portfolio';

/** 3 positions: AAPL positive P&L, GOOGL negative P&L, NVDA cold-cache (current_price=0; buildTreeData detects via live===undefined && current_price===0). */
export const portfolioFixture: PortfolioResponse = {
  cash_balance: 5000,
  total_value: 11500,
  positions: [
    { ticker: 'AAPL',  quantity: 10, avg_cost: 150, current_price: 200, unrealized_pnl: 500,  change_percent: 33.33 },
    { ticker: 'GOOGL', quantity: 5,  avg_cost: 200, current_price: 180, unrealized_pnl: -100, change_percent: -10.0 },
    { ticker: 'NVDA',  quantity: 2,  avg_cost: 520, current_price: 0,   unrealized_pnl: 0,    change_percent: 0     },
  ],
};
