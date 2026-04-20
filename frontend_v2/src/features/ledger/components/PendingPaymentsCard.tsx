import {
  Card,
  CardContent,
  Typography,
  Box,
  List,
  ListItem,
  ListItemText,
  Button,
  Chip,
  Skeleton,
  Divider,
  Alert,
} from '@mui/material';
import PendingActionsIcon from '@mui/icons-material/PendingActions';
import PaymentsIcon from '@mui/icons-material/Payments';
import { formatBRL } from '../../../lib/format/currency';
import { LedgerEntry, usePendingPayments, useSettleUser } from '../services/ledgerApi';

interface PendingPaymentsCardProps {
  userId?: number;
  isAdmin?: boolean;
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
};

function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

function formatDueDate(due_date: string | null): string | null {
  if (!due_date) return null;
  const d = new Date(due_date + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((d.getTime() - today.getTime()) / 86400000);
  const formatted = d.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' });
  if (diff < 0) return `Atrasado — ${formatted}`;
  if (diff === 0) return `Hoje — ${formatted}`;
  if (diff === 1) return `Amanhã — ${formatted}`;
  return formatted;
}

function dueDateColor(due_date: string | null): 'error' | 'warning' | 'default' {
  if (!due_date) return 'default';
  const d = new Date(due_date + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((d.getTime() - today.getTime()) / 86400000);
  if (diff < 0) return 'error';
  if (diff <= 1) return 'warning';
  return 'default';
}

export function PendingPaymentsCard({ userId, isAdmin }: PendingPaymentsCardProps) {
  const pendingQuery = usePendingPayments(userId);
  const settleMutation = useSettleUser();

  const entries: LedgerEntry[] = pendingQuery.data ?? [];
  const total = entries.reduce((acc, e) => acc + e.amount, 0);

  const hasOverdue = entries.some((e) => {
    if (!e.due_date) return false;
    const due = new Date(e.due_date + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return due.getTime() < today.getTime();
  });

  const handleSettle = () => {
    settleMutation.mutate(userId);
  };

  return (
    <Card
      elevation={2}
      sx={{
        borderRadius: 2,
        border: entries.length > 0 ? '1px solid' : undefined,
        borderColor: entries.length > 0 ? (hasOverdue ? 'error.light' : 'warning.light') : undefined,
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
          <Box display="flex" alignItems="center" gap={1}>
            <PendingActionsIcon color={hasOverdue ? 'error' : 'warning'} />
            <Typography variant="subtitle2" color="text.secondary">
              A Receber
            </Typography>
            {entries.length > 0 && (
              <Chip
                size="small"
                label={entries.length}
                color={hasOverdue ? 'error' : 'warning'}
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            )}
          </Box>

          {entries.length > 0 && (
            <Button
              variant="contained"
              color="success"
              size="small"
              startIcon={<PaymentsIcon />}
              onClick={handleSettle}
              disabled={settleMutation.isPending}
              sx={{ fontWeight: 700, minWidth: 180 }}
            >
              Recebi pagamento — {formatBRL(total)}
            </Button>
          )}
        </Box>

        {pendingQuery.isLoading ? (
          <Box>
            {[1, 2].map((i) => (
              <Skeleton key={i} variant="rectangular" height={44} sx={{ mb: 1, borderRadius: 1 }} />
            ))}
          </Box>
        ) : entries.length === 0 ? (
          <Alert severity="success" sx={{ mt: 1 }}>
            Nenhum valor pendente. Tudo em dia!
          </Alert>
        ) : (
          <>
            {!isAdmin && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                Clique em "Recebi" após receber o pagamento. Quita todos os lançamentos de uma vez.
              </Typography>
            )}
            <Divider sx={{ mb: 1 }} />
            <List dense disablePadding>
              {entries.map((entry) => {
                const dueFmt = formatDueDate(entry.due_date);
                const dueColor = dueDateColor(entry.due_date);
                return (
                  <ListItem key={entry.id} disableGutters sx={{ px: 0, py: 0.5 }}>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={0.5}>
                          <Typography variant="body2" fontWeight={500}>
                            {categoryLabel(entry.category)}
                          </Typography>
                          <Typography variant="body2" color="success.main" fontWeight={600}>
                            {formatBRL(entry.amount)}
                          </Typography>
                          {entry.pedido_id && (
                            <Typography variant="caption" color="text.secondary">
                              #{entry.pedido_id}
                            </Typography>
                          )}
                        </Box>
                      }
                      secondary={
                        dueFmt ? (
                          <Chip
                            size="small"
                            label={dueFmt}
                            color={dueColor}
                            variant="outlined"
                            sx={{ height: 18, fontSize: '0.65rem', mt: 0.25 }}
                          />
                        ) : (
                          entry.description || undefined
                        )
                      }
                      secondaryTypographyProps={{ component: 'div' }}
                    />
                  </ListItem>
                );
              })}
            </List>
          </>
        )}
      </CardContent>
    </Card>
  );
}
