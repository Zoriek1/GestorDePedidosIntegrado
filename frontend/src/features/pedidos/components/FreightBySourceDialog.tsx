import { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Box,
  CircularProgress,
  TextField,
  Stack,
} from '@mui/material';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import dayjs from 'dayjs';
import { createApiRequest } from '../../../api/http';
import { useAuth } from '../../auth/authStore';

interface FreightBySourceItem {
  fonte: string;
  total_pedidos: number;
  media_taxa_entrega: number | null;
  total_taxa_entrega: number | null;
  n_taxa_entrega: number;
  media_frete_cobrado: number | null;
  total_frete_cobrado: number | null;
  n_frete_cobrado: number;
  media_frete_liquido: number | null;
  total_frete_liquido: number | null;
  n_frete_liquido: number;
}

interface FreightBySourceDialogProps {
  open: boolean;
  onClose: () => void;
}

const formatBRL = (v: number | null) =>
  v == null
    ? '—'
    : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);

const todayISO = () => dayjs().format('YYYY-MM-DD');
const firstOfMonthISO = () => dayjs().startOf('month').format('YYYY-MM-DD');

export function FreightBySourceDialog({ open, onClose }: FreightBySourceDialogProps) {
  const { getAuthHeader } = useAuth();
  const [start, setStart] = useState(firstOfMonthISO());
  const [end, setEnd] = useState(todayISO());
  const [items, setItems] = useState<FreightBySourceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchData = useCallback(
    async (s: string, e: string) => {
      setLoading(true);
      setError('');
      try {
        const apiRequest = createApiRequest(getAuthHeader);
        const res = await apiRequest<{ items: FreightBySourceItem[] }>(
          `/pedidos/freight-by-source?start=${s}&end=${e}`,
        );
        if (!res.ok) throw new Error('Erro ao buscar dados');
        setItems(res.data.items || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao buscar dados');
      } finally {
        setLoading(false);
      }
    },
    [getAuthHeader],
  );

  useEffect(() => {
    if (!open) return;
    fetchData(start, end);
  }, [open, start, end, fetchData]);

  const totalPedidos = items.reduce((acc, it) => acc + it.total_pedidos, 0);
  const totalTaxa = items.reduce((acc, it) => acc + (it.total_taxa_entrega || 0), 0);
  const totalCobrado = items.reduce((acc, it) => acc + (it.total_frete_cobrado || 0), 0);
  const totalLiquido = items.reduce((acc, it) => acc + (it.total_frete_liquido || 0), 0);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <LocalShippingIcon color="primary" />
        Frete médio por fonte
      </DialogTitle>
      <DialogContent>
        <Stack direction="row" spacing={2} sx={{ mb: 2, mt: 1, flexWrap: 'wrap' }}>
          <TextField
            type="date"
            label="De"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            size="small"
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <TextField
            type="date"
            label="Até"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            size="small"
            slotProps={{ inputLabel: { shrink: true } }}
          />
        </Stack>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">{error}</Typography>
        ) : items.length === 0 ? (
          <Typography color="text.secondary">
            Nenhum pedido entre {dayjs(start).format('DD/MM/YYYY')} e{' '}
            {dayjs(end).format('DD/MM/YYYY')}.
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Fonte</TableCell>
                  <TableCell align="right">Pedidos</TableCell>
                  <TableCell align="right">Média taxa entrega</TableCell>
                  <TableCell align="right">Média frete cobrado</TableCell>
                  <TableCell align="right">Média frete líquido</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((it) => (
                  <TableRow key={it.fonte}>
                    <TableCell>{it.fonte}</TableCell>
                    <TableCell align="right">{it.total_pedidos}</TableCell>
                    <TableCell align="right">
                      {formatBRL(it.media_taxa_entrega)}{' '}
                      <Typography component="span" variant="caption" color="text.secondary">
                        (n={it.n_taxa_entrega})
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      {formatBRL(it.media_frete_cobrado)}{' '}
                      <Typography component="span" variant="caption" color="text.secondary">
                        (n={it.n_frete_cobrado})
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      {formatBRL(it.media_frete_liquido)}{' '}
                      <Typography component="span" variant="caption" color="text.secondary">
                        (n={it.n_frete_liquido})
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow>
                  <TableCell>
                    <Typography fontWeight="bold">Total</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="bold">{totalPedidos}</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="bold" color="primary.main">
                      {formatBRL(totalTaxa)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="bold" color="primary.main">
                      {formatBRL(totalCobrado)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography fontWeight="bold" color="primary.main">
                      {formatBRL(totalLiquido)}
                    </Typography>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        )}
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
          Período usa a data de entrega (dia_entrega). "n" é a quantidade de pedidos com o campo
          preenchido (médias ignoram valores vazios).
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fechar</Button>
      </DialogActions>
    </Dialog>
  );
}
