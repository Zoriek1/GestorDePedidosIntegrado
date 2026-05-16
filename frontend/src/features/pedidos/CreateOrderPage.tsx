/**
 * Create Order Page
 * Página de criação de novo pedido com Wizard Inteligente de 4 etapas
 * Features: Autocomplete de cliente, CEP automático, seleção de horário
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Typography, Breadcrumbs, Link, Container, Paper, Box, Alert, Collapse, IconButton } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import AddShoppingCartIcon from '@mui/icons-material/AddShoppingCart';
import BoltIcon from '@mui/icons-material/Bolt';
import CloseIcon from '@mui/icons-material/Close';
import { CreateOrderWizard } from './CreateOrderWizard';
import { OrderFormProvider } from './contexts/OrderFormContext';
import { useCreatePedido, CreatePedidoPayload } from '../../api/endpoints/pedidos';
import { useToast } from '../../components/system/useToast';
import { SourceSelectionModal } from './components/SourceSelectionModal';
import type { PedidoFormData } from './schemas';

// Tipo para os dados passados via location.state (Quick Entry)
interface QuickEntryLocationState {
  prefillData?: Partial<PedidoFormData>;
  quickEntryWarnings?: string[];
  orderReset?: number;
}

const ORDER_DRAFT_STORAGE_KEY = 'puf_pedido_draft_v2';
const ORDER_STEP_STORAGE_KEY = 'puf_pedido_step_v2';

export default function CreateOrderPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { success, error: showError } = useToast();
  const createPedido = useCreatePedido();
  
  // Extrair dados de Quick Entry do location.state
  const locationState = location.state as QuickEntryLocationState | undefined;
  const prefillData = locationState?.prefillData;
  const quickEntryWarnings = locationState?.quickEntryWarnings || [];
  
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [fonteSelecionada, setFonteSelecionada] = useState<number | undefined>(() => {
    // Se tem prefillData com fonte, usar direto
    return prefillData?.fonte_pedido_id;
  });
  const [modalOpen, setModalOpen] = useState(() => {
    // Se tem prefillData, não abrir modal
    return !prefillData?.fonte_pedido_id;
  });
  const [wizardKey, setWizardKey] = useState<number>(() => Date.now());
  const [showQuickEntryWarnings, setShowQuickEntryWarnings] = useState(quickEntryWarnings.length > 0);
  const lastResetRef = useRef<number | null>(null);
  const prefillAppliedRef = useRef(false);

  const clearLocalDraft = useCallback(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(ORDER_DRAFT_STORAGE_KEY);
      window.localStorage.removeItem(ORDER_STEP_STORAGE_KEY);
    } catch {
      // ignorar falhas de limpeza
    }
  }, []);

  const resetFlow = useCallback(() => {
    clearLocalDraft();
    setSubmitError(null);
    setFonteSelecionada(undefined);
    setModalOpen(true);
    setWizardKey(Date.now());
    setShowQuickEntryWarnings(false);
  }, [clearLocalDraft]);

  // Efeito para processar prefillData na montagem (sem setState)
  useEffect(() => {
    if (prefillData && !prefillAppliedRef.current) {
      prefillAppliedRef.current = true;
      // Limpar draft anterior para não misturar dados do lead com rascunho antigo
      clearLocalDraft();
    }
  }, [prefillData, clearLocalDraft]);

  useEffect(() => {
    const resetToken = locationState?.orderReset;
    if (resetToken && resetToken !== lastResetRef.current) {
      lastResetRef.current = resetToken;
      // Se tem prefillData, não resetar o flow completo
      if (!prefillData) {
        setTimeout(() => {
          resetFlow();
        }, 0);
      }
    }
  }, [locationState?.orderReset, resetFlow, prefillData]);

  const handleSubmit = useCallback(async (data: Record<string, unknown>) => {
    setSubmitError(null);
    
    try {
      await createPedido.mutateAsync(data as unknown as CreatePedidoPayload);
      success('Pedido criado com sucesso!');
      navigate('/');
      return true;
    } catch (err) {
      // Verifica se foi salvo offline
      if (err instanceof Error && err.message === 'OFFLINE_ENQUEUED') {
        navigate('/');
        return true;
      }
      
      const errorMessage = err instanceof Error ? err.message : 'Erro ao criar pedido';
      setSubmitError(errorMessage);
      showError(errorMessage);
      return false;
    }
  }, [createPedido, navigate, success, showError]);

  const handleFonteConfirm = useCallback((fonteId: number) => {
    setFonteSelecionada(fonteId);
    setModalOpen(false);
  }, []);

  const initialData = useMemo(() => {
    if (prefillData) {
      // Merge prefillData (lead) com fonte selecionada no modal
      return {
        ...prefillData,
        ...(fonteSelecionada ? { fonte_pedido_id: fonteSelecionada } : {}),
      };
    }
    return fonteSelecionada ? { fonte_pedido_id: fonteSelecionada } : undefined;
  }, [fonteSelecionada, prefillData]);

  const handleClearError = useCallback(() => {
    setSubmitError(null);
  }, []);

  const handleReset = useCallback(() => {
    resetFlow();
  }, [resetFlow]);

  const wizardReady = !modalOpen && Boolean(fonteSelecionada);

  return (
    <OrderFormProvider key={wizardKey}>
      <SourceSelectionModal open={modalOpen} onConfirm={handleFonteConfirm} />
      <Container maxWidth={false} sx={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', py: { xs: 3, md: 6 } }}>
        <Paper
          elevation={4}
          sx={{
            width: '100%',
            maxWidth: 960,
            p: { xs: 2.5, md: 3.5 },
            borderRadius: 2,
            boxShadow: 6,
          }}
        >
          {/* Breadcrumbs */}
          <Breadcrumbs sx={{ mb: 2 }}>
            <Link
              href="/"
              underline="hover"
              color="inherit"
              sx={{ display: 'flex', alignItems: 'center' }}
              onClick={(e) => {
                e.preventDefault();
                navigate('/');
              }}
            >
              <HomeIcon sx={{ mr: 0.5 }} fontSize="small" />
              Início
            </Link>
            <Typography color="text.primary" sx={{ display: 'flex', alignItems: 'center' }}>
              <AddShoppingCartIcon sx={{ mr: 0.5 }} fontSize="small" />
              Novo Pedido
            </Typography>
          </Breadcrumbs>

          {/* Título */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
            <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 0 }}>
              Novo Pedido
            </Typography>
            {prefillData && (
              <BoltIcon color="warning" titleAccess="Entrada Rápida" />
            )}
          </Box>

          {/* Aviso de Quick Entry Warnings */}
          <Collapse in={showQuickEntryWarnings && quickEntryWarnings.length > 0}>
            <Alert 
              severity="warning" 
              sx={{ mb: 2 }}
              action={
                <IconButton
                  size="small"
                  onClick={() => setShowQuickEntryWarnings(false)}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              }
            >
              <Typography variant="body2" fontWeight="bold" sx={{ mb: 0.5 }}>
                Alguns campos não foram preenchidos automaticamente:
              </Typography>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {quickEntryWarnings.map((warn, idx) => (
                  <li key={idx}>
                    <Typography variant="caption">{warn}</Typography>
                  </li>
                ))}
              </ul>
            </Alert>
          </Collapse>

          {/* Wizard Inteligente */}
          {wizardReady ? (
            <CreateOrderWizard
              key={wizardKey}
              onSubmit={handleSubmit}
              isSubmitting={createPedido.isPending}
              submitError={submitError}
              onClearError={handleClearError}
              initialData={initialData}
              onReset={handleReset}
            />
          ) : (
            <Box
              sx={{
                p: 3,
                border: '1px dashed',
                borderColor: 'grey.300',
                borderRadius: 2,
                bgcolor: 'grey.50',
              }}
            >
              <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
                Selecione a fonte do pedido para começar
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Escolha a fonte no modal “Selecione a Fonte do Pedido”. O formulário carregará limpo após sua escolha.
              </Typography>
            </Box>
          )}
        </Paper>
      </Container>
    </OrderFormProvider>
  );
}
