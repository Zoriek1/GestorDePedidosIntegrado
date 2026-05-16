/**
 * PedidoWizard - Wizard de Criação de Pedidos
 * Container principal com Stepper responsivo e persistência localStorage
 */

import { useState, useEffect, useCallback } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { createLogger } from '../../../../lib/logger';

const _log = createLogger('PedidoWizard');
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
} from '../../schemas';
import { Step1Cliente } from './Step1Cliente';
import { Step2Entrega } from './Step2Entrega';
import { Step3Produto } from './Step3Produto';
import { Step4Pagamento } from './Step4Pagamento';

// ============================================================================
// Constantes
// ============================================================================

const STORAGE_KEY = 'puf_pedido_draft';
const DEBOUNCE_DELAY = 500;

const STEPS = [
  { label: 'Cliente', component: Step1Cliente },
  { label: 'Entrega', component: Step2Entrega },
  { label: 'Produto', component: Step3Produto },
  { label: 'Pagamento', component: Step4Pagamento },
];

// ============================================================================
// Props Interface
// ============================================================================

interface PedidoWizardProps {
  /** Callback chamado ao submeter o formulário com sucesso */
  onSubmit: (data: Record<string, unknown>) => Promise<void>;
  /** Se true, exibe loading no botão de salvar */
  isSubmitting?: boolean;
  /** Mensagem de erro do backend */
  submitError?: string | null;
  /** Callback para limpar erro */
  onClearError?: () => void;
}

// ============================================================================
// Componente Principal
// ============================================================================

export function PedidoWizard({
  onSubmit,
  isSubmitting = false,
  submitError,
  onClearError,
}: PedidoWizardProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [activeStep, setActiveStep] = useState(0);
  const [stepErrors, setStepErrors] = useState<Record<number, boolean>>({});

  // Carrega dados do localStorage
  const loadDraft = useCallback((): PedidoFormData => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return { ...pedidoFormDefaultValues, ...parsed };
      }
    } catch {
      // Erro ao carregar rascunho (silenciado em produção)
    }
    return pedidoFormDefaultValues;
  }, []);

  // Hook Form com Zod
  const methods = useForm<PedidoFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(pedidoFormSchema) as any,
    defaultValues: loadDraft(),
    mode: 'onBlur',
  });

  const { handleSubmit, watch, trigger } = methods;

  // Salva no localStorage com debounce
  useEffect(() => {
    // eslint-disable-next-line react-hooks/incompatible-library
    const subscription = watch((data) => {
      const timeoutId = setTimeout(() => {
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } catch {
          // Erro ao salvar rascunho (silenciado em produção)
        }
      }, DEBOUNCE_DELAY);

      return () => clearTimeout(timeoutId);
    });

    return () => subscription.unsubscribe();
  }, [watch]);

  // Limpa erros ao mudar de step
  useEffect(() => {
    if (onClearError) {
      onClearError();
    }
  }, [activeStep, onClearError]);

  // Validação por step
  const validateStep = async (step: number): Promise<boolean> => {
    let isValid = false;

    switch (step) {
      case 0:
        isValid = await trigger(['cliente', 'telefone_cliente']);
        break;
      case 1:
        isValid = await trigger([
          'tipo_pedido',
          'destinatario',
          'dia_entrega',
          'horario',
          'rua',
          'numero',
          'cidade',
          'endereco',
        ]);
        break;
      case 2:
        isValid = await trigger(['produto', 'valor']);
        break;
      case 3:
        isValid = true; // Step 4 tem campos opcionais
        break;
      default:
        isValid = true;
    }

    setStepErrors((prev) => ({ ...prev, [step]: !isValid }));
    return isValid;
  };

  // Navegação
  const handleNext = async () => {
    const isValid = await validateStep(activeStep);
    if (isValid && activeStep < STEPS.length - 1) {
      setActiveStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep((prev) => prev - 1);
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

  // Submissão
  const onFormSubmit = async (data: PedidoFormData) => {
    try {
      const payload = transformFormToApiPayload(data);
      await onSubmit(payload);
      // Limpa o rascunho após sucesso
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      // Erro é tratado pelo componente pai
      console.error('Erro ao salvar pedido:', error);
    }
  };

  // Componente do step atual
  const CurrentStepComponent = STEPS[activeStep].component;

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <FormProvider {...methods}>
      <Box component="form" onSubmit={handleSubmit(onFormSubmit as any)}> {/* eslint-disable-line @typescript-eslint/no-explicit-any */}
        {/* Stepper - Desktop */}
        {!isMobile && (
          <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
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
        <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
          {submitError && (
            <Alert severity="error" sx={{ mb: 3 }} onClose={onClearError}>
              {submitError}
            </Alert>
          )}

          <CurrentStepComponent />
        </Paper>

        {/* Navegação - Desktop */}
        {!isMobile && (
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button
              variant="outlined"
              onClick={handleBack}
              disabled={activeStep === 0}
              startIcon={<ArrowBackIcon />}
            >
              Voltar
            </Button>

            {activeStep === STEPS.length - 1 ? (
              <Button
                type="submit"
                variant="contained"
                color="primary"
                disabled={isSubmitting}
                startIcon={
                  isSubmitting ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <SaveIcon />
                  )
                }
              >
                {isSubmitting ? 'Salvando...' : 'Salvar Pedido'}
              </Button>
            ) : (
              <Button
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
                <Button
                  type="submit"
                  size="small"
                  disabled={isSubmitting}
                  startIcon={
                    isSubmitting ? (
                      <CircularProgress size={16} color="inherit" />
                    ) : null
                  }
                >
                  {isSubmitting ? '...' : 'Salvar'}
                </Button>
              ) : (
                <Button size="small" onClick={handleNext}>
                  Próximo
                  <KeyboardArrowRight />
                </Button>
              )
            }
            backButton={
              <Button
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

export default PedidoWizard;

