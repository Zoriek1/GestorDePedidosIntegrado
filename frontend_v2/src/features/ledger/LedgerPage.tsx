import { useState } from 'react';
import {
  Box,
  Typography,
  Stack,
  Button,
  TextField,
  MenuItem,
  Divider,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Snackbar,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import AddIcon from '@mui/icons-material/Add';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import { BalanceCard } from './components/BalanceCard';
import { EntryList } from './components/EntryList';
import { PendingPaymentsCard } from './components/PendingPaymentsCard';
import { PaymentDialog } from './components/PaymentDialog';
import { WeeklyGenerateBtn } from './components/WeeklyGenerateBtn';
import {
  useLedgerBalance,
  useLedgerEntries,
  useLedgerSummary,
  useGenerateCalendar,
} from './services/ledgerApi';
import { useAuth } from '../auth/authStore';
import { getApiBaseUrl } from '../../api/http';

export default function LedgerPage() {
  const { getUserRole, getUser, getAuthHeader } = useAuth();
  const role = getUserRole();
  const user = getUser();
  const isAdmin = role === 'admin';

  // Para admin, permite selecionar vendedor
  const [selectedUserId, setSelectedUserId] = useState<number | undefined>(
    isAdmin ? undefined : (user?.id ?? undefined)
  );
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  // Calendário modal
  const [calendarDialogOpen, setCalendarDialogOpen] = useState(false);
  const [calendarWeeks, setCalendarWeeks] = useState(4);
  const [snackbarMsg, setSnackbarMsg] = useState('');

  const generateCalendar = useGenerateCalendar();

  // Queries
  const balanceQuery = useLedgerBalance(selectedUserId);
  const entriesQuery = useLedgerEntries({
    user_id: selectedUserId,
    from: fromDate || undefined,
    to: toDate || undefined,
  });
  const summaryQuery = useLedgerSummary();

  const activeUserId = selectedUserId ?? user?.id ?? 0;
  const selectedUserName = isAdmin
    ? summaryQuery.data?.find((s) => s.user.id === selectedUserId)?.user.name
    : user?.name;

  // URL de exportação CSV
  const exportUrl = () => {
    const base = getApiBaseUrl();
    const params = new URLSearchParams();
    if (selectedUserId) params.set('user_id', String(selectedUserId));
    if (fromDate) params.set('from', fromDate);
    if (toDate) params.set('to', toDate);
    return `${base}/ledger/export?${params.toString()}`;
  };

  const handleExport = async () => {
    try {
      const res = await fetch(exportUrl(), { headers: getAuthHeader() });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `extrato_${activeUserId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silencioso
    }
  };

  const handleGenerateCalendar = async () => {
    try {
      const result = await generateCalendar.mutateAsync({ nWeeks: calendarWeeks });
      setCalendarDialogOpen(false);
      setSnackbarMsg(
        `Calendário gerado: ${result.total_created} lançamento(s) criado(s) em ${result.weeks.length} semanas.`
      );
    } catch (e) {
      setSnackbarMsg(`Erro: ${(e as Error).message}`);
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: { xs: 2, sm: 3 } }}>
      {/* Cabeçalho */}
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ sm: 'center' }}
        mb={3}
        gap={1}
      >
        <Typography variant="h5" fontWeight={700}>
          Recebíveis
        </Typography>

        <Stack direction="row" gap={1} flexWrap="wrap">
          {isAdmin && <WeeklyGenerateBtn />}
          {isAdmin && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<CalendarMonthIcon />}
              onClick={() => setCalendarDialogOpen(true)}
            >
              Calendário
            </Button>
          )}
          {isAdmin && activeUserId > 0 && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<AddIcon />}
              onClick={() => setPaymentDialogOpen(true)}
            >
              Lançamento
            </Button>
          )}
          <Button
            variant="outlined"
            size="small"
            startIcon={<DownloadIcon />}
            onClick={handleExport}
            disabled={!activeUserId}
          >
            Exportar CSV
          </Button>
        </Stack>
      </Stack>

      {/* Seletor de vendedor (admin) */}
      {isAdmin && (
        <TextField
          select
          label="Vendedor"
          value={selectedUserId ?? ''}
          onChange={(e) => setSelectedUserId(e.target.value ? Number(e.target.value) : undefined)}
          fullWidth
          sx={{ mb: 2 }}
          size="small"
        >
          <MenuItem value="">— Selecione um vendedor —</MenuItem>
          {summaryQuery.data?.map((s) => (
            <MenuItem key={s.user.id} value={s.user.id}>
              {s.user.name} ({s.user.email})
            </MenuItem>
          ))}
        </TextField>
      )}

      {/* Card de saldo */}
      {activeUserId > 0 && (
        <Box mb={2}>
          <BalanceCard
            balance={balanceQuery.data}
            loading={balanceQuery.isLoading}
            userName={selectedUserName}
          />
        </Box>
      )}

      {/* Pagamentos pendentes */}
      {activeUserId > 0 && (
        <Box mb={3}>
          <PendingPaymentsCard userId={activeUserId} isAdmin={isAdmin} />
        </Box>
      )}

      {/* Filtros de período */}
      {activeUserId > 0 && (
        <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} mb={2}>
          <TextField
            label="De"
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            size="small"
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            label="Até"
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            size="small"
            InputLabelProps={{ shrink: true }}
          />
          {(fromDate || toDate) && (
            <Button size="small" onClick={() => { setFromDate(''); setToDate(''); }}>
              Limpar
            </Button>
          )}
        </Stack>
      )}

      <Divider sx={{ mb: 2 }} />

      {/* Extrato */}
      {!activeUserId && isAdmin ? (
        <Alert severity="info">Selecione um vendedor para ver o extrato.</Alert>
      ) : (
        <EntryList
          entries={entriesQuery.data ?? []}
          loading={entriesQuery.isLoading}
        />
      )}

      {/* Resumo admin */}
      {isAdmin && !selectedUserId && summaryQuery.data && summaryQuery.data.length > 0 && (
        <Box mt={3}>
          <Typography variant="subtitle1" fontWeight={600} mb={1}>
            Resumo Geral
          </Typography>
          <Stack spacing={1}>
            {summaryQuery.data.map((s) => (
              <Box
                key={s.user.id}
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                sx={{
                  p: 1.5,
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
                onClick={() => setSelectedUserId(s.user.id)}
              >
                <Typography variant="body2" fontWeight={500}>
                  {s.user.name}
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color={s.balance >= 0 ? 'success.main' : 'error.main'}
                >
                  {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(s.balance)}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Box>
      )}

      {/* Dialog de lançamento manual */}
      {isAdmin && paymentDialogOpen && (
        <PaymentDialog
          open={paymentDialogOpen}
          onClose={() => setPaymentDialogOpen(false)}
          userId={activeUserId}
          userName={selectedUserName}
        />
      )}

      {/* Dialog geração de calendário */}
      <Dialog open={calendarDialogOpen} onClose={() => setCalendarDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Gerar Calendário de Recebíveis</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Gera lançamentos fixos semanais para todas as vendedoras ativas,
            considerando o dia de pagamento configurado em cada item.
          </DialogContentText>
          <TextField
            label="Número de semanas"
            type="number"
            value={calendarWeeks}
            onChange={(e) => setCalendarWeeks(Math.max(1, Math.min(52, Number(e.target.value))))}
            fullWidth
            size="small"
            inputProps={{ min: 1, max: 52 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCalendarDialogOpen(false)}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={handleGenerateCalendar}
            disabled={generateCalendar.isPending}
          >
            Gerar
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar de feedback */}
      <Snackbar
        open={!!snackbarMsg}
        autoHideDuration={5000}
        onClose={() => setSnackbarMsg('')}
        message={snackbarMsg}
      />
    </Box>
  );
}
