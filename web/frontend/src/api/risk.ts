export interface RiskSummary {
  ok: boolean;
  mode: string;
  source: {
    runtime_artifact: {
      ok: boolean;
      path?: string;
      strategy_slug?: string;
      strategy_name?: string;
      profile_name?: string;
      export_time?: string;
      error?: string;
    };
    rule_error?: string;
    freqtrade_profit_ok: boolean;
    freqtrade_trades_ok: boolean;
    freqtrade_locks_ok: boolean;
  };
  strategy: {
    slug?: string;
    strategy_name?: string;
    profile_name?: string;
    profile_status?: string;
  };
  rules: {
    max_drawdown_pct?: number;
    max_daily_loss_pct?: number;
    max_consecutive_losses?: number;
    cooldown_candles_after_loss_streak?: number;
    max_open_trades?: number;
    protections_in_config_required?: boolean;
  };
  metrics: {
    max_drawdown_ratio: number;
    max_drawdown_abs: number;
    current_drawdown_ratio: number;
    current_drawdown_abs: number;
    daily_loss: {
      date: string;
      timezone: string;
      realized_pnl_abs: number;
      loss_abs: number;
      loss_ratio: number;
      closed_trades: number;
      balance_basis: number;
    };
    consecutive_losses: {
      count: number;
      sample_size: number;
      latest_closed_trade_id?: number;
      latest_closed_at?: string;
    };
    cooldown: {
      configured_candles: number;
      active_locks: number;
      locks: Array<Record<string, unknown>>;
    };
  };
  checks: Array<{
    key: string;
    label: string;
    observed: number;
    limit?: number;
    status: string;
  }>;
  recent_closed_trades: Array<Record<string, unknown>>;
  errors: Record<string, string | undefined>;
}

export async function fetchRiskSummary(): Promise<RiskSummary> {
  const response = await fetch('/api/risk/summary');
  if (!response.ok) {
    throw new Error(`risk summary failed: ${response.status}`);
  }
  return response.json() as Promise<RiskSummary>;
}
