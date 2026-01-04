/**
 * OrderFormContext
 * Responsável por persistir estado crítico do wizard (step atual)
 * para evitar perda de progresso entre navegações/redirecionamentos.
 */

import { createContext, useContext, useMemo, useState, useCallback, ReactNode } from 'react';

const STEP_STORAGE_KEY = 'puf_pedido_step_v2';

type OrderFormContextValue = {
  activeStep: number;
  setActiveStep: (step: number) => void;
  reset: () => void;
};

const OrderFormContext = createContext<OrderFormContextValue | undefined>(undefined);

function getInitialStep(): number {
  if (typeof window === 'undefined') return 0;
  const stored = window.localStorage.getItem(STEP_STORAGE_KEY);
  const parsed = stored ? Number(stored) : NaN;
  if (Number.isFinite(parsed) && parsed >= 0 && parsed <= 3) {
    return parsed;
  }
  return 0;
}

export function OrderFormProvider({ children }: { children: ReactNode }) {
  const [activeStep, setActiveStepState] = useState<number>(getInitialStep);

  const setActiveStep = useCallback((step: number) => {
    setActiveStepState(step);
    try {
      window.localStorage.setItem(STEP_STORAGE_KEY, String(step));
    } catch {
      // Silencioso: falha em persistir step não deve quebrar fluxo
    }
  }, []);

  const reset = useCallback(() => {
    setActiveStep(0);
    try {
      window.localStorage.removeItem(STEP_STORAGE_KEY);
    } catch {
      // noop
    }
  }, [setActiveStep]);

  const value = useMemo(
    () => ({
      activeStep,
      setActiveStep,
      reset,
    }),
    [activeStep, setActiveStep, reset],
  );

  return <OrderFormContext.Provider value={value}>{children}</OrderFormContext.Provider>;
}

export function useOrderFormContext(): OrderFormContextValue {
  const ctx = useContext(OrderFormContext);
  if (!ctx) {
    throw new Error('useOrderFormContext deve ser usado dentro de OrderFormProvider');
  }
  return ctx;
}


