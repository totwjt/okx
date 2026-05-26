import { apiJson, postJson, putJson } from './client';
import type {
  BacktestPayload,
  FactorsHealth,
  LifecycleProfileDetail,
  LifecycleStrategyDetail,
  PaperRun,
  PaperSummary,
  ProfileDraftPayload,
  ProfileOverridesPayload,
  RiskSummary,
  RuntimeArtifact,
  StrategyDraftPayload,
  StrategyDetail,
  StrategyProfile,
  StrategySummary,
  SystemCheck,
  ValidationPayload,
  WebJob,
} from './types';

export * from './types';

export const api = {
  systemCheck: () => apiJson<SystemCheck>('/api/system/check'),
  strategies: async () => (await apiJson<{ items: StrategySummary[] }>('/api/strategies')).items,
  strategy: (slug: string) => apiJson<StrategyDetail>(`/api/strategies/${slug}`),
  createStrategy: (payload: StrategyDraftPayload) => postJson<Record<string, unknown>>('/api/strategies', payload),
  createProfile: (slug: string, payload: ProfileDraftPayload) =>
    postJson<Record<string, unknown>>(`/api/strategies/${slug}/profiles`, payload),
  updateProfileOverrides: (slug: string, profileName: string, payload: ProfileOverridesPayload) =>
    putJson<Record<string, unknown>>(`/api/strategies/${slug}/profiles/${encodeURIComponent(profileName)}/overrides`, payload),
  scaffoldDefinition: (slug: string, profileName?: string | null) =>
    postJson<Record<string, unknown>>(
      `/api/strategies/${slug}/definition/scaffold${profileName ? `?profile_name=${encodeURIComponent(profileName)}` : ''}`,
      {},
    ),
  scaffoldProfileDefaults: (slug: string, profileName: string) =>
    postJson<Record<string, unknown>>(`/api/strategies/${slug}/profiles/${encodeURIComponent(profileName)}/defaults`, {}),
  profiles: async (slug: string) =>
    (await apiJson<{ strategy_slug: string; items: StrategyProfile[] }>(
      `/api/strategies/${slug}/profiles`,
    )).items,
  runtimeArtifacts: async (limit = 50) =>
    (await apiJson<{ items: RuntimeArtifact[] }>(`/api/runtime/artifacts?limit=${limit}`)).items,
  jobs: async (limit = 100) => (await apiJson<{ items: WebJob[] }>(`/api/jobs?limit=${limit}`)).items,
  createJob: (jobType: string, payload: Record<string, unknown>) =>
    postJson<WebJob>('/api/jobs', { job_type: jobType, payload }),
  backtestResults: async (limit = 50) =>
    (await apiJson<{ items: WebJob[] }>(`/api/backtests/results?limit=${limit}`)).items,
  validationResults: async (limit = 50) =>
    (await apiJson<{ items: WebJob[] }>(`/api/validation/results?limit=${limit}`)).items,
  runBacktest: (payload: BacktestPayload) => api.createJob('backtest', { ...payload }),
  runValidation: (payload: ValidationPayload) => api.createJob('validation', { ...payload }),
  ensureData: (payload: Record<string, unknown>) => postJson<WebJob>('/api/data/ensure', payload),
  promoteProfile: (strategySlug: string, profileName: string, toStatus = 'validated') =>
    postJson<{ promoted: boolean }>('/api/profiles/promote', {
      strategy_slug: strategySlug,
      profile_name: profileName,
      to_status: toStatus,
      reason: 'web validation gate',
    }),
  lifecycleStrategies: async () =>
    (await apiJson<{ items: StrategySummary[] }>('/api/lifecycle/strategies')).items,
  lifecycleStrategy: (slug: string) => apiJson<LifecycleStrategyDetail>(`/api/lifecycle/${slug}`),
  lifecycleProfile: (strategySlug: string, profileName: string) =>
    apiJson<LifecycleProfileDetail>(
      `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}`,
    ),
  evidenceCheck: (strategySlug: string, profileName: string, targetStatus = 'validated') =>
    postJson<Record<string, unknown>>(
      `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}/evidence-check`,
      { target_status: targetStatus },
    ),
  advanceLifecycle: (strategySlug: string, profileName: string, candidateCount = 3) =>
    postJson<Record<string, unknown>>(
      `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}/advance`,
      { candidate_count: candidateCount },
    ),
  promoteLifecycle: (strategySlug: string, profileName: string, toStatus: string, reason: string) =>
    postJson<Record<string, unknown>>(
      `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}/promote`,
      { to_status: toStatus, reason },
    ),
  demoteLifecycle: (strategySlug: string, profileName: string, toStatus: string, reason: string) =>
    postJson<Record<string, unknown>>(
      `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}/demote`,
      { to_status: toStatus, reason },
    ),
  createPaperRun: (strategySlug: string, profileName: string, runName?: string) =>
    postJson<PaperRun>('/api/lifecycle/paper-runs', {
      strategy_slug: strategySlug,
      profile_name: profileName,
      run_name: runName || null,
    }),
  reviewPaperRun: (runId: number, passed: boolean, conclusion: string) =>
    postJson<PaperRun>(`/api/lifecycle/paper-runs/${runId}/review`, { passed, conclusion }),
  updateThesis: (strategySlug: string, profileName: string, thesis: Record<string, string>) =>
    putJson<{ updated: boolean; thesis: Record<string, string> }>(
      `/api/lifecycle/${strategySlug}/profiles/${encodeURIComponent(profileName)}/thesis`,
      { thesis },
    ),
  materialize: (strategySlug: string, profileName?: string | null) =>
    api.createJob('materialize', {
      strategy_slug: strategySlug,
      profile_name: profileName || null,
    }),
  factorsHealth: () => apiJson<FactorsHealth>('/api/factors/health'),
  paperSummary: () => apiJson<PaperSummary>('/api/paper/summary'),
  riskSummary: () => apiJson<RiskSummary>('/api/risk/summary'),
};
