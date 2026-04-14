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
  CircularProgress,
} from '@mui/material';
import { useCreateLedgerEntry, ManualEntryPayload } from '../services/ledgerApi';
import { useToast } from '../../../components/system/useToast';

const DEBIT_CATEGORIES = [
  { value: 'pagamento', label: 'Pagamento' },
  { value: 'adiantamento', label: 'Adiantamento' },
  { value: 'ajuste_debito', label: 'Ajuste Débito' },
];

const CREDIT_CATEGORIES = [
  { value: 'custom_credit', label: 'Crédito Avulso / Bônus' },
  { value: 'fixo_semanal', label: 'Salário Semanal (manual)' },
  { value: 'fixo_mensal', label: 'Salário Mensal (manual)' },
  { value: 'almoco', label: 'Vale Almoço (manual)' },
  { value: 'transporte', label: 'Vale Transporte (manual)' },
];

interface PaymentDialogProps {
  open: boolean;
  onClose: () => void;
  userId: number;
  userName?: string;
}

export function PaymentDialog({ open, onClose, userId, userName }: PaymentDialogProps) {
  const toast = useToast();
  const { mutateAsync, isPending } = useCreateLedgerEntry();

  const [entryType, setEntryType] = useState<'DEBIT' | 'CREDIT'>('DEBIT');
  const [category, setCategory] = useState('pagamento');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [weekRef, setWeekRef] = useState('');

  const categories = entryType === 'DEBIT' ? DEBIT_CATEGORIES : CREDIT_CATEGORIES;

  const handleTypeChange = (type: 'DEBIT' | 'CREDIT') => {
    setEntryType(type);
    setCategory(type === 'DEBIT' ? 'pagamento' : 'custom_credit');
  };

  const handleSubmit = async () => {
    const amountNum = parseFloat(amount.replace(',', '.'));
    if (!amount || isNaN(amountNum) || amountNum <= 0) {
      toast.error('Informe um valor válido');
      return;
    }

    const payload: ManualEntryPayload = {
      user_id: userId,
      type: entryType,
      category,
      amount: amountNum,
      description: description || undefined,
      week_ref: weekRef || undefined,
    };

    try {
      await mutateAsync(payload);
      toast.success('Lançamento registrado com sucesso');
      onClose();
      setAmount('');
      setDescription('');
      setWeekRef('');
    } catch (e) {
      toast.error(`Erro: ${(e as Error).message}`);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Lançamento Manual — {userName ?? `Usuário #${userId}`}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} mt={1}>
          <TextField
            select
            label="Tipo"
            value={entryType}
            onChange={(e) => handleTypeChange(e.target.value as 'DEBIT' | 'CREDIT')}
            fullWidth
          >
            <MenuItem value="DEBIT">Débito (pagamento / desconto)</MenuItem>
            <MenuItem value="CREDIT">Crédito (bônus / ajuste)</MenuItem>
          </TextField>

          <TextField
            select
            label="Categoria"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            fullWidth
          >
            {categories.map((c) => (
              <MenuItem key={c.value} value={c.value}>
                {c.label}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            label="Valor (R$)"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0,00"
            fullWidth
            inputProps={{ inputMode: 'decimal' }}
          />

          <TextField
            label="Descrição (opcional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            fullWidth
            multiline
            rows={2}
          />

          <TextField
            label="Semana de referência (opcional)"
            type="date"
            value={weekRef}
            onChange={(e) => setWeekRef(e.target.value)}
            fullWidth
            helperText="Deixe em branco para usar a semana atual"
            InputLabelProps={{ shrink: true }}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isPending}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isPending}
          startIcon={isPending ? <CircularProgress size={16} /> : undefined}
        >
          Registrar
        </Button>
      </DialogActions>
    </Dialog>
  );
}
