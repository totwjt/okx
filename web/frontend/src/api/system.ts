export interface SystemCheck {
  ok: boolean;
  operations_ready: boolean;
  checks: Record<string, { ok: boolean; [key: string]: unknown }>;
}

export async function fetchSystemCheck(): Promise<SystemCheck> {
  const response = await fetch('/api/system/check');
  if (!response.ok) {
    throw new Error(`system check failed: ${response.status}`);
  }
  return response.json() as Promise<SystemCheck>;
}

