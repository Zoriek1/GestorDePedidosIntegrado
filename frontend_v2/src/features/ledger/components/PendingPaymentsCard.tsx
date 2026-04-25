import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Button,
  Chip,
  Skeleton,
  Divider,
  Alert,
} from '@mui/material';
import PendingActionsIcon from '@mui/icons-material/PendingActions';
import PaymentsIcon from '@mui/icons-material/Payments';
import { useMemo } from 'react';
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

const SALARY_CATEGORIES = new Set([
  'fixo_semanal',
  'fixo_mensal',
  'almoco',
  'transporte',
  'custom_credit',
]);

function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

function commissionSourceLabel(category: string): string {
  // "comissao_whatsapp" → "WhatsApp"; "comissao_site" → "Site"
  const slug = category.startsWith('comissao_') ? category.slice('comissao_'.length) : category;
  if (!slug) return 'Outras';
  return slug.charAt(0).toUpperCase() + slug.slice(1);
}

interface AggregatedGroup {
  key: string;
  label: string;
  total: number;
  count: number;
  isOverdue: boolean;
}

function aggregate(entries: LedgerEntry[]): {
  salaryGroups: AggregatedGroup[];
  commissionGroups: AggregatedGroup[];
  total: number;
  hasOverdue: boolean;
} {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const salaryMap = new Map<string, AggregatedGroup>();
  const commissionMap = new Map<string, AggregatedGroup>();
  let total = 0;
  let hasOverdue = false;

  for (const entry of entries) {
    let isOverdue = false;
    if (entry.due_date) {
      const due = new Date(entry.due_date + 'T00:00:00');
      isOverdue = due.getTime() < today.getTime();
      if (isOverdue) hasOverdue = true;
    }

    const target = SALARY_CATEGORIES.has(entry.category) ? salaryMap : commissionMap;
    const key = entry.category;
    const label = SALARY_CATEGORIES.has(entry.category)
      ? categoryLabel(entry.category)
      : commissionSourceLabel(entry.category);

    const existing = target.get(key);
    if (existing) {
      existing.total += entry.amount;
      existing.count += 1;
      if (isOverdue) existing.isOverdue = true;
    } else {
      target.set(key, { key, label, total: entry.amount, count: 1, isOverdue });
    }
    total += entry.amount;
  }

  const sortByTotalDesc = (a: AggregatedGroup, b: AggregatedGroup) => b.total - a.total;

  return {
    salaryGroups: Array.from(salaryMap.values()).sort(sortByTotalDesc),
    commissionGroups: Array.from(commissionMap.values()).sort(sortByTotalDesc),
    total,
    hasOverdue,
  };
}

export function PendingPaymentsCard({ userId, isAdmin }: PendingPaymentsCardProps) {
  const pendingQuery = usePendingPayments(userId);
  const settleMutation = useSettleUser();

  const entries: LedgerEntry[] = useMemo(
    () => pendingQuery.data ?? [],
    [pendingQuery.data]
  );
  const { salaryGroups, commissionGroups, total, hasOverdue } = useMemo(
    () => aggregate(entries),
    [entries]
  );

  const handleSettle = () => {
    settleMutation.mutate(userId);
  };

  const salaryTotal = salaryGroups.reduce((acc, g) => acc + g.total, 0);
  const commissionTotal = commissionGroups.reduce((acc, g) => acc + g.total, 0);

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
                Apenas valores desta semana. Clique em "Recebi" após receber o pagamento.
              </Typography>
            )}
            <Divider sx={{ mb: 1.5 }} />

            {salaryGroups.length > 0 && (
              <Box mb={commissionGroups.length > 0 ? 2 : 0}>
                <Box display="flex" alignItems="baseline" justifyContent="space-between" mb={0.5}>
                  <Typography variant="body2" fontWeight={700}>
                    Salário
                  </Typography>
                  <Typography variant="body2" fontWeight={700} color="success.main">
                    {formatBRL(salaryTotal)}
                  </Typography>
                </Box>
                <Stack spacing={0.25} pl={1.5}>
                  {salaryGroups.map((g) => (
                    <Box key={g.key} display="flex" alignItems="baseline" justifyContent="space-between">
                      <Typography variant="caption" color="text.secondary">
                        {g.label}
                        {g.count > 1 ? ` ×${g.count}` : ''}
                      </Typography>
                      <Typography variant="caption" color={g.isOverdue ? 'error.main' : 'text.primary'}>
                        {formatBRL(g.total)}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>
            )}

            {commissionGroups.length > 0 && (
              <Box>
                <Box display="flex" alignItems="baseline" justifyContent="space-between" mb={0.5}>
                  <Typography variant="body2" fontWeight={700}>
                    Comissões
                  </Typography>
                  <Typography variant="body2" fontWeight={700} color="success.main">
                    {formatBRL(commissionTotal)}
                  </Typography>
                </Box>
                <Stack spacing={0.25} pl={1.5}>
                  {commissionGroups.map((g) => (
                    <Box key={g.key} display="flex" alignItems="baseline" justifyContent="space-between">
                      <Typography variant="caption" color="text.secondary">
                        {g.label}
                        {g.count > 1 ? ` (${g.count} pedidos)` : g.count === 1 ? ' (1 pedido)' : ''}
                      </Typography>
                      <Typography variant="caption" color={g.isOverdue ? 'error.main' : 'text.primary'}>
                        {formatBRL(g.total)}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
