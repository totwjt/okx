export interface StrategySummary {
  slug: string;
  name: string;
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

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchStrategies(): Promise<StrategySummary[]> {
  const payload = await getJson<{ items: StrategySummary[] }>('/api/strategies');
  return payload.items;
}

export async function fetchStrategy(slug: string): Promise<StrategyDetail> {
  return getJson<StrategyDetail>(`/api/strategies/${slug}`);
}

export async function fetchStrategyProfiles(slug: string): Promise<StrategyProfile[]> {
  const payload = await getJson<{ strategy_slug: string; items: StrategyProfile[] }>(
    `/api/strategies/${slug}/profiles`,
  );
  return payload.items;
}

