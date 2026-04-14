import { Card, CardContent, Typography, Box, Skeleton, Chip, Stack } from '@mui/material';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import { formatBRL } from '../../../lib/format/currency';
import { LedgerBalance } from '../services/ledgerApi';

interface BalanceCardProps {
  balance?: LedgerBalance;
  loading?: boolean;
  userName?: string;
}

export function BalanceCard({ balance, loading, userName }: BalanceCardProps) {
  const isPositive = (balance?.balance ?? 0) >= 0;

  return (
    <Card elevation={2} sx={{ borderRadius: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <AccountBalanceWalletIcon color="primary" />
          <Typography variant="subtitle2" color="text.secondary">
            {userName ? `Saldo — ${userName}` : 'Saldo Devedor'}
          </Typography>
        </Box>

        {loading ? (
          <Skeleton variant="text" width={160} height={48} />
        ) : (
          <Typography
            variant="h4"
            fontWeight={700}
            color={isPositive ? 'success.main' : 'error.main'}
          >
            {formatBRL(balance?.balance ?? 0)}
          </Typography>
        )}

        <Stack direction="row" gap={1} mt={1} flexWrap="wrap">
          <Chip
            size="small"
            icon={<CheckCircleOutlineIcon />}
            label={`Confirmado: ${formatBRL(balance?.confirmed_credits ?? 0)}`}
            color="success"
            variant="outlined"
          />
          <Chip
            size="small"
            icon={<HourglassEmptyIcon />}
            label={`Pendente: ${formatBRL(balance?.pending_credits ?? 0)}`}
            color="warning"
            variant="outlined"
          />
          <Chip
            size="small"
            label={`Débitos: ${formatBRL(balance?.total_debits ?? 0)}`}
            color="error"
            variant="outlined"
          />
        </Stack>
      </CardContent>
    </Card>
  );
}
