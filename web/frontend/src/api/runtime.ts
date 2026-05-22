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

export interface MaterializeResult {
  strategy_slug: string;
  profile_name: string;
  artifacts: Array<{
    artifact_type: string;
    artifact_path: string;
    artifact_hash: string;
  }>;
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchRuntimeArtifacts(limit = 50): Promise<RuntimeArtifact[]> {
  const payload = await getJson<{ items: RuntimeArtifact[] }>(
    `/api/runtime/artifacts?limit=${limit}`,
  );
  return payload.items;
}

export async function materializeRuntime(
  strategySlug: string,
  profileName?: string | null,
): Promise<MaterializeResult> {
  const response = await fetch('/api/runtime/materialize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      strategy_slug: strategySlug,
      profile_name: profileName || null,
    }),
  });
  if (!response.ok) {
    throw new Error(`materialize failed: ${response.status}`);
  }
  return response.json() as Promise<MaterializeResult>;
}
