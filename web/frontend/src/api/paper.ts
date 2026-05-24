export interface PaperSummary {
  ok: boolean;
  mode: string;
  execution_baseline: string;
  websocket_enabled: boolean;
  dry_run: boolean;
  trading_mode: string;
  margin_mode: string;
  pair_whitelist: string[];
  api: {
    ok: boolean;
    url: string;
  };
  balance: {
    ok: boolean;
    data?: {
      total?: number;
      total_bot?: number;
      stake?: string;
      starting_capital_pct?: number;
      note?: string;
    };
    error?: string;
  };
  profit: {
    ok: boolean;
    data?: {
      profit_all_coin?: number;
      profit_all_percent?: number;
      closed_trade_count?: number;
      trade_count?: number;
      winrate?: number;
      max_drawdown_abs?: number;
    };
    error?: string;
  };
  open_trades: {
    ok: boolean;
    count: number;
    items: Array<Record<string, unknown>>;
    error?: string;
  };
  recent_trades: {
    ok: boolean;
    items: Array<Record<string, unknown>>;
    error?: string;
  };
}

export async function fetchPaperSummary(): Promise<PaperSummary> {
  const response = await fetch('/api/paper/summary');
  if (!response.ok) {
    throw new Error(`paper summary failed: ${response.status}`);
  }
  return response.json() as Promise<PaperSummary>;
}
