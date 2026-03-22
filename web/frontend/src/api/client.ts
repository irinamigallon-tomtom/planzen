import type { SessionState, SessionSummary, CapacityConfig, Epic, ComputeResponse } from '../types';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadSession(file: File, quarter: number): Promise<SessionState> {
  const form = new FormData();
  form.append('file', file);
  form.append('quarter', String(quarter));
  const res = await fetch('/api/sessions/upload', { method: 'POST', body: form });
  return handleResponse<SessionState>(res);
}

export async function listSessions(): Promise<SessionSummary[]> {
  const res = await fetch('/api/sessions');
  return handleResponse<SessionSummary[]>(res);
}

export async function getSession(id: string): Promise<SessionState> {
  const res = await fetch(`/api/sessions/${id}`);
  return handleResponse<SessionState>(res);
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }
}

export async function updateCapacity(id: string, capacity: CapacityConfig): Promise<SessionState> {
  const res = await fetch(`/api/sessions/${id}/capacity`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(capacity),
  });
  return handleResponse<SessionState>(res);
}

export async function updateEpics(id: string, epics: Epic[]): Promise<SessionState> {
  const res = await fetch(`/api/sessions/${id}/epics`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(epics),
  });
  return handleResponse<SessionState>(res);
}

export async function updateOverrides(
  id: string,
  overrides: Record<string, Record<string, number>>,
): Promise<SessionState> {
  const res = await fetch(`/api/sessions/${id}/overrides`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(overrides),
  });
  return handleResponse<SessionState>(res);
}

export async function computeAllocation(id: string): Promise<ComputeResponse> {
  const res = await fetch(`/api/sessions/${id}/compute`, { method: 'POST' });
  return handleResponse<ComputeResponse>(res);
}

export async function exportSession(id: string): Promise<Blob> {
  const res = await fetch(`/api/sessions/${id}/export`);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.blob();
}
