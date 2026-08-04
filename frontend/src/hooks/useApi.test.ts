import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Mock } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useGet, usePost } from './useApi';
import api from '../api/client';

// Hermetic: the hooks talk only to the axios client.
vi.mock('../api/client', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

const apiGet = api.get as unknown as Mock;
const apiPost = api.post as unknown as Mock;

describe('useGet', () => {
  beforeEach(() => {
    apiGet.mockReset();
  });

  it('starts idle: no data, not loading, no error', () => {
    const { result } = renderHook(() => useGet<{ ok: boolean }>('/mortality/lee-carter'));

    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(apiGet).not.toHaveBeenCalled();
  });

  it('reports loading while the request is in flight, then stops', async () => {
    // THEORY: every page keys its spinners off this flag; if it never went
    // true the user would stare at a blank panel with no explanation.
    let resolveRequest!: (value: { data: { ok: boolean } }) => void;
    apiGet.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );
    const { result } = renderHook(() => useGet<{ ok: boolean }>('/mortality/lee-carter'));

    act(() => {
      void result.current.execute();
    });
    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolveRequest({ data: { ok: true } });
    });
    expect(result.current.loading).toBe(false);
  });

  it('exposes the response data on success and passes params through', async () => {
    apiGet.mockResolvedValueOnce({ data: { drift: -1.086 } });
    const { result } = renderHook(() => useGet<{ drift: number }>('/mortality/lee-carter'));

    await act(async () => {
      await result.current.execute({ sex: 'unisex' });
    });

    expect(result.current.data).toEqual({ drift: -1.086 });
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(apiGet).toHaveBeenCalledWith(
      '/mortality/lee-carter',
      expect.objectContaining({ params: { sex: 'unisex' } }),
    );
  });

  it('exposes the error message on failure, with no stale data', async () => {
    apiGet.mockRejectedValueOnce(new Error('Request failed with status code 500'));
    const { result } = renderHook(() => useGet<{ drift: number }>('/mortality/lee-carter'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.error).toBe('Request failed with status code 500');
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('keeps execute referentially stable across renders and state updates', async () => {
    // THEORY: the pages list `execute` in useEffect dependency arrays. If a
    // completed request produced a new function reference, the effect would
    // re-fire, request again, and loop forever -- a real, expensive bug.
    apiGet.mockResolvedValue({ data: { ok: true } });
    const { result, rerender } = renderHook(() => useGet<{ ok: boolean }>('/mortality/lee-carter'));
    const firstExecute = result.current.execute;

    rerender();
    expect(result.current.execute).toBe(firstExecute);

    // A completed request re-renders via setState; the reference must survive.
    await act(async () => {
      await result.current.execute();
    });
    expect(result.current.data).toEqual({ ok: true });
    expect(result.current.execute).toBe(firstExecute);
  });
});

describe('usePost', () => {
  beforeEach(() => {
    apiPost.mockReset();
  });

  it('starts idle: no data, not loading, no error', () => {
    const { result } = renderHook(() =>
      usePost<{ age: number }, { annual_premium: number }>('/pricing/premium'),
    );

    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(apiPost).not.toHaveBeenCalled();
  });

  it('reports loading while the request is in flight, then stops', async () => {
    let resolveRequest!: (value: { data: { annual_premium: number } }) => void;
    apiPost.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );
    const { result } = renderHook(() =>
      usePost<{ age: number }, { annual_premium: number }>('/pricing/premium'),
    );

    act(() => {
      void result.current.execute({ age: 30 });
    });
    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolveRequest({ data: { annual_premium: 12345 } });
    });
    expect(result.current.loading).toBe(false);
  });

  it('sends the body and exposes the response data on success', async () => {
    apiPost.mockResolvedValueOnce({ data: { annual_premium: 12345 } });
    const { result } = renderHook(() =>
      usePost<{ age: number }, { annual_premium: number }>('/pricing/premium'),
    );

    await act(async () => {
      await result.current.execute({ age: 30 });
    });

    expect(result.current.data).toEqual({ annual_premium: 12345 });
    expect(result.current.error).toBeNull();
    expect(apiPost).toHaveBeenCalledWith(
      '/pricing/premium',
      { age: 30 },
      expect.objectContaining({ signal: expect.anything() }),
    );
  });

  it('exposes the error message on failure, with no stale data', async () => {
    apiPost.mockRejectedValueOnce(new Error('timeout of 30000ms exceeded'));
    const { result } = renderHook(() =>
      usePost<{ age: number }, { annual_premium: number }>('/pricing/premium'),
    );

    await act(async () => {
      await result.current.execute({ age: 30 });
    });

    expect(result.current.error).toBe('timeout of 30000ms exceeded');
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('keeps execute referentially stable across renders and state updates', async () => {
    apiPost.mockResolvedValue({ data: { annual_premium: 12345 } });
    const { result, rerender } = renderHook(() =>
      usePost<{ age: number }, { annual_premium: number }>('/pricing/premium'),
    );
    const firstExecute = result.current.execute;

    rerender();
    expect(result.current.execute).toBe(firstExecute);

    await act(async () => {
      await result.current.execute({ age: 30 });
    });
    expect(result.current.execute).toBe(firstExecute);
  });
});
