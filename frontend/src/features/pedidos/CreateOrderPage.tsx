/**
 * Create Order Page
 * Página de criação de novo pedido com o Wizard redesenhado (estética de floricultura).
 * Mantém: seleção de fonte (modal), prefill de Entrada Rápida e persistência de rascunho.
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Leaf, Bolt, X } from 'lucide-react';
import { CreateOrderWizardNovo } from './wizardNovo/CreateOrderWizardNovo';
import { OrderFormProvider } from './contexts/OrderFormContext';
import { useCreatePedido, CreatePedidoPayload } from '../../api/endpoints/pedidos';
import { useToast } from '../../components/system/useToast';
import { useConfirm } from '../../components/system/useConfirm';
import { SourceSelectionModal } from './components/SourceSelectionModal';
import type { PedidoFormData } from './schemas';

/** Formata telefone BR para wa.me (prepende 55 quando tem 10/11 dígitos). */
function formatWhatsappPhone(raw: string): string {
  const digits = (raw || '').replace(/\D/g, '');
  if (digits.length === 10 || digits.length === 11) return `55${digits}`;
  return digits;
}

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
  const confirm = useConfirm();
  const createPedido = useCreatePedido();

  const locationState = location.state as QuickEntryLocationState | undefined;
  const prefillData = locationState?.prefillData;
  const quickEntryWarnings = locationState?.quickEntryWarnings || [];

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [fonteSelecionada, setFonteSelecionada] = useState<number | undefined>(() => prefillData?.fonte_pedido_id);
  const [modalOpen, setModalOpen] = useState(() => !prefillData?.fonte_pedido_id);
  const [wizardKey, setWizardKey] = useState<number>(() => Date.now());
  const [showQuickEntryWarnings, setShowQuickEntryWarnings] = useState(quickEntryWarnings.length > 0);
  const lastResetRef = useRef<number | null>(null);
  const prefillAppliedRef = useRef(false);

  const clearLocalDraft = useCallback(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(ORDER_DRAFT_STORAGE_KEY);
      window.localStorage.removeItem(ORDER_STEP_STORAGE_KEY);
    } catch { /* ignorar falhas de limpeza */ }
  }, []);

  const resetFlow = useCallback(() => {
    clearLocalDraft();
    setSubmitError(null);
    setFonteSelecionada(undefined);
    setModalOpen(true);
    setWizardKey(Date.now());
    setShowQuickEntryWarnings(false);
  }, [clearLocalDraft]);

  useEffect(() => {
    if (prefillData && !prefillAppliedRef.current) {
      prefillAppliedRef.current = true;
      clearLocalDraft();
    }
  }, [prefillData, clearLocalDraft]);

  useEffect(() => {
    const resetToken = locationState?.orderReset;
    if (resetToken && resetToken !== lastResetRef.current) {
      lastResetRef.current = resetToken;
      if (!prefillData) {
        setTimeout(() => { resetFlow(); }, 0);
      }
    }
  }, [locationState?.orderReset, resetFlow, prefillData]);

  const handleSubmit = useCallback(async (data: Record<string, unknown>) => {
    setSubmitError(null);
    try {
      const result = await createPedido.mutateAsync(data as unknown as CreatePedidoPayload);
      success('Pedido criado com sucesso!');

      const trackUrl = result?.track_url;
      const telefone = formatWhatsappPhone(String((data as Record<string, unknown>).telefone_cliente || ''));
      if (trackUrl && telefone) {
        const enviar = await confirm({
          title: 'Enviar acompanhamento?',
          description: 'Deseja enviar ao cliente, pelo WhatsApp, o link para acompanhar o status do pedido?',
          confirmText: 'Enviar no WhatsApp', cancelText: 'Agora não', confirmColor: 'success',
        });
        if (enviar) {
          const mensagem =
            `Olá! Seu pedido na Plante uma Flor foi confirmado.\n` +
            `Acompanhe o status da sua entrega por aqui: ${trackUrl}`;
          window.open(`https://wa.me/${telefone}?text=${encodeURIComponent(mensagem)}`, '_blank');
        }
      }

      navigate('/');
      return true;
    } catch (err) {
      if (err instanceof Error && err.message === 'OFFLINE_ENQUEUED') {
        navigate('/');
        return true;
      }
      const errorMessage = err instanceof Error ? err.message : 'Erro ao criar pedido';
      setSubmitError(errorMessage);
      showError(errorMessage);
      return false;
    }
  }, [createPedido, navigate, success, showError, confirm]);

  const handleFonteConfirm = useCallback((fonteId: number) => {
    setFonteSelecionada(fonteId);
    setModalOpen(false);
  }, []);

  const initialData = useMemo(() => {
    if (prefillData) {
      return { ...prefillData, ...(fonteSelecionada ? { fonte_pedido_id: fonteSelecionada } : {}) };
    }
    return fonteSelecionada ? { fonte_pedido_id: fonteSelecionada } : undefined;
  }, [fonteSelecionada, prefillData]);

  const handleClearError = useCallback(() => setSubmitError(null), []);
  const handleReset = useCallback(() => resetFlow(), [resetFlow]);

  const wizardReady = !modalOpen && Boolean(fonteSelecionada);

  return (
    <OrderFormProvider key={wizardKey}>
      <SourceSelectionModal open={modalOpen} onConfirm={handleFonteConfirm} />
      <div className="pw-root">
        <main className="pw-shell">
          <div className="pw-hero">
            <div className="pw-crumb">
              <a href="/" onClick={(e) => { e.preventDefault(); navigate('/'); }}>Início</a>
              <span>/</span> Novo Pedido
            </div>
            <p className="pw-eyebrow">
              <Leaf size={12} /> {prefillData ? 'Entrada rápida' : 'Novo pedido'}
              {prefillData && <Bolt size={12} />}
            </p>
            <h1 className="pw-title">Novo <em>Pedido</em></h1>
          </div>

          {showQuickEntryWarnings && quickEntryWarnings.length > 0 && (
            <div className="pw-warn" style={{ alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <strong>Alguns campos não foram preenchidos automaticamente:</strong>
                <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
                  {quickEntryWarnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
              <button type="button" className="pw-link-inline" onClick={() => setShowQuickEntryWarnings(false)}>
                <X size={14} />
              </button>
            </div>
          )}

          {wizardReady ? (
            <CreateOrderWizardNovo
              key={wizardKey}
              onSubmit={handleSubmit}
              isSubmitting={createPedido.isPending}
              submitError={submitError}
              onClearError={handleClearError}
              initialData={initialData}
              onReset={handleReset}
            />
          ) : (
            <div className="pw-card">
              <h2 style={{ fontFamily: 'var(--serif)', margin: '0 0 6px' }}>Selecione a fonte do pedido para começar</h2>
              <p style={{ color: 'var(--muted)', margin: 0, fontSize: 13 }}>
                Escolha a fonte no modal “Selecione a Fonte do Pedido”. O formulário carregará limpo após sua escolha.
              </p>
            </div>
          )}
        </main>
      </div>
    </OrderFormProvider>
  );
}
