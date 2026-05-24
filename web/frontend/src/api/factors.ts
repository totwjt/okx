export interface FactorDataset {
  ok: boolean;
  source: string;
  file: string;
  filename: string;
  pair_key?: string;
  pair?: string;
  timeframe?: string;
  kind: string;
  rows?: number;
  unique_timestamps?: number;
  start?: string | null;
  end?: string | null;
  expected_interval_seconds?: number | null;
  gap_count?: number;
  missing_intervals?: number;
  max_gap_seconds?: number;
  samples?: Array<{
    from?: string | null;
    to?: string | null;
    gap_seconds: number;
    missing_intervals: number;
  }>;
  error?: string;
}

export interface FactorsHealth {
  ok: boolean;
  summary: {
    dataset_count?: number;
    ohlcv_count?: number;
    funding_count?: number;
    gap_dataset_count?: number;
    error_count?: number;
  };
  coverage: {
    ohlcv: FactorDataset[];
    funding: FactorDataset[];
  };
  error?: string;
}

export async function fetchFactorsHealth(): Promise<FactorsHealth> {
  const response = await fetch('/api/factors/health');
  if (!response.ok) {
    throw new Error(`factors health failed: ${response.status}`);
  }
  return response.json() as Promise<FactorsHealth>;
}
