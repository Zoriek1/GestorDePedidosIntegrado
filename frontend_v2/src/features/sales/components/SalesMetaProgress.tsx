import { useMemo, useState } from 'react';
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, Paper, TextField, Typography } from '@mui/material';
import dayjs from 'dayjs';
import { useMetaFaturamento, useUpdateMetaFaturamento } from '../../../api/endpoints/config';

interface SalesMetaProgressProps {
  startDate: string;
  /** Faturamento bruto do período (sem descontar entregas) para comparar com a meta */
  totalBruto: number;
}

export function SalesMetaProgress({ startDate, totalBruto }: SalesMetaProgressProps) {
  const mes = useMemo(() => dayjs(startDate).format('YYYY-MM'), [startDate]);
  const { data, isLoading } = useMetaFaturamento(mes);
  const { mutateAsync: updateMeta, isPending } = useUpdateMetaFaturamento();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [metaInput, setMetaInput] = useState('');

  const metaValor = data?.valor ?? null;
  const progress = metaValor && metaValor > 0 ? Math.min((totalBruto / metaValor) * 100, 100) : 0;
  const metaLabel = dayjs(startDate).format('MMMM [de] YYYY');

  const handleOpen = () => {
    setMetaInput(metaValor ? String(metaValor) : '');
    setDialogOpen(true);
  };

  const handleSave = async () => {
    const valor = parseFloat(metaInput.replace(',', '.'));
    if (Number.isNaN(valor)) return;
    await updateMeta({ mes, valor });
    setDialogOpen(false);
  };

  return (
    <Paper sx={{ p: 3, mt: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6">Meta de Faturamento</Typography>
        <Button size="small" variant="outlined" onClick={handleOpen}>
          {metaValor ? 'Editar meta' : 'Definir meta'}
        </Button>
      </Box>

      {isLoading ? (
        <Typography variant="body2" color="text.secondary">
          Carregando meta...
        </Typography>
      ) : metaValor && metaValor > 0 ? (
        <>
          <Typography variant="body2" color="text.secondary">
            Meta do mês ({metaLabel})
          </Typography>
          <Typography variant="body1" sx={{ mt: 0.5 }}>
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalBruto)} /{' '}
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(metaValor)}
          </Typography>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              mt: 1.5,
              height: 10,
              borderRadius: 5,
              '& .MuiLinearProgress-bar': {
                backgroundColor: progress < 50 ? '#ef4444' : progress < 90 ? '#f59e0b' : '#22c55e',
              },
            }}
          />
        </>
      ) : (
        <Typography variant="body2" color="text.secondary">
          Meta não definida para {metaLabel}.
        </Typography>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Definir meta de faturamento</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Valor da meta (R$)"
            value={metaInput}
            onChange={(e) => setMetaInput(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancelar</Button>
          <Button onClick={handleSave} variant="contained" disabled={isPending}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
