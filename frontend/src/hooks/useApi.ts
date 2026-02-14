import { useState, useCallback } from 'react';
import api from '../api/client';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function usePost<TReq, TRes>(endpoint: string) {
  const [state, setState] = useState<UseApiState<TRes>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (body: TReq) => {
    setState({ data: null, loading: true, error: null });
    try {
      const res = await api.post<TRes>(endpoint, body);
      setState({ data: res.data, loading: false, error: null });
      return res.data;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error desconocido';
      setState({ data: null, loading: false, error: msg });
      return null;
    }
  }, [endpoint]);

  return { ...state, execute };
}

export function useGet<TRes>(endpoint: string) {
  const [state, setState] = useState<UseApiState<TRes>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (params?: Record<string, unknown>) => {
    setState({ data: null, loading: true, error: null });
    try {
      const res = await api.get<TRes>(endpoint, { params });
      setState({ data: res.data, loading: false, error: null });
      return res.data;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error desconocido';
      setState({ data: null, loading: false, error: msg });
      return null;
    }
  }, [endpoint]);

  return { ...state, execute };
}
