import { createJob, type WebJob } from './jobs';

export interface BacktestPayload {
  strategy_slug: string;
  profile_name?: string | null;
  phase: 'train' | 'validation' | 'test' | 'custom';
  timerange?: string | null;
}

export interface BacktestMetrics {
  total_trades: number;
  profit_total: number;
  profit_total_abs: number;
  profit_factor: number;
  wins: number;
  losses: number;
  draws: number;
  winrate: number;
  avg_profit: number;
  expectancy_ratio: number;
  max_drawdown_account: number;
  stake_currency: string;
}

export interface BacktestResult {
  strategy_slug: string;
  strategy_name: string;
  profile_name: string;
  phase: string;
  timerange: string;
  metrics: BacktestMetrics;
  backtest_zip: string;
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function runBacktest(payload: BacktestPayload): Promise<WebJob> {
  return createJob('backtest', { ...payload });
}

export async function fetchBacktestJobs(limit = 50): Promise<WebJob[]> {
  const payload = await getJson<{ items: WebJob[] }>(`/api/backtests/results?limit=${limit}`);
  return payload.items;
}
