import { useState, useEffect } from 'react';
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
} from '@mui/material';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import dayjs from 'dayjs';
import { createApiRequest } from '../../../api/http';
import { useAuth } from '../../auth/authStore';

interface FreightItem {
  id: number;
  cliente: string;
  endereco: string;
  taxa_entrega: number;
  status: string;
}

interface DailyFreightDialogProps {
  open: boolean;
  onClose: () => void;
}

const formatBRL = (v: number) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);

export function DailyFreightDialog({ open, onClose }: DailyFreightDialogProps) {
  const { getAuthHeader } = useAuth();
  const [date, setDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [items, setItems] = useState<FreightItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    fetchData(date);
  }, [open, date]);

  const fetchData = async (d: string) => {
    setLoading(true);
    setError('');
    try {
      const apiRequest = createApiRequest(getAuthHeader);
      const res = await apiRequest<{
        items: FreightItem[];
        total: number;
      }>(`/pedidos/daily-freight?date=${d}`);
      if (!res.ok) throw new Error('Erro ao buscar dados');
      setItems(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao buscar dados');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <LocalShippingIcon color="primary" />
        Frete do Dia
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2, mt: 1 }}>
          <TextField
            type="date"
            label="Data"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            size="small"
            slotProps={{ inputLabel: { shrink: true } }}
          />
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">{error}</Typography>
        ) : items.length === 0 ? (
          <Typography color="text.secondary">
            Nenhuma entrega para {dayjs(date).format('DD/MM/YYYY')}.
          </Typography>
        ) : (
          <>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>#</TableCell>
                    <TableCell>Cliente</TableCell>
                    <TableCell>Endereço</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Taxa</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>{item.id}</TableCell>
                      <TableCell>{item.cliente || '-'}</TableCell>
                      <TableCell sx={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.endereco || '-'}
                      </TableCell>
                      <TableCell>{item.status}</TableCell>
                      <TableCell align="right">{formatBRL(item.taxa_entrega)}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow>
                    <TableCell colSpan={4}>
                      <Typography fontWeight="bold">
                        Total ({items.length} entregas)
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography fontWeight="bold" color="primary.main">
                        {formatBRL(total)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fechar</Button>
      </DialogActions>
    </Dialog>
  );
}
