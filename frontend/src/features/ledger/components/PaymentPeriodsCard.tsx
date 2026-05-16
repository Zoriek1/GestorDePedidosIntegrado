import { Alert, Box, Chip, Skeleton, Stack, Typography } from '@mui/material';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import { formatBRL } from '../../../lib/format/currency';
import { LedgerPeriod } from '../services/ledgerApi';

interface PaymentPeriodsCardProps {
  periods: LedgerPeriod[];
  loading?: boolean;
}

function fmtDate(value: string | null): string {
  if (!value) return 'Sem data';
  const d = new Date(value + 'T00:00:00');
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

export function PaymentPeriodsCard({ periods, loading }: PaymentPeriodsCardProps) {
  if (loading) {
    return (
      <Box>
        {[1, 2].map((i) => (
          <Skeleton key={i} variant="rectangular" height={56} sx={{ mb: 1, borderRadius: 1 }} />
        ))}
      </Box>
    );
  }

  if (!periods.length) {
    return <Alert severity="info">Sem comissões agrupadas por período de pagamento.</Alert>;
  }

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <CalendarMonthIcon fontSize="small" color="action" />
        <Typography variant="subtitle2" fontWeight={600}>
          Períodos de Pagamento
        </Typography>
      </Box>
      <Stack spacing={1}>
        {periods.map((period, idx) => (
          <Box
            key={`${period.period_date || 'sem_data'}-${idx}`}
            sx={{
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1.5,
              px: 1.5,
              py: 1,
            }}
          >
            <Box display="flex" justifyContent="space-between" alignItems="center" gap={1}>
              <Box>
                <Typography variant="body2" fontWeight={600}>
                  {fmtDate(period.period_date)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {period.orders_count} pedido(s)
                </Typography>
              </Box>
              <Typography variant="body2" fontWeight={700} color="success.main">
                {formatBRL(period.total_commission)}
              </Typography>
            </Box>
            <Stack direction="row" gap={1} mt={1} flexWrap="wrap">
              <Chip
                size="small"
                label={`Ativo: ${formatBRL(period.active_commission)}`}
                color={period.is_overdue ? 'error' : 'warning'}
                variant="outlined"
              />
              <Chip
                size="small"
                label={`Quitado: ${formatBRL(period.settled_commission)}`}
                color="success"
                variant="outlined"
              />
              <Chip
                size="small"
                label={period.status}
                color={period.is_overdue ? 'error' : 'default'}
                variant="outlined"
              />
            </Stack>
            {period.by_source.length > 0 && (
              <Stack direction="row" gap={0.5} mt={1} flexWrap="wrap">
                {period.by_source.map((source, sourceIdx) => (
                  <Chip
                    key={`${source.source_id ?? 'legacy'}-${source.source_slug ?? sourceIdx}`}
                    size="small"
                    variant="outlined"
                    label={`${source.source || 'Sem fonte'}: ${formatBRL(source.total)}`}
                  />
                ))}
              </Stack>
            )}
          </Box>
        ))}
      </Stack>
    </Box>
  );
}
