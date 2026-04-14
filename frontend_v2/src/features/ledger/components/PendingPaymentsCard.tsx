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
import CheckIcon from '@mui/icons-material/Check';
import { formatBRL } from '../../../lib/format/currency';
import { LedgerEntry, usePendingPayments, useConfirmEntry } from '../services/ledgerApi';

interface PendingPaymentsCardProps {
  userId?: number;
  isAdmin?: boolean;
}

function categoryLabel(category: string): string {
  const labels: Record<string, string> = {
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
  return labels[category] ?? category;
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
  const confirmMutation = useConfirmEntry();

  const entries: LedgerEntry[] = pendingQuery.data ?? [];

  const handleConfirm = (entryId: number) => {
    confirmMutation.mutate(entryId);
  };

  return (
    <Card
      elevation={2}
      sx={{
        borderRadius: 2,
        border: entries.length > 0 ? '1px solid' : undefined,
        borderColor: entries.length > 0 ? 'warning.light' : undefined,
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <PendingActionsIcon color="warning" />
          <Typography variant="subtitle2" color="text.secondary">
            Pagamentos Pendentes
          </Typography>
          {entries.length > 0 && (
            <Chip
              size="small"
              label={entries.length}
              color="warning"
              sx={{ height: 20, fontSize: '0.7rem' }}
            />
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
            Nenhum pagamento pendente. Tudo em dia!
          </Alert>
        ) : (
          <>
            {!isAdmin && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                Clique em "Recebi" após receber o pagamento.
              </Typography>
            )}
            <Divider sx={{ mb: 1 }} />
            <List dense disablePadding>
              {entries.map((entry) => {
                const dueFmt = formatDueDate(entry.due_date);
                const dueColor = dueDateColor(entry.due_date);
                return (
                  <ListItem
                    key={entry.id}
                    disableGutters
                    sx={{ px: 0, py: 0.5 }}
                    secondaryAction={
                      <Button
                        size="small"
                        variant="contained"
                        color="success"
                        startIcon={<CheckIcon />}
                        onClick={() => handleConfirm(entry.id)}
                        disabled={confirmMutation.isPending}
                        sx={{ minWidth: 80, fontSize: '0.75rem' }}
                      >
                        Recebi
                      </Button>
                    }
                  >
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={0.5}>
                          <Typography variant="body2" fontWeight={500}>
                            {categoryLabel(entry.category)}
                          </Typography>
                          <Typography variant="body2" color="success.main" fontWeight={600}>
                            {formatBRL(entry.amount)}
                          </Typography>
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
