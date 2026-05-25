import { createJob, type WebJob } from './jobs';

export interface OptimizationParameter {
  path: string;
  title_zh: string;
  current: number;
  min: number;
  max: number;
  source: string;
}

export interface OptimizationCandidate {
  profile_name: string;
  status: string;
  is_active: boolean;
  diff: Array<{ path: string; baseline: unknown; candidate: unknown }>;
  train_metrics: Record<string, number>;
  validation_metrics: Record<string, number>;
  score: number;
  reasons_zh: string[];
  warnings_zh: string[];
}

export interface OptimizationAssistant {
  strategy_slug: string;
  baseline_profile: string;
  parameters: OptimizationParameter[];
  candidates: OptimizationCandidate[];
  scoring_zh: string[];
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchOptimizationAssistant(
  strategySlug: string,
  baselineProfile?: string,
): Promise<OptimizationAssistant> {
  const query = baselineProfile ? `?baseline_profile=${encodeURIComponent(baselineProfile)}` : '';
  return getJson<OptimizationAssistant>(`/api/optimization/${strategySlug}${query}`);
}

export async function saveDraftProfile(
  strategySlug: string,
  profileName: string,
  baselineProfile: string,
  overrides: Record<string, unknown>,
): Promise<{ saved: boolean; profile_name: string }> {
  const response = await fetch(`/api/optimization/${strategySlug}/profiles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      profile_name: profileName,
      baseline_profile: baselineProfile,
      overrides,
    }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `save draft profile failed: ${response.status}`);
  }
  return response.json() as Promise<{ saved: boolean; profile_name: string }>;
}

export async function startAutoTuneJob(
  strategySlug: string,
  baselineProfile: string,
  candidateCount = 3,
): Promise<WebJob> {
  return createJob('optimization', {
    strategy_slug: strategySlug,
    baseline_profile: baselineProfile,
    candidate_count: candidateCount,
    run_backtests: true,
  });
}
