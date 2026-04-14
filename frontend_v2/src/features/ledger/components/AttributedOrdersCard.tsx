import {
  Box,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Skeleton,
  Alert,
} from '@mui/material';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import { usePedidosAtribuidos } from '../services/ledgerApi';

const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

interface Props {
  userId: number;
  from?: string;
  to?: string;
}

export function AttributedOrdersCard({ userId, from, to }: Props) {
  const { data, isLoading, isError } = usePedidosAtribuidos({ user_id: userId, from, to });

  if (isLoading) {
    return (
      <Box>
        <Skeleton variant="rectangular" height={40} sx={{ mb: 1 }} />
        <Skeleton variant="rectangular" height={120} />
      </Box>
    );
  }

  if (isError) {
    return <Alert severity="error">Erro ao carregar pedidos atribuídos.</Alert>;
  }

  if (!data || data.length === 0) {
    return (
      <Box
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          p: 2,
          textAlign: 'center',
        }}
      >
        <ReceiptLongIcon sx={{ fontSize: 36, color: 'text.disabled', mb: 1 }} />
        <Typography variant="body2" color="text.secondary">
          Nenhum pedido atribuído encontrado.
        </Typography>
      </Box>
    );
  }

  const totalComissao = data.reduce((acc, p) => acc + p.commission_amount, 0);

  return (
    <Box>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1.5}>
        <Box display="flex" alignItems="center" gap={1}>
          <ReceiptLongIcon fontSize="small" color="action" />
          <Typography variant="subtitle2" fontWeight={600}>
            Pedidos Atribuídos
          </Typography>
          <Chip label={data.length} size="small" />
        </Box>
        <Typography variant="body2" fontWeight={700} color="success.main">
          {BRL.format(totalComissao)}
        </Typography>
      </Box>

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: 'grey.50' }}>
              <TableCell sx={{ fontWeight: 600, fontSize: 12 }}>Pedido</TableCell>
              <TableCell sx={{ fontWeight: 600, fontSize: 12 }}>Pgt. Previsto</TableCell>
              <TableCell sx={{ fontWeight: 600, fontSize: 12 }} align="right">
                Valor Pedido
              </TableCell>
              <TableCell sx={{ fontWeight: 600, fontSize: 12 }}>Fonte / Taxa</TableCell>
              <TableCell sx={{ fontWeight: 600, fontSize: 12 }} align="right">
                Comissão
              </TableCell>
              <TableCell sx={{ fontWeight: 600, fontSize: 12 }}>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((p) => (
              <TableRow
                key={p.entry_id}
                sx={{ '&:last-child td': { border: 0 } }}
              >
                <TableCell>
                  <Typography variant="body2" fontWeight={500} noWrap>
                    {p.cliente}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    #{p.pedido_id} · {fmtDate(p.dia_entrega)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">{fmtDate(p.due_date)}</Typography>
                  {p.week_ref && (
                    <Typography variant="caption" color="text.secondary">
                      sem. {fmtDate(p.week_ref)}
                    </Typography>
                  )}
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2">
                    {p.valor_pedido != null ? BRL.format(p.valor_pedido) : '—'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" textTransform="capitalize">
                    {p.fonte || '—'}
                  </Typography>
                  {p.rate != null && (
                    <Typography variant="caption" color="text.secondary">
                      {p.rate}%
                    </Typography>
                  )}
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" fontWeight={600} color="success.dark">
                    {BRL.format(p.commission_amount)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={p.status === 'confirmado' ? 'Confirmado' : 'Pendente'}
                    size="small"
                    color={p.status === 'confirmado' ? 'success' : 'warning'}
                    variant="outlined"
                    sx={{ fontSize: 11 }}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
