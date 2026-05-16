import { useState } from 'react';
import {
  Box,
  Typography,
  Divider,
  List,
  ListItem,
  ListItemText,
  Chip,
  Skeleton,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Snackbar,
  Alert,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { formatBRL } from '../../../lib/format/currency';
import { LedgerEntry, useDeleteSalaryEntry } from '../services/ledgerApi';

interface EntryListProps {
  entries: LedgerEntry[];
  loading?: boolean;
  /** Quando true, exibe a lixeira ao lado de salários não-liquidados (admin only). */
  canDeleteSalary?: boolean;
}

const SALARY_CATEGORIES = new Set(['fixo_semanal', 'almoco', 'transporte']);

function groupByWeek(entries: LedgerEntry[]): Map<string, LedgerEntry[]> {
  const map = new Map<string, LedgerEntry[]>();
  for (const e of entries) {
    const key = e.week_ref;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(e);
  }
  return map;
}

function weekLabel(weekRef: string): string {
  if (!weekRef) return '';
  const d = new Date(weekRef + 'T00:00:00');
  const end = new Date(d);
  end.setDate(d.getDate() + 6);
  const fmt = (dt: Date) =>
    dt.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  return `Semana ${fmt(d)} – ${fmt(end)}`;
}

const CATEGORY_LABELS: Record<string, string> = {
  fixo_semanal: 'Salário Semanal',
  fixo_mensal: 'Salário Mensal',
  almoco: 'Vale Almoço',
  transporte: 'Vale Transporte',
  comissao_whatsapp: 'Comissão WhatsApp',
  comissao_site: 'Comissão Site',
  comissao_balcao: 'Comissão Balcão',
  comissao_indicacao: 'Comissão Indicação',
  comissao_lucro: 'Comissão Lucro',
  custom_credit: 'Crédito Avulso',
  pagamento: 'Pagamento',
  adiantamento: 'Adiantamento',
  ajuste_debito: 'Ajuste Débito',
};

function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

function getCreditStatus(entry: LedgerEntry): {
  label: string;
  color: 'success' | 'warning' | 'error' | 'default';
} {
  if (entry.status === 'settled') {
    return { label: 'Quitado', color: 'success' };
  }
  if (!entry.due_date) {
    return { label: 'A receber', color: 'warning' };
  }

  const due = new Date(entry.due_date + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  if (due.getTime() < today.getTime()) {
    return { label: 'Atrasado', color: 'error' };
  }
  if (due.getTime() === today.getTime()) {
    return { label: 'Hoje', color: 'warning' };
  }
  return { label: 'A receber', color: 'default' };
}

function settledInfo(entry: LedgerEntry): string | null {
  if (entry.status !== 'settled' || entry.type !== 'CREDIT') return null;
  const parts: string[] = [];
  if (entry.settled_at) {
    const d = new Date(entry.settled_at);
    parts.push(`Quitado em ${d.toLocaleDateString('pt-BR')}`);
  }
  if (entry.settled_by_id) {
    parts.push(`ref. pagamento #${entry.settled_by_id}`);
  }
  return parts.length ? parts.join(' · ') : null;
}

export function EntryList({ entries, loading, canDeleteSalary = false }: EntryListProps) {
  const [confirmEntry, setConfirmEntry] = useState<LedgerEntry | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const deleteMutation = useDeleteSalaryEntry();

  const isDeletable = (entry: LedgerEntry) =>
    canDeleteSalary &&
    entry.type === 'CREDIT' &&
    SALARY_CATEGORIES.has(entry.category) &&
    entry.status !== 'settled' &&
    !entry.voided;

  const onConfirmDelete = async () => {
    if (!confirmEntry) return;
    try {
      await deleteMutation.mutateAsync(confirmEntry.id);
      setConfirmEntry(null);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Erro ao apagar');
      setConfirmEntry(null);
    }
  };

  if (loading) {
    return (
      <Box>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} variant="rectangular" height={48} sx={{ mb: 1, borderRadius: 1 }} />
        ))}
      </Box>
    );
  }

  if (!entries.length) {
    return (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
        Nenhum lançamento encontrado.
      </Typography>
    );
  }

  const grouped = groupByWeek(entries);

  return (
    <Box>
      {Array.from(grouped.entries()).map(([week, weekEntries]) => {
        const weekTotal = weekEntries.reduce(
          (acc, e) => acc + (e.type === 'CREDIT' ? e.amount : -e.amount),
          0
        );

        return (
          <Box key={week} mb={2}>
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              sx={{ py: 1, px: 0.5 }}
            >
              <Typography variant="subtitle2" color="text.secondary">
                {weekLabel(week)}
              </Typography>
              <Typography
                variant="subtitle2"
                fontWeight={600}
                color={weekTotal >= 0 ? 'success.main' : 'error.main'}
              >
                {weekTotal >= 0 ? '+' : ''}{formatBRL(weekTotal)}
              </Typography>
            </Box>
            <Divider />
            <List dense disablePadding>
              {weekEntries.map((entry) => {
                const creditStatus = getCreditStatus(entry);
                const settled = settledInfo(entry);

                return (
                  <ListItem key={entry.id} disableGutters sx={{ px: 0.5 }}>
                    <ListItemText
                      primary={
                        <Box display="flex" justifyContent="space-between" alignItems="center" gap={1}>
                          <Box display="flex" alignItems="center" gap={0.5} flexWrap="wrap">
                            <Typography variant="body2">
                              {categoryLabel(entry.category)}
                              {entry.pedido_id && (
                                <Typography
                                  component="span"
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{ ml: 0.5 }}
                                >
                                  #{entry.pedido_id}
                                </Typography>
                              )}
                            </Typography>
                            {entry.type === 'CREDIT' && (
                              <Chip
                                size="small"
                                label={creditStatus.label}
                                color={creditStatus.color}
                                variant="filled"
                                sx={{ height: 18, fontSize: '0.65rem' }}
                              />
                            )}
                          </Box>
                          <Box display="flex" alignItems="center" gap={0.5} flexShrink={0}>
                            <Chip
                              size="small"
                              label={`${entry.type === 'CREDIT' ? '+' : '-'} ${formatBRL(entry.amount)}`}
                              color={entry.type === 'CREDIT' ? 'success' : 'error'}
                              variant="outlined"
                              sx={{ fontWeight: 600 }}
                            />
                            {isDeletable(entry) && (
                              <Tooltip title="Apagar salário (admin)">
                                <IconButton
                                  size="small"
                                  onClick={() => setConfirmEntry(entry)}
                                  aria-label={`Apagar lançamento ${entry.id}`}
                                >
                                  <DeleteOutlineIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Box>
                        </Box>
                      }
                      secondary={
                        settled
                          ? settled
                          : entry.due_date
                          ? `${entry.description ? entry.description + ' · ' : ''}Vence ${new Date(entry.due_date + 'T00:00:00').toLocaleDateString('pt-BR')}`
                          : entry.description || undefined
                      }
                    />
                  </ListItem>
                );
              })}
            </List>
          </Box>
        );
      })}

      <Dialog open={confirmEntry !== null} onClose={() => setConfirmEntry(null)}>
        <DialogTitle>Apagar lançamento?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {confirmEntry && (
              <>
                Tem certeza que deseja apagar este lançamento de{' '}
                <strong>{categoryLabel(confirmEntry.category)}</strong> de{' '}
                <strong>{formatBRL(confirmEntry.amount)}</strong>?
                <br />A entrada ficará marcada como estornada (mantida para auditoria).
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmEntry(null)}>Cancelar</Button>
          <Button
            onClick={onConfirmDelete}
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Apagando…' : 'Apagar'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!errorMsg}
        autoHideDuration={5000}
        onClose={() => setErrorMsg('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="error" onClose={() => setErrorMsg('')}>
          {errorMsg}
        </Alert>
      </Snackbar>
    </Box>
  );
}
