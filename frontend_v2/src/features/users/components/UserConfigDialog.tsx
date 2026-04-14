import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Stack,
  Typography,
  Divider,
  IconButton,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  CircularProgress,
  Box,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import {
  useUserConfig,
  useUpdatePayroll,
  useUpdateCommission,
  PayrollConfig,
} from '../services/userApi';
import { useToast } from '../../../components/system/useToast';

const SOURCES = [
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'site', label: 'Site' },
  { value: 'balcao', label: 'Balcão' },
  { value: 'indicacao', label: 'Indicação' },
  { value: 'lucro_bruto', label: 'Lucro Bruto (em breve)' },
];

const PAYROLL_CATEGORIES = [
  { value: 'fixo_semanal', label: 'Salário Semanal' },
  { value: 'fixo_mensal', label: 'Salário Mensal' },
  { value: 'almoco', label: 'Vale Almoço' },
  { value: 'transporte', label: 'Vale Transporte' },
  { value: 'custom', label: 'Personalizado' },
];

interface UserConfigDialogProps {
  open: boolean;
  onClose: () => void;
  userId: number;
  userName: string;
}

export function UserConfigDialog({ open, onClose, userId, userName }: UserConfigDialogProps) {
  const toast = useToast();
  const configQuery = useUserConfig(userId);
  const updatePayroll = useUpdatePayroll(userId);
  const updateCommission = useUpdateCommission(userId);

  // Estado local de edição de payroll
  const [newPayroll, setNewPayroll] = useState<Partial<PayrollConfig>>({
    category: 'fixo_semanal',
    label: 'Salário Semanal',
    amount: 0,
    frequency: 'semanal',
  });

  // Estado local de edição de commission
  const [newCommission, setNewCommission] = useState({ source: 'whatsapp', rate: '' });

  const handleAddPayroll = async () => {
    if (!newPayroll.amount || Number(newPayroll.amount) <= 0) {
      toast.error('Informe um valor válido');
      return;
    }
    try {
      await updatePayroll.mutateAsync([newPayroll]);
      toast.success('Remuneração atualizada');
      setNewPayroll({ category: 'fixo_semanal', label: 'Salário Semanal', amount: 0, frequency: 'semanal' });
    } catch (e) {
      toast.error(`Erro: ${(e as Error).message}`);
    }
  };

  const handleAddCommission = async () => {
    const rate = parseFloat(String(newCommission.rate).replace(',', '.')) / 100;
    if (isNaN(rate) || rate <= 0) {
      toast.error('Informe uma taxa válida (%)');
      return;
    }
    try {
      await updateCommission.mutateAsync([{ source: newCommission.source, rate }]);
      toast.success('Comissão atualizada');
      setNewCommission({ source: 'whatsapp', rate: '' });
    } catch (e) {
      toast.error(`Erro: ${(e as Error).message}`);
    }
  };

  const isLoading = configQuery.isLoading;
  const payroll = configQuery.data?.payroll ?? [];
  const commission = configQuery.data?.commission ?? [];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Configurar: {userName}</DialogTitle>
      <DialogContent dividers>
        {isLoading ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Stack spacing={3}>
            {/* ---- Remuneração Fixa ---- */}
            <Box>
              <Typography variant="subtitle1" fontWeight={600} mb={1}>
                Remuneração Fixa
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Categoria</TableCell>
                    <TableCell>Descrição</TableCell>
                    <TableCell>Valor</TableCell>
                    <TableCell>Frequência</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {payroll.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4}>
                        <Typography variant="caption" color="text.secondary">
                          Nenhuma configuração ativa
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    payroll.map((p) => (
                      <TableRow key={p.id}>
                        <TableCell>{p.category}</TableCell>
                        <TableCell>{p.label}</TableCell>
                        <TableCell>
                          {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(p.amount)}
                        </TableCell>
                        <TableCell>{p.frequency}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>

              <Stack direction="row" gap={1} mt={2} flexWrap="wrap" alignItems="flex-end">
                <TextField
                  select
                  label="Categoria"
                  value={newPayroll.category}
                  onChange={(e) => {
                    const cat = PAYROLL_CATEGORIES.find((c) => c.value === e.target.value);
                    setNewPayroll((p) => ({ ...p, category: e.target.value, label: cat?.label ?? '' }));
                  }}
                  size="small"
                  sx={{ minWidth: 180 }}
                >
                  {PAYROLL_CATEGORIES.map((c) => (
                    <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Descrição"
                  value={newPayroll.label}
                  onChange={(e) => setNewPayroll((p) => ({ ...p, label: e.target.value }))}
                  size="small"
                  sx={{ minWidth: 160 }}
                />
                <TextField
                  label="Valor (R$)"
                  value={newPayroll.amount || ''}
                  onChange={(e) => setNewPayroll((p) => ({ ...p, amount: Number(e.target.value) }))}
                  size="small"
                  sx={{ width: 110 }}
                  inputProps={{ inputMode: 'decimal' }}
                />
                <TextField
                  select
                  label="Frequência"
                  value={newPayroll.frequency}
                  onChange={(e) => setNewPayroll((p) => ({ ...p, frequency: e.target.value as 'semanal' | 'mensal' }))}
                  size="small"
                  sx={{ minWidth: 120 }}
                >
                  <MenuItem value="semanal">Semanal</MenuItem>
                  <MenuItem value="mensal">Mensal</MenuItem>
                </TextField>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={handleAddPayroll}
                  disabled={updatePayroll.isPending}
                >
                  Adicionar
                </Button>
              </Stack>
            </Box>

            <Divider />

            {/* ---- Comissões ---- */}
            <Box>
              <Typography variant="subtitle1" fontWeight={600} mb={1}>
                Comissões por Fonte
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Fonte</TableCell>
                    <TableCell>Taxa</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {commission.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3}>
                        <Typography variant="caption" color="text.secondary">
                          Nenhuma comissão configurada
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    commission.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell>
                          {SOURCES.find((s) => s.value === c.source)?.label ?? c.source}
                        </TableCell>
                        <TableCell>{(c.rate * 100).toFixed(1)}%</TableCell>
                        <TableCell>
                          {c.source === 'lucro_bruto' ? (
                            <Chip label="Em breve" size="small" />
                          ) : (
                            <Chip label="Ativo" size="small" color="success" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>

              <Stack direction="row" gap={1} mt={2} flexWrap="wrap" alignItems="flex-end">
                <TextField
                  select
                  label="Fonte"
                  value={newCommission.source}
                  onChange={(e) => setNewCommission((c) => ({ ...c, source: e.target.value }))}
                  size="small"
                  sx={{ minWidth: 160 }}
                >
                  {SOURCES.map((s) => (
                    <MenuItem key={s.value} value={s.value}>{s.label}</MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Taxa (%)"
                  value={newCommission.rate}
                  onChange={(e) => setNewCommission((c) => ({ ...c, rate: e.target.value }))}
                  size="small"
                  sx={{ width: 100 }}
                  placeholder="3"
                  inputProps={{ inputMode: 'decimal' }}
                />
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={handleAddCommission}
                  disabled={updateCommission.isPending}
                >
                  Salvar
                </Button>
              </Stack>
            </Box>
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fechar</Button>
      </DialogActions>
    </Dialog>
  );
}
