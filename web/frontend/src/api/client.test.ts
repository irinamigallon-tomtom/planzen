import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { uploadSession, getSession, deleteSession, updateCapacity, updateEpics, exportSession } from './client';
import type { CapacityConfig, Epic } from '../types';

describe('client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('uploadSession makes POST to /api/sessions/upload with correct FormData', async () => {
    const mockResponse = { session_id: 's1', filename: 'f.xlsx', quarter: 1, capacity: { eng_bruto: 0, eng_absence: 0, mgmt_capacity: 0, mgmt_absence: 0, eng_bruto_by_week: {}, eng_absence_by_week: {} }, epics: [], manual_overrides: {} };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const file = new File(['data'], 'plan.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const result = await uploadSession(file, 3);

    expect(fetch).toHaveBeenCalledOnce();
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe('/api/sessions/upload');
    expect(options.method).toBe('POST');
    expect(options.body).toBeInstanceOf(FormData);
    const fd = options.body as FormData;
    expect(fd.get('quarter')).toBe('3');
    expect(fd.get('file')).toBe(file);
    expect(result).toEqual(mockResponse);
  });

  it('getSession makes GET to /api/sessions/{id} and returns parsed JSON', async () => {
    const mockResponse = { session_id: 's1', filename: 'f.xlsx', quarter: 2, capacity: { eng_bruto: 10, eng_absence: 1, mgmt_capacity: 5, mgmt_absence: 0, eng_bruto_by_week: {}, eng_absence_by_week: {} }, epics: [], manual_overrides: {} };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await getSession('s1');

    expect(fetch).toHaveBeenCalledOnce();
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe('/api/sessions/s1');
    expect(options).toBeUndefined();
    expect(result).toEqual(mockResponse);
  });

  it('deleteSession makes DELETE to /api/sessions/{id} and resolves on 204', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true });

    await deleteSession('s1');

    expect(fetch).toHaveBeenCalledOnce();
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe('/api/sessions/s1');
    expect(options.method).toBe('DELETE');
  });

  it('updateCapacity makes PUT to /api/sessions/{id}/capacity with JSON body', async () => {
    const capacity: CapacityConfig = { eng_bruto: 40, eng_absence: 4, mgmt_capacity: 20, mgmt_absence: 2, eng_bruto_by_week: {}, eng_absence_by_week: {} };
    const mockResponse = { session_id: 's1', filename: 'f.xlsx', quarter: 1, capacity, epics: [], manual_overrides: {} };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await updateCapacity('s1', capacity);

    expect(fetch).toHaveBeenCalledOnce();
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe('/api/sessions/s1/capacity');
    expect(options.method).toBe('PUT');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(options.body)).toEqual(capacity);
    expect(result).toEqual(mockResponse);
  });

  it('updateEpics makes PUT to /api/sessions/{id}/epics with JSON body', async () => {
    const epics: Epic[] = [{ epic_description: 'E1', estimation: 5, budget_bucket: 'core', priority: 1, allocation_mode: 'Sprint', link: '', type: 'feature', milestone: 'M1' }];
    const mockResponse = { session_id: 's1', filename: 'f.xlsx', quarter: 1, capacity: { eng_bruto: 0, eng_absence: 0, mgmt_capacity: 0, mgmt_absence: 0, eng_bruto_by_week: {}, eng_absence_by_week: {} }, epics, manual_overrides: {} };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await updateEpics('s1', epics);

    expect(fetch).toHaveBeenCalledOnce();
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe('/api/sessions/s1/epics');
    expect(options.method).toBe('PUT');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(options.body)).toEqual(epics);
    expect(result).toEqual(mockResponse);
  });

  it('exportSession makes GET to /api/sessions/{id}/export and returns a Blob', async () => {
    const blob = new Blob(['binary'], { type: 'application/octet-stream' });
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(blob),
    });

    const result = await exportSession('s1');

    expect(fetch).toHaveBeenCalledOnce();
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe('/api/sessions/s1/export');
    expect(options).toBeUndefined();
    expect(result).toBeInstanceOf(Blob);
  });
});
