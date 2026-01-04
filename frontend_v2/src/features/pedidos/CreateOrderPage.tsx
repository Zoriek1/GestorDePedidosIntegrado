/**
 * Create Order Page
 * Página de criação de novo pedido com Wizard Inteligente de 4 etapas
 * Features: Autocomplete de cliente, CEP automático, seleção de horário
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Typography, Breadcrumbs, Link, Container, Paper, Box } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import AddShoppingCartIcon from '@mui/icons-material/AddShoppingCart';
import { CreateOrderWizard } from './CreateOrderWizard';
import { OrderFormProvider } from './contexts/OrderFormContext';
import { useCreatePedido, CreatePedidoPayload } from '../../api/endpoints/pedidos';
import { useToast } from '../../components/system/useToast';
import { SourceSelectionModal } from './components/SourceSelectionModal';

const ORDER_DRAFT_STORAGE_KEY = 'puf_pedido_draft_v2';
const ORDER_STEP_STORAGE_KEY = 'puf_pedido_step_v2';

export default function CreateOrderPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { success, error: showError } = useToast();
  const createPedido = useCreatePedido();
  
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [fonteSelecionada, setFonteSelecionada] = useState<number | undefined>(undefined);
  const [modalOpen, setModalOpen] = useState(true);
  const [wizardKey, setWizardKey] = useState<number>(() => Date.now());
  const lastResetRef = useRef<number | null>(null);

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
  }, [clearLocalDraft]);

  useEffect(() => {
    const resetToken = (location.state as { orderReset?: number } | undefined)?.orderReset;
    if (resetToken && resetToken !== lastResetRef.current) {
      lastResetRef.current = resetToken;
      resetFlow();
    }
  }, [location.state, resetFlow]);

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
    return fonteSelecionada ? { fonte_pedido_id: fonteSelecionada } : undefined;
  }, [fonteSelecionada]);

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
          <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
            Novo Pedido
          </Typography>

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
