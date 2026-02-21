import { useState, useCallback, useRef, useEffect } from 'react';
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
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => { controllerRef.current?.abort(); };
  }, []);

  const execute = useCallback(async (body: TReq) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setState({ data: null, loading: true, error: null });
    try {
      const res = await api.post<TRes>(endpoint, body, { signal: controller.signal });
      setState({ data: res.data, loading: false, error: null });
      return res.data;
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'CanceledError') return null;
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
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => { controllerRef.current?.abort(); };
  }, []);

  const execute = useCallback(async (params?: Record<string, unknown>) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setState({ data: null, loading: true, error: null });
    try {
      const res = await api.get<TRes>(endpoint, { params, signal: controller.signal });
      setState({ data: res.data, loading: false, error: null });
      return res.data;
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'CanceledError') return null;
      const msg = err instanceof Error ? err.message : 'Error desconocido';
      setState({ data: null, loading: false, error: msg });
      return null;
    }
  }, [endpoint]);

  return { ...state, execute };
}
