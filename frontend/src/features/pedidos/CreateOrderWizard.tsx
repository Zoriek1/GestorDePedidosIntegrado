/**
 * CreateOrderWizard - Wizard de Criação de Pedidos "Inteligente"
 * Container principal com Stepper responsivo e persistência localStorage
 * Integra todos os steps com validação incremental
 */

import { useState, useEffect, useCallback } from 'react';
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

// ============================================================================
// Constantes
// ============================================================================

const STORAGE_KEY = 'puf_pedido_draft_v2';
const DEBOUNCE_DELAY = 500;

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
}: CreateOrderWizardProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { activeStep, setActiveStep, reset: resetOrderFormContext } = useOrderFormContext();
  const [stepErrors, setStepErrors] = useState<Record<number, boolean>>({});
  const [isReadyToSubmit, setIsReadyToSubmit] = useState(false);

  // Carrega dados do localStorage
  const loadDraft = useCallback((): PedidoFormData => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Importante: `initialData` deve ganhar do rascunho (ex: fonte escolhida no modal)
        return { ...pedidoFormDefaultValues, ...parsed, ...initialData };
      }
    } catch {
      // Erro ao carregar rascunho (silenciado em produção)
    }
    return { ...pedidoFormDefaultValues, ...initialData };
  }, [initialData]);

  // Hook Form com Zod
  const methods = useForm<PedidoFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(pedidoFormSchema) as any,
    defaultValues: loadDraft(),
    mode: 'onBlur',
  });

  const { handleSubmit, watch, trigger, setError, getValues, formState } = methods;

  // Salva no localStorage com debounce
  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;
    
    // eslint-disable-next-line react-hooks/incompatible-library
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
  }, [watch]);

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

  const handleStepClick = async (step: number) => {
    // Só permite ir para frente se os steps anteriores são válidos
    if (step > activeStep) {
      for (let i = activeStep; i < step; i++) {
        const isValid = await validateStep(i);
        if (!isValid) {
          setActiveStep(i);
          return;
        }
      }
    }
    setActiveStep(step);
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
        sx={{ maxWidth: 960, mx: 'auto' }}
      >
        {/* Stepper - Desktop */}
        {!isMobile && (
          <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
            {STEPS.map((step, index) => (
              <Step
                key={step.label}
                completed={index < activeStep}
                sx={{ cursor: 'pointer' }}
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
                      disabled={isSubmitting || !isReadyToSubmit}
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
              bgcolor: 'background.paper',
              borderRadius: 1,
              boxShadow: 1,
            }}
            nextButton={
              activeStep === STEPS.length - 1 ? (
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    type="button"
                    size="small"
                    variant="outlined"
                    onClick={handleSaveDraft}
                    disabled={isSubmitting}
                  >
                    Rascunho
                  </Button>
                  <Tooltip
                    title={
                      isSubmitting 
                        ? 'Salvando...' 
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
                        disabled={isSubmitting || !isReadyToSubmit}
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
                </Box>
              ) : (
                <Button type="button" size="small" onClick={handleNext}>
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

