export type JobStatus = 'pending' | 'running' | 'success' | 'failed';

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

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchJobs(limit = 100): Promise<WebJob[]> {
  const payload = await getJson<{ items: WebJob[] }>(`/api/jobs?limit=${limit}`);
  return payload.items;
}

export async function createJob(
  jobType: string,
  payload: Record<string, unknown>,
): Promise<WebJob> {
  const response = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_type: jobType,
      payload,
    }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    const message = detail?.detail?.error_summary ?? `job failed: ${response.status}`;
    throw new Error(message);
  }
  return response.json() as Promise<WebJob>;
}
