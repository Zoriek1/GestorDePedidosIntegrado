/**
 * CreateOrderWizard - Wizard de Criação de Pedidos "Inteligente"
 * Container principal com Stepper responsivo e persistência localStorage
 * Integra todos os steps com validação incremental
 */

import { useState, useEffect, useMemo, useRef } from 'react';
import { createLogger } from '../../lib/logger';

const _log = createLogger('CreateOrderWizard');
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  useMediaQuery,
  useTheme,
  MobileStepper,
  Tooltip,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import SaveIcon from '@mui/icons-material/Save';
import KeyboardArrowLeft from '@mui/icons-material/KeyboardArrowLeft';
import KeyboardArrowRight from '@mui/icons-material/KeyboardArrowRight';

import {
  pedidoFormSchema,
  pedidoFormDefaultValues,
  transformFormToApiPayload,
  type PedidoFormData,
} from './schemas';
import type { FieldPath } from 'react-hook-form';
import {
  StepCliente,
  StepEntrega,
  StepProduto,
  StepPagamento,
} from './components/WizardSteps';
import { useOrderFormContext } from './contexts/OrderFormContext';
import { useConfirm } from '../../components/system/useConfirm';

// ============================================================================
// Constantes
// ============================================================================

const STORAGE_KEY = 'puf_pedido_draft_v2';
const DEBOUNCE_DELAY = 500;

/**
 * Um rascunho só vale o pop-up de "Retomar?" se o usuário tiver digitado algo de fato —
 * ignorando os campos que vieram de prefill (initialData), para não perguntar à toa.
 */
function isDraftMeaningful(
  draft: Partial<PedidoFormData> | null,
  initialData?: Partial<PedidoFormData>,
): boolean {
  if (!draft) return false;
  const fields: (keyof PedidoFormData)[] = [
    'cliente', 'telefone_cliente', 'destinatario', 'produto', 'valor', 'mensagem',
    'rua', 'numero', 'endereco', 'flores_cor', 'obs_entrega', 'observacoes',
    'cep', 'bairro', 'cidade',
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

const STEPS = [
  { label: 'Cliente', component: StepCliente, fields: ['cliente', 'telefone_cliente', 'destinatario', 'tipo_pedido'] as const },
  { label: 'Produto', component: StepProduto, fields: ['produto', 'valor', 'dia_entrega', 'horario'] as const },
  { label: 'Entrega', component: StepEntrega, fields: ['rua', 'numero', 'cidade', 'endereco'] as const },
  { label: 'Pagamento', component: StepPagamento, fields: ['pagamento', 'parcelas_cartao', 'status_pagamento'] as const },
];

// ============================================================================
// Props Interface
// ============================================================================

interface CreateOrderWizardProps {
  /** Callback chamado ao submeter o formulário. Retorna true em sucesso, false em erro. */
  onSubmit: (data: Record<string, unknown>) => Promise<boolean>;
  /** Se true, exibe loading no botão de salvar */
  isSubmitting?: boolean;
  /** Mensagem de erro do backend */
  submitError?: string | null;
  /** Callback para limpar erro */
  onClearError?: () => void;
  /** Valores iniciais (edição) */
  initialData?: Partial<PedidoFormData>;
  /** Callback para reiniciar o fluxo completo */
  onReset?: () => void;
  /**
   * Liga o rascunho local (autosave + diálogo "Retomar?"). Default `true` (criação).
   * Em edição deve ser `false`: os dados do servidor são a fonte da verdade e o rascunho
   * global de criação não deve interferir nem ser sobrescrito.
   */
  enableDraft?: boolean;
}

// ============================================================================
// Componente Principal
// ============================================================================

export function CreateOrderWizard({
  onSubmit,
  isSubmitting = false,
  submitError,
  onClearError,
  initialData,
  onReset,
  enableDraft = true,
}: CreateOrderWizardProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { activeStep, setActiveStep, reset: resetOrderFormContext } = useOrderFormContext();
  const [stepErrors, setStepErrors] = useState<Record<number, boolean>>({});
  const [isReadyToSubmit, setIsReadyToSubmit] = useState(false);

  // Lê o rascunho salvo uma única vez no mount, ANTES de o auto-save sobrescrevê-lo.
  // Não injeta direto: a decisão de retomar é feita via diálogo (#1).
  const [storedDraft] = useState<Partial<PedidoFormData> | null>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? (JSON.parse(stored) as Partial<PedidoFormData>) : null;
    } catch {
      return null;
    }
  });
  const confirm = useConfirm();
  // Auto-save só liga depois que o usuário decide sobre o rascunho — assim o form vazio
  // inicial não sobrescreve o rascunho antes da resposta.
  const [draftResolved, setDraftResolved] = useState(false);
  const draftDecidedRef = useRef(false);

  // Hook Form com Zod — inicia limpo (defaults + prefill), sem o rascunho.
  const methods = useForm<PedidoFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(pedidoFormSchema) as any,
    defaultValues: { ...pedidoFormDefaultValues, ...initialData },
    mode: 'onBlur',
  });

  const { handleSubmit, watch, trigger, setError, getValues, formState } = methods;

  // Aplica initialData via reset quando muda (ex: fonte escolhida após prefill de lead).
  // RHF só lê defaultValues uma vez no mount; sem isso, prefill chega "tarde" e fica perdido.
  const initialDataKey = useMemo(
    () => JSON.stringify(initialData ?? {}),
    [initialData]
  );
  const appliedInitialDataRef = useRef<string | null>(null);
  useEffect(() => {
    if (!initialData) return;
    if (appliedInitialDataRef.current === initialDataKey) return;
    appliedInitialDataRef.current = initialDataKey;
    methods.reset({ ...methods.getValues(), ...initialData }, { keepDirty: true });
  }, [initialData, initialDataKey, methods]);

  // No mount, decide o que fazer com o rascunho salvo: pergunta antes de retomar (#1).
  useEffect(() => {
    if (draftDecidedRef.current) return;
    draftDecidedRef.current = true;

    // Em edição (enableDraft=false), o servidor é a fonte da verdade: não retoma rascunho.
    if (!enableDraft || !isDraftMeaningful(storedDraft, initialData)) {
      setDraftResolved(true);
      return;
    }

    (async () => {
      const resume = await confirm({
        title: 'Retomar rascunho?',
        description:
          'Encontramos um pedido que você começou e não finalizou. Deseja continuar de onde parou?',
        confirmText: 'Retomar',
        cancelText: 'Começar novo',
      });
      if (resume && storedDraft) {
        // initialData (prefill) continua tendo prioridade sobre o rascunho.
        methods.reset({ ...pedidoFormDefaultValues, ...storedDraft, ...initialData });
      } else {
        try {
          localStorage.removeItem(STORAGE_KEY);
        } catch {
          // noop
        }
      }
      setDraftResolved(true);
    })();
    // Executa só uma vez no mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Salva no localStorage com debounce (só após a decisão sobre o rascunho).
  useEffect(() => {
    if (!draftResolved || !enableDraft) return;
    let timeoutId: ReturnType<typeof setTimeout>;

    const subscription = watch((data) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } catch {
          // Erro ao salvar rascunho (silenciado em produção)
        }
      }, DEBOUNCE_DELAY);
    });

    return () => {
      clearTimeout(timeoutId);
      subscription.unsubscribe();
    };
  }, [watch, draftResolved, enableDraft]);

  // Limpa erros ao mudar de step
  useEffect(() => {
    if (onClearError) {
      onClearError();
    }
  }, [activeStep, onClearError]);

  // Atualizar estado de submissão baseado no step atual (SEM delay)
  useEffect(() => {
    // Permitir submissão imediatamente ao chegar no último step
    if (activeStep === STEPS.length - 1) {
      setIsReadyToSubmit(true);
    } else {
      setIsReadyToSubmit(false);
    }
  }, [activeStep]);

  // Validação por step
  const validateStep = async (step: number): Promise<boolean> => {
    const stepConfig = STEPS[step];
    if (!stepConfig) {
      return true;
    }

    // Se o step é de Entrega e o tipo é Retirada, não validar (pula)
    if (stepConfig.label === 'Entrega') {
      const tipo = methods.getValues('tipo_pedido');
      if (tipo === 'Retirada') {
        return true;
      }
    }

    // Verificar se há campos para validar
    const fieldsToValidate = stepConfig.fields as unknown as (keyof PedidoFormData)[];
    if (fieldsToValidate.length === 0) {
      return true; // Step sem campos obrigatórios
    }

    const isValid = await trigger(fieldsToValidate);
    setStepErrors((prev) => ({ ...prev, [step]: !isValid }));
    return isValid;
  };

  // Navegação
  const handleNext = async () => {
    const isValid = await validateStep(activeStep);
    if (isValid && activeStep < STEPS.length - 1) {
      let nextStep = activeStep + 1;
      
      // Se está indo para o Step 2 (Entrega, índice 2) e o tipo de pedido é Retirada, pular para Step 3 (Pagamento)
      if (nextStep === 2) {
        const tipoPedido = watch('tipo_pedido');
        if (tipoPedido === 'Retirada') {
          nextStep = 3; // Pular Step 2 (Entrega) se for Retirada
        }
      }
      
      setActiveStep(nextStep);
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      let previousStep = activeStep - 1;
      
      // Se está voltando do Step 3 (Pagamento) e o tipo de pedido é Retirada, voltar para Step 1 (Produto, índice 1)
      if (activeStep === 3) {
        const tipoPedido = watch('tipo_pedido');
        if (tipoPedido === 'Retirada') {
          previousStep = 1; // Pular Step 2 (Entrega) se for Retirada
        }
      }
      
      setActiveStep(previousStep);
    }
  };

  const handleStepClick = (step: number) => {
    // Passos clicáveis apenas para voltar (<= índice atual). Avançar só pelo botão "Próximo".
    if (step <= activeStep) {
      setActiveStep(step);
    }
  };

  // Salvar apenas rascunho (sem submeter)
  const handleSaveDraft = () => {
    const currentData = methods.getValues();
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(currentData));
      // Rascunho salvo (feedback visual pode ser adicionado se necessário)
    } catch {
      // Erro ao salvar rascunho (silenciado em produção)
    }
  };

  // Submissão (salvar e concluir)
  const onFormSubmit = async (data: PedidoFormData) => {
    // DEBUG: Log detalhado para diagnóstico
    console.log('=== DEBUG SUBMIT ===');
    console.log('activeStep:', activeStep, 'STEPS.length - 1:', STEPS.length - 1);
    console.log('isReadyToSubmit:', isReadyToSubmit);
    console.log('Form data:', data);
    console.log('Form errors:', formState.errors);
    
    // Prevenir submissão automática: só permite se estiver no último step E isReadyToSubmit for true
    if (activeStep !== STEPS.length - 1 || !isReadyToSubmit) {
      console.warn('Submit bloqueado:', { activeStep, isReadyToSubmit, expectedStep: STEPS.length - 1 });
      return;
    }

    // Validação explícita antes de prosseguir
    const isValid = await validateFormExplicitly();
    if (!isValid) {
      console.error('Formulário inválido - submit cancelado');
      return;
    }

    try {
      console.log('Transformando payload...');
      const payload = transformFormToApiPayload(data);
      console.log('Payload transformado:', payload);
      
      console.log('Chamando onSubmit...');
      const ok = await onSubmit(payload);
      console.log('Resultado onSubmit:', ok);
      
      if (ok) {
        // Limpa o rascunho após sucesso
        localStorage.removeItem(STORAGE_KEY);
        resetOrderFormContext();
        setIsReadyToSubmit(false);
      }
    } catch (error) {
      // Erro é tratado pelo componente pai
      console.error('Erro ao salvar pedido:', error);
      console.error('Stack trace:', error instanceof Error ? error.stack : 'N/A');
    }
  };

  const handleResetForm = () => {
    methods.reset(pedidoFormDefaultValues);
    setActiveStep(0);
    setStepErrors({});
    setIsReadyToSubmit(false);
    resetOrderFormContext();
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // noop
    }
    if (onReset) {
      onReset();
    }
  };

  // Validação explícita do formulário com feedback detalhado
  const validateFormExplicitly = async (): Promise<boolean> => {
    const formData = getValues();
    console.log('=== Validando formulário explicitamente ===');
    console.log('Form data para validação:', formData);
    
    const validationResult = pedidoFormSchema.safeParse(formData);
    
    if (!validationResult.success) {
      console.error('Validação Zod falhou:', validationResult.error.flatten());
      console.error('Erros detalhados:', validationResult.error.errors);
      
      // Mostrar erros ao usuário via react-hook-form
      validationResult.error.errors.forEach(err => {
        const fieldPath = err.path.join('.') as FieldPath<PedidoFormData>;
        setError(fieldPath, {
          type: 'manual',
          message: err.message
        });
        console.error(`Erro no campo "${fieldPath}":`, err.message);
      });
      
      return false;
    }
    
    console.log('Validação passou com sucesso!');
    return true;
  };

  // Handler para prevenir submissão por Enter quando não estiver pronto
  const handleFormKeyDown = (e: React.KeyboardEvent<HTMLFormElement>) => {
    // Se estiver no último step e pressionar Enter, permitir apenas se isReadyToSubmit for true
    if (e.key === 'Enter') {
      if (activeStep !== STEPS.length - 1) {
        // Em steps anteriores, Enter não deve submeter
        e.preventDefault();
      } else if (!isReadyToSubmit) {
        // No último step, Enter só funciona se estiver pronto
        e.preventDefault();
      }
    }
  };

  // Status "Pago" exige forma de pagamento — bloqueia "Salvar e Concluir".
  const pagamentoInvalido = watch('status_pagamento') === 'Pago' && !watch('pagamento');

  // Componente do step atual
  const CurrentStepComponent = STEPS[activeStep].component;

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <FormProvider {...methods}>
      <Box 
        component="form" 
        onSubmit={handleSubmit(onFormSubmit as any)} // eslint-disable-line @typescript-eslint/no-explicit-any
        onKeyDown={handleFormKeyDown}
        sx={{
          maxWidth: 960,
          mx: 'auto',
          // Evita zoom automático no iOS: inputs com pelo menos 16px no mobile.
          '& .MuiInputBase-input': { fontSize: { xs: 16, md: 'inherit' } },
        }}
      >
        {/* Stepper - Desktop */}
        {!isMobile && (
          <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
            {STEPS.map((step, index) => (
              <Step
                key={step.label}
                completed={index < activeStep}
                sx={{ cursor: index <= activeStep ? 'pointer' : 'default' }}
                onClick={() => handleStepClick(index)}
              >
                <StepLabel error={stepErrors[index]}>
                  {step.label}
                </StepLabel>
              </Step>
            ))}
          </Stepper>
        )}

        {/* Stepper - Mobile */}
        {isMobile && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Passo {activeStep + 1} de {STEPS.length}
            </Typography>
            <Typography variant="h6" fontWeight="bold">
              {STEPS[activeStep].label}
            </Typography>
          </Box>
        )}

        {/* Conteúdo do Step */}
        <Paper sx={{ p: { xs: 2, sm: 2.5 }, mb: 3 }}>
          {submitError && (
            <Alert severity="error" sx={{ mb: 3 }} onClose={onClearError}>
              {submitError}
            </Alert>
          )}

          <CurrentStepComponent />
        </Paper>

        {/* Navegação - Desktop */}
        {!isMobile && (
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2 }}>
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <Button
                type="button"
                variant="text"
                color="secondary"
                onClick={handleResetForm}
                disabled={isSubmitting}
              >
                Limpar/Reiniciar
              </Button>
              <Button
                type="button"
                variant="outlined"
                onClick={handleBack}
                disabled={activeStep === 0}
                startIcon={<ArrowBackIcon />}
              >
                Voltar
              </Button>
            </Box>

            {activeStep === STEPS.length - 1 ? (
              <Box sx={{ display: 'flex', gap: 1.5 }}>
                <Button
                  type="button"
                  variant="outlined"
                  color="primary"
                  onClick={handleSaveDraft}
                  disabled={isSubmitting}
                  startIcon={<SaveIcon />}
                >
                  Salvar Rascunho
                </Button>
                <Tooltip
                  title={
                    isSubmitting
                      ? 'Salvando pedido...'
                      : pagamentoInvalido
                        ? 'Defina a forma de pagamento para concluir'
                        : !isReadyToSubmit
                          ? 'Navegue até o último passo para salvar'
                          : 'Clique para salvar o pedido'
                  }
                  arrow
                >
                  <span>
                    <Button
                      type="submit"
                      variant="contained"
                      color="primary"
                      disabled={isSubmitting || !isReadyToSubmit || pagamentoInvalido}
                      onClick={() => console.log('Botão Salvar clicado! isReadyToSubmit:', isReadyToSubmit)}
                      startIcon={
                        isSubmitting ? (
                          <CircularProgress size={20} color="inherit" />
                        ) : (
                          <SaveIcon />
                        )
                      }
                    >
                      {isSubmitting ? 'Salvando...' : 'Salvar e Concluir'}
                    </Button>
                  </span>
                </Tooltip>
              </Box>
            ) : (
              <Button
                type="button"
                variant="contained"
                onClick={handleNext}
                endIcon={<ArrowForwardIcon />}
              >
                Próximo
              </Button>
            )}
          </Box>
        )}

        {/* Navegação - Mobile (MobileStepper) */}
        {isMobile && (
          <MobileStepper
            variant="dots"
            steps={STEPS.length}
            position="static"
            activeStep={activeStep}
            sx={{
              position: 'sticky',
              bottom: 0,
              zIndex: 5,
              bgcolor: 'background.paper',
              borderRadius: 1,
              boxShadow: 3,
              py: 1,
              '& .MuiMobileStepper-dots': { flex: 0 },
            }}
            nextButton={
              activeStep === STEPS.length - 1 ? (
                <Tooltip
                  title={
                    isSubmitting
                      ? 'Salvando...'
                      : pagamentoInvalido
                        ? 'Defina a forma de pagamento'
                        : !isReadyToSubmit
                          ? 'Navegue até o último passo'
                          : 'Salvar pedido'
                  }
                  arrow
                >
                  <span>
                    <Button
                      type="submit"
                      size="small"
                      variant="contained"
                      sx={{ flex: 1 }}
                      disabled={isSubmitting || !isReadyToSubmit || pagamentoInvalido}
                      onClick={() => console.log('Botão Concluir clicado! isReadyToSubmit:', isReadyToSubmit)}
                      startIcon={
                        isSubmitting ? (
                          <CircularProgress size={16} color="inherit" />
                        ) : null
                      }
                    >
                      {isSubmitting ? '...' : 'Concluir'}
                    </Button>
                  </span>
                </Tooltip>
              ) : (
                <Button type="button" size="small" variant="contained" sx={{ flex: 1 }} onClick={handleNext}>
                  Próximo
                  <KeyboardArrowRight />
                </Button>
              )
            }
            backButton={
              <Button
                type="button"
                size="small"
                onClick={handleBack}
                disabled={activeStep === 0}
              >
                <KeyboardArrowLeft />
                Voltar
              </Button>
            }
          />
        )}

        {isMobile && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <Button
              type="button"
              size="small"
              color="secondary"
              onClick={handleResetForm}
              disabled={isSubmitting}
            >
              Limpar/Reiniciar
            </Button>
          </Box>
        )}

        {/* Indicador de rascunho salvo */}
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', mt: 2, textAlign: 'center' }}
        >
          💾 Rascunho salvo automaticamente
        </Typography>
      </Box>
    </FormProvider>
  );
}

export default CreateOrderWizard;

