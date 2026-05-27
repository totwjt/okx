export type JobStatus = 'pending' | 'running' | 'success' | 'failed';

export interface StrategySummary {
  slug: string;
  name: string;
  raw_name?: string | null;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  profile_count: number;
  active_profile: string | null;
}

export interface StrategyDetail extends StrategySummary {
  spec: Record<string, unknown>;
}

export interface StrategyDraftPayload {
  slug: string;
  name: string;
  description: string;
  profile_name: string;
  thesis: Record<string, string>;
}

export interface StrategyResetResult {
  reset: boolean;
  table_counts: Record<string, number>;
  deleted_artifact_paths: string[];
  service_pause: {
    ok: boolean;
    skipped: boolean;
    reason?: string;
    returncode?: number;
    stdout?: string;
    stderr?: string;
  };
}

export interface ProfileDraftPayload {
  profile_name: string;
  source_profile?: string | null;
  overrides?: Record<string, unknown>;
  thesis?: Record<string, string>;
}

export interface ProfileOverridesPayload {
  overrides: Record<string, unknown>;
}

export interface StrategyProfile {
  profile_name: string;
  status: string;
  source: string | null;
  is_active: boolean;
  overrides: Record<string, unknown>;
  validation: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WebJob {
  id: number;
  job_type: string;
  status: JobStatus;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error_summary: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  updated_at: string;
}

export interface RuntimeArtifact {
  id: number;
  strategy_slug: string;
  profile_name: string;
  artifact_type: string;
  artifact_path: string;
  artifact_hash: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface SystemCheck {
  ok: boolean;
  operations_ready: boolean;
  checks: Record<string, { ok: boolean; [key: string]: unknown }>;
}

export interface LifecycleEvidence {
  label_zh: string;
  value: string | number | boolean | null;
  source: string;
}

export interface LifecycleGateCheck {
  label_zh: string;
  value: string | number | boolean | null;
  status: string;
}

export interface LifecycleStatusDefinition {
  title_zh: string;
  description_zh: string;
  related_content_zh: string;
}

export interface LifecycleStep {
  key: string;
  title_zh: string;
  description_zh: string;
  required: boolean;
  status: 'completed' | 'pending' | 'blocked' | 'locked';
  inputs: string[];
  outputs: string[];
  evidence: LifecycleEvidence[];
  gate_checks: LifecycleGateCheck[];
  blocked_reasons: string[];
  next_actions: string[];
  substeps: LifecycleStep[];
}

export interface PaperRun {
  id: number;
  run_name: string;
  strategy_slug: string;
  profile_name: string;
  artifact_hash: string | null;
  config_hash: string | null;
  dry_run: boolean;
  started_at: string;
  ended_at: string | null;
  start_balance: number | null;
  current_balance: number | null;
  natural_closed_trades: number;
  force_trades: number;
  pnl: number | null;
  max_drawdown: number | null;
  status: string;
  review_conclusion: string | null;
  metadata: Record<string, unknown>;
}

export interface LifecycleStrategyDetail {
  strategy: StrategySummary & { spec?: Record<string, unknown> };
  profiles: StrategyProfile[];
  default_profile_name: string | null;
  status_definitions: Record<string, LifecycleStatusDefinition>;
}

export interface LifecycleProfileDetail {
  strategy: StrategySummary & { spec?: Record<string, unknown> };
  profile: StrategyProfile;
  status_definitions: Record<string, LifecycleStatusDefinition>;
  summary: {
    current_status: string;
    current_status_zh: string;
    current_step_key: string;
    current_step_title_zh: string;
    completed_steps: number;
    total_steps: number;
    blocked_reasons: string[];
    next_actions: string[];
  };
  assistant_plan: {
    mode_zh: string;
    can_auto_advance: boolean;
    next_step_zh: string;
    codex_prompt_zh: string;
    attempt_policy_zh: string;
    branching_policy_zh: string;
    recent_job_count: number;
  };
  alignment: {
    ok: boolean;
    status: 'aligned' | 'drift' | 'unknown';
    summary_zh: string;
    blocked_reasons: string[];
    checks: Array<{
      key: string;
      title_zh: string;
      passed: boolean;
      required: boolean;
      status: 'passed' | 'failed' | 'unknown';
      details_zh: string;
      evidence: Record<string, unknown>;
    }>;
  };
  paper_run: PaperRun | null;
  thesis: {
    values: Record<string, string>;
    missing_fields: string[];
    recommended_missing_fields?: string[];
    complete: boolean;
  };
  thesis_required_fields: Record<string, string>;
  promotion_events: Array<{
    id: number;
    from_status: string | null;
    to_status: string;
    reason: string | null;
    metadata: Record<string, unknown>;
    created_at: string;
  }>;
  steps: LifecycleStep[];
}

export interface BacktestPayload {
  strategy_slug: string;
  profile_name?: string | null;
  phase: 'train' | 'validation' | 'test' | 'custom';
  timerange?: string | null;
}

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

export interface PaperSummary {
  ok: boolean;
  mode: string;
  execution_baseline: string;
  websocket_enabled: boolean;
  dry_run: boolean;
  trading_mode: string;
  margin_mode: string;
  pair_whitelist: string[];
  api: { ok: boolean; url: string };
  balance: { ok: boolean; data?: Record<string, number | string | undefined>; error?: string };
  profit: { ok: boolean; data?: Record<string, number | undefined>; error?: string };
  open_trades: { ok: boolean; count: number; items: Array<Record<string, unknown>>; error?: string };
  recent_trades: { ok: boolean; items: Array<Record<string, unknown>>; error?: string };
}

export interface RiskSummary {
  ok: boolean;
  mode: string;
  source: Record<string, unknown>;
  strategy: Record<string, string | undefined>;
  rules: Record<string, number | boolean | undefined>;
  metrics: Record<string, unknown>;
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
