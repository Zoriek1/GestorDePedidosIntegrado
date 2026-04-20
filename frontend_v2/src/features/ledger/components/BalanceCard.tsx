import { Card, CardContent, Typography, Box, Skeleton, Chip, Stack } from '@mui/material';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import ScheduleIcon from '@mui/icons-material/Schedule';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import { formatBRL } from '../../../lib/format/currency';
import { LedgerBalance } from '../services/ledgerApi';

interface BalanceCardProps {
  balance?: LedgerBalance;
  loading?: boolean;
  userName?: string;
}

export function BalanceCard({ balance, loading, userName }: BalanceCardProps) {
  const totalAReceber = balance?.balance ?? 0;
  const aReceber = (balance?.due_today_credits ?? 0) + (balance?.upcoming_credits ?? 0);

  return (
    <Card elevation={2} sx={{ borderRadius: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <AccountBalanceWalletIcon color="primary" />
          <Typography variant="subtitle2" color="text.secondary">
            {userName ? `A Receber — ${userName}` : 'Contas a Receber'}
          </Typography>
        </Box>

        {loading ? (
          <Skeleton variant="text" width={160} height={48} />
        ) : (
          <Typography
            variant="h4"
            fontWeight={700}
            color="success.main"
          >
            {formatBRL(totalAReceber)}
          </Typography>
        )}

        <Stack direction="row" gap={1} mt={1} flexWrap="wrap">
          {/* A Receber (due_today + upcoming) */}
          <Chip
            size="small"
            icon={<ScheduleIcon />}
            label={`A receber: ${formatBRL(aReceber)}`}
            color="info"
            variant="outlined"
          />
          {/* Atrasado */}
          {(balance?.overdue_credits ?? 0) > 0 && (
            <Chip
              size="small"
              icon={<WarningAmberIcon />}
              label={`Atrasado: ${formatBRL(balance?.overdue_credits ?? 0)}`}
              color="error"
              variant="outlined"
            />
          )}
          {/* Débitos totais */}
          {(balance?.total_debits ?? 0) > 0 && (
            <Chip
              size="small"
              icon={<RemoveCircleOutlineIcon />}
              label={`Quitado: ${formatBRL(balance?.total_debits ?? 0)}`}
              color="default"
              variant="outlined"
            />
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
