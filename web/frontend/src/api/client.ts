export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(url: string, status: number, detail: unknown) {
    super(extractErrorMessage(detail) ?? `${url} failed: ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

function extractErrorMessage(detail: unknown): string | null {
  if (!detail || typeof detail !== 'object') {
    return null;
  }
  const record = detail as Record<string, unknown>;
  if (typeof record.detail === 'string') {
    return record.detail;
  }
  const nested = record.detail;
  if (nested && typeof nested === 'object') {
    const nestedRecord = nested as Record<string, unknown>;
    if (typeof nestedRecord.error_summary === 'string') {
      return nestedRecord.error_summary;
    }
  }
  if (typeof record.error_summary === 'string') {
    return record.error_summary;
  }
  return null;
}

export async function apiJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ApiError(url, response.status, detail);
  }
  return response.json() as Promise<T>;
}

export function postJson<T>(url: string, body: unknown): Promise<T> {
  return apiJson<T>(url, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function putJson<T>(url: string, body: unknown): Promise<T> {
  return apiJson<T>(url, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

export function deleteJson<T>(url: string): Promise<T> {
  return apiJson<T>(url, {
    method: 'DELETE',
  });
}
