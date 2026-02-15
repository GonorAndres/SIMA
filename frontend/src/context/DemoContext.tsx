import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import demoSteps from './demoSteps';

interface DemoContextValue {
  active: boolean;
  step: number;
  totalSteps: number;
  narrativeKey: string;
  next: () => void;
  prev: () => void;
  start: () => void;
  stop: () => void;
}

const DemoContext = createContext<DemoContextValue | null>(null);

export function useDemoContext() {
  const ctx = useContext(DemoContext);
  if (!ctx) throw new Error('useDemoContext must be used inside DemoProvider');
  return ctx;
}

export function useDemo() {
  return useContext(DemoContext);
}

export function DemoProvider({ children }: { children: React.ReactNode }) {
  const [active, setActive] = useState(false);
  const [step, setStep] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const totalSteps = demoSteps.length;
  const currentStep = demoSteps[step] ?? demoSteps[0];

  const scrollToSection = useCallback((scrollTo?: string) => {
    if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
    scrollTimeoutRef.current = setTimeout(() => {
      if (!scrollTo || scrollTo === 'top') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
      }
      const el = document.querySelector(`[data-demo-section="${scrollTo}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 350);
  }, []);

  const goToStep = useCallback((nextStep: number) => {
    if (nextStep < 0 || nextStep >= totalSteps) return;
    const target = demoSteps[nextStep];
    setStep(nextStep);

    if (target.path !== location.pathname) {
      navigate(target.path);
    }
    // Scroll will be triggered by the effect below
  }, [totalSteps, location.pathname, navigate]);

  // When step changes, scroll to the target section
  useEffect(() => {
    if (!active) return;
    scrollToSection(currentStep.scrollTo);
  }, [active, step, currentStep.scrollTo, scrollToSection]);

  const next = useCallback(() => goToStep(step + 1), [goToStep, step]);
  const prev = useCallback(() => goToStep(step - 1), [goToStep, step]);

  const start = useCallback(() => {
    setStep(0);
    setActive(true);
    navigate('/');
  }, [navigate]);

  const stop = useCallback(() => {
    setActive(false);
    if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
  }, []);

  // Keyboard navigation
  useEffect(() => {
    if (!active) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); next(); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
      if (e.key === 'Escape') { e.preventDefault(); stop(); }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [active, next, prev, stop]);

  return (
    <DemoContext.Provider value={{
      active,
      step,
      totalSteps,
      narrativeKey: currentStep.narrativeKey,
      next,
      prev,
      start,
      stop,
    }}>
      {children}
    </DemoContext.Provider>
  );
}
