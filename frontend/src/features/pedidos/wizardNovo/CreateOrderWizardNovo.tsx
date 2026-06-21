/**
 * CreateOrderWizardNovo — wizard de criação de pedido com o visual "atelier de floricultura".
 * Porta a orquestração do CreateOrderWizard original (react-hook-form + Zod, rascunho em
 * localStorage, validação por etapa, pulo de Entrega para Retirada, submit) trocando a
 * apresentação MUI pela marcação `pw-*` do mockup. As fontes seguem as do app (Jost/Fraunces).
 */
import './wizardNovo.css';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm, FormProvider, useWatch } from 'react-hook-form';
import type { FieldPath } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  User, Flower2, MapPin, CreditCard, Check, ChevronRight, ChevronLeft, Save, Loader2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import {
  pedidoFormSchema, pedidoFormDefaultValues, transformFormToApiPayload, type PedidoFormData,
} from '../schemas';
import { useOrderFormContext } from '../contexts/OrderFormContext';
import { useConfirm } from '../../../components/system/useConfirm';
import { entregaExtrasDefaults, mergeEntregaExtras, type PedidoFormDataExt } from './types';
import { StepClienteNovo } from './steps/StepClienteNovo';
import { StepProdutoNovo } from './steps/StepProdutoNovo';
import { StepEntregaNovo } from './steps/StepEntregaNovo';
import { StepPagamentoNovo } from './steps/StepPagamentoNovo';
import { ResumoVivo } from './components/ResumoVivo';
import { CartaoEntrega } from './components/CartaoEntrega';

const STORAGE_KEY = 'puf_pedido_draft_v2';
const DEBOUNCE_DELAY = 500;

type StepKey = 'cliente' | 'produto' | 'entrega' | 'pagamento';
interface StepDef { key: StepKey; label: string; icon: LucideIcon; fields: FieldPath<PedidoFormData>[]; }

const STEPS: StepDef[] = [
  { key: 'cliente', label: 'Cliente', icon: User, fields: ['cliente', 'telefone_cliente', 'destinatario', 'tipo_pedido'] },
  { key: 'produto', label: 'Produto', icon: Flower2, fields: ['produto', 'valor', 'dia_entrega', 'horario'] },
  { key: 'entrega', label: 'Entrega', icon: MapPin, fields: ['rua', 'numero', 'cidade', 'endereco'] },
  {
    key: 'pagamento',
    label: 'Pagamento',
    icon: CreditCard,
    fields: [
      'pagamento',
      'parcelas_cartao',
      'status_pagamento',
      'forma_pagamento_entrada',
      'forma_pagamento_restante',
    ],
  },
];

function useIsMobile(bp = 860) {
  const [m, setM] = useState(() => typeof window !== 'undefined' && window.innerWidth <= bp);
  useEffect(() => {
    const on = () => setM(window.innerWidth <= bp);
    window.addEventListener('resize', on);
    return () => window.removeEventListener('resize', on);
  }, [bp]);
  return m;
}

function isDraftMeaningful(draft: Partial<PedidoFormDataExt> | null, initialData?: Partial<PedidoFormData>): boolean {
  if (!draft) return false;
  const fields: (keyof PedidoFormData)[] = [
    'cliente', 'telefone_cliente', 'destinatario', 'produto', 'valor', 'mensagem',
    'rua', 'numero', 'endereco', 'flores_cor', 'obs_entrega', 'observacoes', 'cep', 'bairro', 'cidade',
  ];
  return fields.some((k) => {
    const v = draft[k];
    if (typeof v !== 'string') return false;
    const trimmed = v.trim();
    if (!trimmed) return false;
    const initVal = initialData?.[k];
    if (typeof initVal === 'string' && initVal.trim() === trimmed) return false;
    return true;
  });
}

interface Props {
  onSubmit: (data: Record<string, unknown>) => Promise<boolean>;
  isSubmitting?: boolean;
  submitError?: string | null;
  onClearError?: () => void;
  initialData?: Partial<PedidoFormData>;
  onReset?: () => void;
}

export function CreateOrderWizardNovo({
  onSubmit, isSubmitting = false, submitError, onClearError, initialData, onReset,
}: Props) {
  const isMobile = useIsMobile(860);
  const { activeStep, setActiveStep, reset: resetOrderFormContext } = useOrderFormContext();
  const confirm = useConfirm();

  const methods = useForm<PedidoFormDataExt>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(pedidoFormSchema) as any,
    defaultValues: { ...pedidoFormDefaultValues, ...entregaExtrasDefaults, ...initialData },
    mode: 'onBlur',
  });
  const { watch, control, trigger, getValues, setError, reset } = methods;

  const [storedDraft] = useState<Partial<PedidoFormDataExt> | null>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? (JSON.parse(stored) as Partial<PedidoFormDataExt>) : null;
    } catch { return null; }
  });
  const [draftResolved, setDraftResolved] = useState(false);
  const draftDecidedRef = useRef(false);

  // Aplica initialData (prefill/fonte) quando muda.
  const initialDataKey = useMemo(() => JSON.stringify(initialData ?? {}), [initialData]);
  const appliedInitialDataRef = useRef<string | null>(null);
  useEffect(() => {
    if (!initialData) return;
    if (appliedInitialDataRef.current === initialDataKey) return;
    appliedInitialDataRef.current = initialDataKey;
    reset({ ...getValues(), ...initialData }, { keepDirty: true });
  }, [initialData, initialDataKey, reset, getValues]);

  // Pergunta antes de retomar rascunho.
  useEffect(() => {
    if (draftDecidedRef.current) return;
    draftDecidedRef.current = true;
    if (!isDraftMeaningful(storedDraft, initialData)) { setDraftResolved(true); return; }
    (async () => {
      const resume = await confirm({
        title: 'Retomar rascunho?',
        description: 'Encontramos um pedido que você começou e não finalizou. Deseja continuar de onde parou?',
        confirmText: 'Retomar', cancelText: 'Começar novo',
      });
      if (resume && storedDraft) {
        reset({ ...pedidoFormDefaultValues, ...entregaExtrasDefaults, ...storedDraft, ...initialData });
      } else {
        try { localStorage.removeItem(STORAGE_KEY); } catch { /* noop */ }
      }
      setDraftResolved(true);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-save (após decisão do rascunho).
  useEffect(() => {
    if (!draftResolved) return;
    let timeoutId: ReturnType<typeof setTimeout>;
    const sub = watch((data) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch { /* noop */ }
      }, DEBOUNCE_DELAY);
    });
    return () => { clearTimeout(timeoutId); sub.unsubscribe(); };
  }, [watch, draftResolved]);

  useEffect(() => { onClearError?.(); }, [activeStep, onClearError]);

  const tipoPedido = useWatch({ control, name: 'tipo_pedido' });
  const isEntrega = tipoPedido === 'Entrega';
  const statusPagamento = useWatch({ control, name: 'status_pagamento' });
  const formaPagamento = useWatch({ control, name: 'pagamento' });
  const pagamentoInvalido = statusPagamento === 'Pago' && !formaPagamento;

  const visibleSteps = useMemo(
    () => STEPS.filter((s) => isEntrega || s.key !== 'entrega'),
    [isEntrega],
  );
  const current = STEPS[Math.min(activeStep, STEPS.length - 1)];
  const last = activeStep === STEPS.length - 1; // 'pagamento'
  const curVisibleIdx = visibleSteps.findIndex((s) => s.key === current.key);

  // --- Navegação (espelha o wizard original) ---
  const validateStep = async (step: number): Promise<boolean> => {
    const cfg = STEPS[step];
    if (!cfg) return true;
    if (cfg.key === 'entrega' && !isEntrega) return true;
    return trigger(cfg.fields as FieldPath<PedidoFormDataExt>[]);
  };

  const handleNext = async () => {
    if (!(await validateStep(activeStep))) return;
    if (activeStep >= STEPS.length - 1) return;
    let next = activeStep + 1;
    if (next === 2 && !isEntrega) next = 3; // pula Entrega na Retirada
    setActiveStep(next);
  };

  const handleBack = () => {
    if (activeStep <= 0) return;
    let prev = activeStep - 1;
    if (activeStep === 3 && !isEntrega) prev = 1;
    setActiveStep(prev);
  };

  const goToStepKey = async (targetFullIdx: number) => {
    if (targetFullIdx <= activeStep) { setActiveStep(targetFullIdx); return; }
    for (let i = activeStep; i < targetFullIdx; i++) {
      if (!(await validateStep(i))) { setActiveStep(i); return; }
    }
    setActiveStep(targetFullIdx);
  };

  const handleResetForm = () => {
    reset({ ...pedidoFormDefaultValues, ...entregaExtrasDefaults });
    setActiveStep(0);
    resetOrderFormContext();
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* noop */ }
    onReset?.();
  };

  const handleConcluir = async () => {
    if (!last || pagamentoInvalido) return;
    const base = mergeEntregaExtras(getValues());
    const result = pedidoFormSchema.safeParse(base);
    if (!result.success) {
      result.error.issues.forEach((err) => {
        setError(err.path.join('.') as FieldPath<PedidoFormDataExt>, { type: 'manual', message: err.message });
      });
      return;
    }
    try {
      const payload = transformFormToApiPayload(base as PedidoFormData);
      const ok = await onSubmit(payload);
      if (ok) {
        try { localStorage.removeItem(STORAGE_KEY); } catch { /* noop */ }
        resetOrderFormContext();
      }
    } catch { /* tratado pelo pai */ }
  };

  // --- Stepper geometry ---
  const inset = `${50 / visibleSteps.length}%`;
  const fillW = visibleSteps.length > 1 ? `${(curVisibleIdx / (visibleSteps.length - 1)) * 100}%` : '0%';

  const renderStep = () => {
    switch (current.key) {
      case 'cliente': return <StepClienteNovo />;
      case 'produto': return <StepProdutoNovo />;
      case 'entrega': return <StepEntregaNovo />;
      case 'pagamento': return <StepPagamentoNovo isMobile={isMobile} />;
      default: return null;
    }
  };

  return (
    <FormProvider {...methods}>
      <ol className="pw-steps">
        <span className="pw-steps-track" style={{ left: inset, right: inset }}>
          <span className="pw-steps-fill" style={{ width: fillW }} />
        </span>
        {visibleSteps.map((s) => {
          const fullIdx = STEPS.findIndex((x) => x.key === s.key);
          const state = fullIdx < activeStep ? 'done' : fullIdx === activeStep ? 'now' : 'todo';
          const Ico = s.icon;
          return (
            <li key={s.key} className={`pw-stp ${state}`}
              onClick={() => state !== 'todo' && goToStepKey(fullIdx)}>
              <span className="pw-stp-dot">{state === 'done' ? <Check size={16} /> : <Ico size={16} />}</span>
              <span className="pw-stp-lbl">{s.label}</span>
            </li>
          );
        })}
      </ol>

      <div className="pw-grid">
        <section className="pw-card">
          {submitError && <div className="pw-err-banner">{submitError}</div>}

          <div className="pw-step-anim" key={current.key}>
            {renderStep()}
          </div>

          <p className="pw-autosave">
            <span className="pw-save-dot" /> Rascunho salvo automaticamente
            <span className="pw-sep">·</span>
            <button type="button" className="pw-link-inline" onClick={handleResetForm}>Limpar</button>
          </p>

          <div className="pw-actions">
            {activeStep > 0 && (
              <button type="button" className="pw-btn ghost" onClick={handleBack}>
                <ChevronLeft size={16} /> Voltar
              </button>
            )}
            {!last ? (
              <button type="button" className="pw-btn primary" onClick={handleNext}>
                Próximo <ChevronRight size={16} />
              </button>
            ) : (
              <button type="button" className="pw-btn primary" onClick={handleConcluir}
                disabled={isSubmitting || pagamentoInvalido}
                title={pagamentoInvalido ? 'Defina a forma de pagamento' : ''}>
                {isSubmitting ? <Loader2 size={15} className="pw-spin" /> : <Save size={15} />}
                {isSubmitting ? 'Salvando…' : 'Salvar e concluir'}
              </button>
            )}
          </div>
        </section>

        {!isMobile && (
          <aside className="pw-summary">
            <ResumoVivo />
            {current.key === 'entrega' && isEntrega && <CartaoEntrega />}
          </aside>
        )}
      </div>
    </FormProvider>
  );
}

export default CreateOrderWizardNovo;
