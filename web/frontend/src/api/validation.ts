import { createJob, type WebJob } from './jobs';

export interface ValidationPayload {
  strategy_slug: string;
  profile_name?: string | null;
  timerange?: string | null;
  min_trades: number;
  min_profit: number;
  min_profit_factor: number;
  max_drawdown: number;
  min_winrate: number;
  min_avg_profit: number;
  min_trades_per_day: number;
}

export interface ValidationResult {
  strategy_slug: string;
  profile_name: string;
  timerange: string;
  passed: boolean;
  gate: Record<string, number>;
  failed_checks: string[];
  warnings: string[];
  metrics: {
    total_trades: number;
    profit_total: number;
    profit_factor: number;
    winrate: number;
    max_drawdown_account: number;
  };
  backtest_zip: string;
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function runValidation(payload: ValidationPayload): Promise<WebJob> {
  return createJob('validation', { ...payload });
}

export async function fetchValidationJobs(limit = 50): Promise<WebJob[]> {
  const payload = await getJson<{ items: WebJob[] }>(`/api/validation/results?limit=${limit}`);
  return payload.items;
}

export async function promoteProfile(
  strategySlug: string,
  profileName: string,
  toStatus = 'validated',
): Promise<{ promoted: boolean }> {
  const response = await fetch('/api/profiles/promote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      strategy_slug: strategySlug,
      profile_name: profileName,
      to_status: toStatus,
      reason: 'web validation gate',
    }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `promotion failed: ${response.status}`);
  }
  return response.json() as Promise<{ promoted: boolean }>;
}
