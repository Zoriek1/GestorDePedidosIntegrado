/**
 * Tela simplificada de "Recebíveis Hoje" para entregadores.
 *
 * Entregador recebe diariamente por entrega — não precisa do extrato semanal,
 * períodos de pagamento, calendário ou competências do vendedor.
 */
import { useMemo } from 'react';
import {
  Box,
  Typography,
  Stack,
  Paper,
  Button,
  Chip,
  Divider,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import PaidIcon from '@mui/icons-material/Paid';
import HistoryIcon from '@mui/icons-material/History';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import dayjs from 'dayjs';
import { useAuth } from '../auth/authStore';
import { useLedgerEntries, useSettleUser } from './services/ledgerApi';
import type { LedgerEntry } from './services/ledgerApi';
import { useConfirm } from '../../components/system/useConfirm';
import { useToast } from '../../components/system/useToast';
import { formatCurrency } from '../pedidos/schemas';

function formatDayLabel(dateStr: string): string {
  const d = dayjs(dateStr);
  const today = dayjs().startOf('day');
  if (d.isSame(today, 'day')) return 'Hoje';
  if (d.isSame(today.subtract(1, 'day'), 'day')) return 'Ontem';
  return d.format('DD/MM/YYYY');
}

function entryDate(entry: LedgerEntry): string {
  return entry.due_date || entry.created_at?.slice(0, 10) || '';
}

export function EntregadorTodayView() {
  const { getUser } = useAuth();
  const user = getUser();
  const userId = user?.id;
  const confirm = useConfirm();
  const { success, error: showError } = useToast();

  const entriesQuery = useLedgerEntries(userId ? { user_id: userId } : {});
  const settleMutation = useSettleUser();

  const allEntries = useMemo(() => entriesQuery.data ?? [], [entriesQuery.data]);

  // Pendentes: CREDITs ativos de taxa_entrega (a receber)
  const pendentes = useMemo(
    () =>
      allEntries
        .filter(
          (e) =>
            e.type === 'CREDIT' &&
            e.category === 'taxa_entrega' &&
            e.status === 'active' &&
            !e.voided,
        )
        .sort((a, b) => entryDate(b).localeCompare(entryDate(a))),
    [allEntries],
  );

  // Histórico: últimas 7 quitações (DEBITs de pagamento)
  const historico = useMemo(
    () =>
      allEntries
        .filter((e) => e.type === 'DEBIT' && e.category === 'pagamento' && !e.voided)
        .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
        .slice(0, 7),
    [allEntries],
  );

  const total = pendentes.reduce((acc, e) => acc + Number(e.amount || 0), 0);

  // Agrupar pendentes por dia
  const grupos = useMemo(() => {
    const m = new Map<string, LedgerEntry[]>();
    for (const e of pendentes) {
      const k = entryDate(e);
      const arr = m.get(k) ?? [];
      arr.push(e);
      m.set(k, arr);
    }
    return Array.from(m.entries()).sort((a, b) => b[0].localeCompare(a[0]));
  }, [pendentes]);

  const handleReceberTudo = async () => {
    if (!userId || pendentes.length === 0) return;
    const ok = await confirm({
      title: 'Marcar tudo como recebido',
      description: `Confirmar recebimento de ${pendentes.length} entrega(s) — total ${formatCurrency(total)}? Esta ação não pode ser desfeita.`,
      confirmText: 'Recebi tudo',
      confirmColor: 'success',
    });
    if (!ok) return;
    try {
      const res = await settleMutation.mutateAsync({
        user_id: userId,
        entry_ids: pendentes.map((e) => e.id),
      });
      success(`${res.settled} entrega(s) quitada(s) — ${formatCurrency(res.amount)}`);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao registrar recebimento');
    }
  };

  if (!userId) {
    return (
      <Box sx={{ maxWidth: 600, mx: 'auto', p: 3 }}>
        <Alert severity="warning">Não foi possível identificar o usuário.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto', p: { xs: 2, sm: 3 } }}>
      <Stack direction="row" alignItems="center" spacing={1} mb={2}>
        <LocalShippingIcon color="primary" fontSize="large" />
        <Typography variant="h5" component="h1">
          Minhas entregas a receber
        </Typography>
      </Stack>

      <Paper
        elevation={0}
        sx={{
          p: 3,
          mb: 3,
          bgcolor: 'primary.main',
          color: 'primary.contrastText',
          borderRadius: 2,
        }}
      >
        <Typography variant="body2" sx={{ opacity: 0.9 }}>
          Total a receber
        </Typography>
        <Typography variant="h3" fontWeight="bold">
          {formatCurrency(total)}
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
          {pendentes.length} {pendentes.length === 1 ? 'entrega pendente' : 'entregas pendentes'}
        </Typography>
      </Paper>

      <Button
        variant="contained"
        color="success"
        size="large"
        fullWidth
        startIcon={<PaidIcon />}
        disabled={pendentes.length === 0 || settleMutation.isPending}
        onClick={handleReceberTudo}
        sx={{ mb: 3, py: 1.5, fontSize: '1.05rem' }}
      >
        {settleMutation.isPending ? 'Registrando…' : 'Recebi tudo'}
      </Button>

      {entriesQuery.isLoading && (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      )}

      {entriesQuery.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Erro ao carregar entregas: {(entriesQuery.error as Error).message}
        </Alert>
      )}

      {!entriesQuery.isLoading && pendentes.length === 0 && (
        <Paper variant="outlined" sx={{ p: 3, textAlign: 'center', mb: 3 }}>
          <Typography color="text.secondary">
            Nenhuma entrega pendente de pagamento.
          </Typography>
        </Paper>
      )}

      {grupos.map(([dia, lista]) => {
        const totalDia = lista.reduce((a, e) => a + Number(e.amount || 0), 0);
        return (
          <Paper key={dia} variant="outlined" sx={{ mb: 2, overflow: 'hidden' }}>
            <Box
              sx={{
                px: 2,
                py: 1.5,
                bgcolor: 'action.hover',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <Typography variant="subtitle2" fontWeight="bold">
                {formatDayLabel(dia)}
              </Typography>
              <Chip
                label={formatCurrency(totalDia)}
                size="small"
                color="primary"
                variant="outlined"
              />
            </Box>
            <Divider />
            <List disablePadding>
              {lista.map((e) => (
                <ListItem key={e.id} divider>
                  <ListItemText
                    primary={
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="body2">
                          {e.pedido_id ? `Pedido #${e.pedido_id}` : e.description || 'Entrega'}
                        </Typography>
                        <Typography variant="body2" fontWeight="bold">
                          {formatCurrency(Number(e.amount))}
                        </Typography>
                      </Stack>
                    }
                    secondary={e.description || undefined}
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        );
      })}

      {historico.length > 0 && (
        <Accordion sx={{ mt: 3 }} disableGutters elevation={0} variant="outlined">
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <HistoryIcon fontSize="small" />
              <Typography variant="subtitle2">
                Últimos recebimentos ({historico.length})
              </Typography>
            </Stack>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 0 }}>
            <List dense disablePadding>
              {historico.map((e) => (
                <ListItem key={e.id} divider>
                  <ListItemText
                    primary={
                      <Stack direction="row" justifyContent="space-between">
                        <Typography variant="body2">
                          {e.created_at ? dayjs(e.created_at).format('DD/MM/YYYY HH:mm') : '-'}
                        </Typography>
                        <Typography variant="body2" fontWeight="bold" color="success.main">
                          {formatCurrency(Number(e.amount))}
                        </Typography>
                      </Stack>
                    }
                    secondary={e.description || undefined}
                  />
                </ListItem>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  );
}

export default EntregadorTodayView;
