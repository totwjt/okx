import type { StrategyProfile, StrategySummary } from './strategies';

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

export interface EvidenceGateCheck {
  key: string;
  title_zh: string;
  passed: boolean;
  required: boolean;
  status: 'passed' | 'failed' | 'warning';
  details_zh: string;
  evidence: Record<string, unknown>;
}

export interface EvidenceGateResult {
  strategy_slug: string;
  profile_name: string;
  target_status: string;
  passed: boolean;
  thresholds: Record<string, number>;
  checks: EvidenceGateCheck[];
  failed_checks: EvidenceGateCheck[];
  warnings: EvidenceGateCheck[];
  summary_zh: string;
}

export interface PromotionResult {
  promoted?: boolean;
  demoted?: boolean;
  strategy_slug: string;
  profile_name: string;
  to_status: string;
  reason: string;
  evidence?: EvidenceGateResult;
  failed_checks?: EvidenceGateCheck[];
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchLifecycleStrategies(): Promise<StrategySummary[]> {
  const payload = await getJson<{ items: StrategySummary[] }>('/api/lifecycle/strategies');
  return payload.items;
}

export async function fetchLifecycleStrategy(slug: string): Promise<LifecycleStrategyDetail> {
  return getJson<LifecycleStrategyDetail>(`/api/lifecycle/${slug}`);
}

export async function fetchLifecycleProfile(
  strategySlug: string,
  profileName: string,
): Promise<LifecycleProfileDetail> {
  return getJson<LifecycleProfileDetail>(
    `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}`,
  );
}

export async function runEvidenceCheck(
  strategySlug: string,
  profileName: string,
  targetStatus = 'validated',
): Promise<EvidenceGateResult> {
  const response = await fetch(
    `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}/evidence-check`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_status: targetStatus }),
    },
  );
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `evidence check failed: ${response.status}`);
  }
  return response.json() as Promise<EvidenceGateResult>;
}

export async function promoteLifecycleProfile(
  strategySlug: string,
  profileName: string,
  toStatus: string,
  reason: string,
): Promise<PromotionResult> {
  return postLifecycleAction(strategySlug, profileName, 'promote', toStatus, reason);
}

export async function demoteLifecycleProfile(
  strategySlug: string,
  profileName: string,
  toStatus: string,
  reason: string,
): Promise<PromotionResult> {
  return postLifecycleAction(strategySlug, profileName, 'demote', toStatus, reason);
}

export async function createPaperRun(
  strategySlug: string,
  profileName: string,
  runName?: string,
): Promise<PaperRun> {
  const response = await fetch('/api/lifecycle/paper-runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      strategy_slug: strategySlug,
      profile_name: profileName,
      run_name: runName || null,
    }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `create paper run failed: ${response.status}`);
  }
  return response.json() as Promise<PaperRun>;
}

export async function reviewPaperRun(
  runId: number,
  passed: boolean,
  conclusion: string,
): Promise<PaperRun> {
  const response = await fetch(`/api/lifecycle/paper-runs/${runId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ passed, conclusion }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `review paper run failed: ${response.status}`);
  }
  return response.json() as Promise<PaperRun>;
}

export async function updateProfileThesis(
  strategySlug: string,
  profileName: string,
  thesis: Record<string, string>,
): Promise<{ updated: boolean; thesis: Record<string, string> }> {
  const response = await fetch(
    `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}/thesis`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thesis }),
    },
  );
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `update thesis failed: ${response.status}`);
  }
  return response.json() as Promise<{ updated: boolean; thesis: Record<string, string> }>;
}

async function postLifecycleAction(
  strategySlug: string,
  profileName: string,
  action: 'promote' | 'demote',
  toStatus: string,
  reason: string,
): Promise<PromotionResult> {
  const response = await fetch(
    `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}/${action}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ to_status: toStatus, reason }),
    },
  );
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `${action} failed: ${response.status}`);
  }
  return response.json() as Promise<PromotionResult>;
}
