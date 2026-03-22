import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { uploadSession, getSession } from './client';

describe('client error handling', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('uploadSession throws an Error when server returns 422', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      text: () => Promise.resolve('Validation failed: missing quarter'),
    });

    const file = new File(['data'], 'plan.xlsx');
    await expect(uploadSession(file, 0)).rejects.toThrow('Validation failed: missing quarter');
  });

  it('uploadSession throws a fallback Error when response body is empty on 422', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      text: () => Promise.resolve(''),
    });

    const file = new File(['data'], 'plan.xlsx');
    await expect(uploadSession(file, 0)).rejects.toThrow('HTTP 422');
  });

  it('getSession throws an Error when server returns 404', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve('Session not found'),
    });

    await expect(getSession('missing-id')).rejects.toThrow('Session not found');
  });

  it('getSession throws a fallback Error when response body is empty on 404', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve(''),
    });

    await expect(getSession('missing-id')).rejects.toThrow('HTTP 404');
  });
});
