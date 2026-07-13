import { createContext, useContext } from 'react';

export interface DemoContextValue {
  active: boolean;
  step: number;
  totalSteps: number;
  narrativeKey: string;
  next: () => void;
  prev: () => void;
  start: () => void;
  stop: () => void;
}

export const DemoContext = createContext<DemoContextValue | null>(null);

export function useDemoContext() {
  const ctx = useContext(DemoContext);
  if (!ctx) throw new Error('useDemoContext must be used inside DemoProvider');
  return ctx;
}

export function useDemo() {
  return useContext(DemoContext);
}
