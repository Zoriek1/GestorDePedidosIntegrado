import { useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import { ExternalLink, FileJson, ListChecks, RefreshCw, RotateCcw, Send } from 'lucide-react';
import {
  useBlingOutboxLogs,
  useBlingPreviewPedido,
  useRetryBlingOutbox,
  useSendBlingPedido,
} from '../../../api/endpoints/bling';
import type { BlingOutbox } from '../../../api/endpoints/bling';
import { useToast } from '../../../components/system/useToast';
import { formatBRL } from '../../../lib/format/currency';

const STEP_LABELS: Record<string, string> = {
  pending: 'Pendente',
  validating_mapping: 'Validando',
  building_payload: 'Montando payload',
  checking_duplicate: 'Checando duplicidade',
  creating_order: 'Criando pedido',
  launching_order_accounts: 'Lancando contas',
  finding_receivables: 'Localizando contas',
  settling_entry: 'Baixando entrada',
  completed: 'Concluido',
  failed_retryable: 'Erro recuperavel',
  failed_final: 'Erro final',
  cancelled: 'Cancelado',
};

function outboxLabel(outbox?: BlingOutbox | null, hasRef = false) {
  if (!outbox) return hasRef ? 'Pedido criado' : 'Nao enviado';
  if (outbox.status === 'completed') return 'Concluido';
  if (outbox.status === 'cancelled') return 'Cancelado';
  if (outbox.status?.startsWith('failed')) return 'Erro';
  if (outbox.status === 'processing') return STEP_LABELS[outbox.step] || 'Processando';
  return STEP_LABELS[outbox.status] || 'Pendente';
}

function outboxColor(outbox?: BlingOutbox | null): 'default' | 'info' | 'success' | 'warning' | 'error' {
  if (!outbox) return 'default';
  if (outbox.status === 'completed') return 'success';
  if (outbox.status?.startsWith('failed')) return 'error';
  if (outbox.status === 'cancelled') return 'warning';
  return 'info';
}

function JsonDialog({
  open,
  title,
  value,
  onClose,
}: {
  open: boolean;
  title: string;
  value: unknown;
  onClose: () => void;
}) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent dividers>
        <Box
          component="pre"
          sx={{
            m: 0,
            p: 2,
            bgcolor: 'grey.100',
            borderRadius: 1,
            maxHeight: 520,
            overflow: 'auto',
            fontSize: 12,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {JSON.stringify(value ?? {}, null, 2)}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fechar</Button>
      </DialogActions>
    </Dialog>
  );
}

export function BlingIntegrationCard({ pedidoId }: { pedidoId: number }) {
  const [payloadOpen, setPayloadOpen] = useState(false);
  const [logsOpen, setLogsOpen] = useState(false);
  const { success, error: showError } = useToast();

  const previewQuery = useBlingPreviewPedido(pedidoId);
  const sendMutation = useSendBlingPedido();
  const retryMutation = useRetryBlingOutbox();

  const preview = previewQuery.data;
  const outbox = preview?.outbox ?? null;
  const outboxId = outbox?.id ?? null;
  const logsQuery = useBlingOutboxLogs(logsOpen ? outboxId : null);
  const hasExternalRef = Boolean(preview?.external_ref);
  const statusText = outboxLabel(outbox, hasExternalRef);
  const canSend =
    Boolean(preview?.valid) &&
    !outbox?.status?.startsWith('failed') &&
    outbox?.status !== 'completed' &&
    outbox?.status !== 'processing';
  const canRetry = Boolean(outbox?.id && outbox.status?.startsWith('failed'));
  const orderId = outbox?.bling_order_id || preview?.external_ref?.external_order_id;
  const orderNumber = outbox?.bling_order_number || preview?.external_ref?.external_order_number;

  const latestError = outbox?.error_message || previewQuery.error?.message;
  const plan = preview?.financial_plan ?? [];
  const planTotal = useMemo(
    () => plan.reduce((acc, row) => acc + (Number(row.amount) || 0), 0),
    [plan],
  );

  const handleSend = async () => {
    try {
      await sendMutation.mutateAsync(pedidoId);
      success('Pedido enviado para o Bling');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao enviar para o Bling');
    }
  };

  const handleRetry = async () => {
    if (!outbox?.id) return;
    try {
      await retryMutation.mutateAsync(outbox.id);
      success('Retentativa enviada');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao tentar novamente');
    }
  };

  const handleOpenBling = () => {
    window.open('https://www.bling.com.br/vendas.php', '_blank', 'noopener,noreferrer');
  };

  const busy = previewQuery.isLoading || sendMutation.isPending || retryMutation.isPending;

  return (
    <Paper sx={{ p: 2.5, mb: 2 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={2}>
        <Stack spacing={0.75}>
          <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 1.2, fontWeight: 700 }}>
            Integracao Bling
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Chip label={statusText} color={outboxColor(outbox)} size="small" sx={{ fontWeight: 700 }} />
            {outbox?.step && <Chip label={STEP_LABELS[outbox.step] || outbox.step} variant="outlined" size="small" />}
            {orderNumber && <Chip label={`Bling #${orderNumber}`} variant="outlined" size="small" />}
            {busy && <CircularProgress size={18} />}
          </Stack>
        </Stack>

        <Stack direction="row" spacing={1} flexWrap="wrap" justifyContent={{ xs: 'flex-start', sm: 'flex-end' }}>
          <Button
            size="small"
            variant="outlined"
            startIcon={<FileJson size={16} />}
            onClick={() => setPayloadOpen(true)}
            disabled={!preview?.payload}
          >
            Ver payload
          </Button>
          <Button
            size="small"
            variant="contained"
            startIcon={<Send size={16} />}
            onClick={handleSend}
            disabled={!canSend || busy}
          >
            Enviar
          </Button>
          <Button
            size="small"
            variant="outlined"
            startIcon={<RotateCcw size={16} />}
            onClick={handleRetry}
            disabled={!canRetry || busy}
          >
            Tentar novamente
          </Button>
          <Button
            size="small"
            variant="outlined"
            startIcon={<ListChecks size={16} />}
            onClick={() => setLogsOpen(true)}
            disabled={!outboxId}
          >
            Logs
          </Button>
          <Button
            size="small"
            variant="outlined"
            startIcon={<ExternalLink size={16} />}
            onClick={handleOpenBling}
            disabled={!orderId}
          >
            Abrir no Bling
          </Button>
        </Stack>
      </Stack>

      {(preview?.warnings?.length || preview?.errors?.length || latestError) && (
        <Stack spacing={1} sx={{ mt: 2 }}>
          {preview?.warnings?.map((warning) => (
            <Alert key={warning} severity="warning">
              {warning}
            </Alert>
          ))}
          {preview?.errors?.map((err) => (
            <Alert key={err.message} severity="error">
              {err.message}
            </Alert>
          ))}
          {latestError && (
            <Alert
              severity={outbox?.status === 'failed_retryable' ? 'warning' : 'error'}
              action={
                <Button color="inherit" size="small" startIcon={<RefreshCw size={14} />} onClick={() => previewQuery.refetch()}>
                  Recarregar
                </Button>
              }
            >
              {latestError}
            </Alert>
          )}
        </Stack>
      )}

      {plan.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Divider sx={{ mb: 1.5 }} />
          <Stack spacing={1}>
            {plan.map((row) => (
              <Stack
                key={row.marker}
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1}
                justifyContent="space-between"
              >
                <Typography variant="body2" fontWeight={600}>
                  {row.kind} - {formatBRL(row.amount)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  vence {row.due_date} {row.should_settle ? '| baixa imediata' : '| aberto'}
                </Typography>
              </Stack>
            ))}
            <Typography variant="caption" color="text.secondary">
              Total no plano financeiro: {formatBRL(planTotal)}
            </Typography>
          </Stack>
        </Box>
      )}

      <JsonDialog
        open={payloadOpen}
        title="Payload Bling"
        value={preview?.payload}
        onClose={() => setPayloadOpen(false)}
      />

      <Dialog open={logsOpen} onClose={() => setLogsOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Logs Bling</DialogTitle>
        <DialogContent dividers>
          {logsQuery.isLoading ? (
            <Stack direction="row" spacing={1} alignItems="center">
              <CircularProgress size={18} />
              <Typography variant="body2">Carregando logs...</Typography>
            </Stack>
          ) : (
            <Stack spacing={1.5}>
              {(logsQuery.data?.logs ?? []).map((log) => (
                <Box key={log.id} sx={{ p: 1.5, bgcolor: 'grey.100', borderRadius: 1 }}>
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                    <Chip label={log.level} size="small" />
                    {log.step && <Chip label={STEP_LABELS[log.step] || log.step} size="small" variant="outlined" />}
                    {log.status_code && <Chip label={log.status_code} size="small" variant="outlined" />}
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {log.message}
                  </Typography>
                  {(log.request || log.response || log.error_code) && (
                    <Box
                      component="pre"
                      sx={{ mt: 1, mb: 0, fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                    >
                      {JSON.stringify(
                        { error_code: log.error_code, request: log.request, response: log.response },
                        null,
                        2,
                      )}
                    </Box>
                  )}
                </Box>
              ))}
              {!logsQuery.data?.logs?.length && (
                <Typography variant="body2" color="text.secondary">
                  Nenhum log registrado para esta tentativa.
                </Typography>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => logsQuery.refetch()} startIcon={<RefreshCw size={16} />} disabled={!outboxId}>
            Recarregar
          </Button>
          <Button onClick={() => setLogsOpen(false)}>Fechar</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}

export default BlingIntegrationCard;
