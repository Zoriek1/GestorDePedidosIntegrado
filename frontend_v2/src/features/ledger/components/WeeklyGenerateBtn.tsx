import { useState } from 'react';
import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  CircularProgress,
  TextField,
  Stack,
} from '@mui/material';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import { useGenerateWeekly } from '../services/ledgerApi';
import { useToast } from '../../../components/system/useToast';

export function WeeklyGenerateBtn() {
  const toast = useToast();
  const { mutateAsync, isPending } = useGenerateWeekly();
  const [open, setOpen] = useState(false);
  const [weekRef, setWeekRef] = useState('');

  const handleGenerate = async () => {
    try {
      const result = await mutateAsync(weekRef || undefined);
      toast.success(
        `Semana gerada: ${result.created} criados, ${result.skipped} já existiam`
      );
      setOpen(false);
      setWeekRef('');
    } catch (e) {
      toast.error(`Erro: ${(e as Error).message}`);
    }
  };

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<AutorenewIcon />}
        onClick={() => setOpen(true)}
        size="small"
      >
        Gerar Semana
      </Button>

      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Gerar Créditos Fixos da Semana</DialogTitle>
        <DialogContent>
          <Stack spacing={2} mt={1}>
            <DialogContentText>
              Gera os créditos fixos (salário, vale almoço, transporte) para todos os vendedores
              ativos com configuração ativa. A operação é idempotente — não cria duplicatas.
            </DialogContentText>
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
          <Button onClick={() => setOpen(false)} disabled={isPending}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={handleGenerate}
            disabled={isPending}
            startIcon={isPending ? <CircularProgress size={16} /> : undefined}
          >
            Gerar
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
