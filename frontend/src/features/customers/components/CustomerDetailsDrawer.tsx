import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Stack,
  Divider,
  Chip,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import type { Customer } from '../../../api/endpoints/customers';
import type { CustomerBadge } from '../services/ICustomerInsightsService';
import { formatBRL } from '../../../lib/format/currency';

interface CustomerDetailsDrawerProps {
  open: boolean;
  customer?: Customer | null;
  orders?: Array<{ id: number; numero_pedido?: number | null; created_at?: string; dia_entrega?: string; horario?: string; status?: string; valor?: string }>;
  badges?: CustomerBadge[];
  onClose: () => void;
}

export function CustomerDetailsDrawer({ open, customer, orders, badges, onClose }: CustomerDetailsDrawerProps) {
  if (!customer) return null;

  const formatDate = (iso?: string) =>
    iso ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(new Date(iso)) : '—';

  return (
    <Drawer anchor="right" open={open} onClose={onClose}>
      <Box sx={{ width: 360, p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">Cliente</Typography>
          <IconButton onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Stack>

        <Box>
          <Typography variant="subtitle1" fontWeight="bold">
            {customer.nome}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Telefone: {customer.telefone || '—'}
          </Typography>
          {customer.email && (
            <Typography variant="body2" color="text.secondary">
              Email: {customer.email}
            </Typography>
          )}
          {badges && badges.length > 0 && (
            <Stack direction="row" spacing={1} mt={1} flexWrap="wrap">
              {badges.map((b) => (
                <Chip key={b.label} label={b.label} size="small" color={b.color} variant="outlined" />
              ))}
            </Stack>
          )}
        </Box>

        <Divider />

        <Stack spacing={0.5}>
          <Typography variant="subtitle2">Indicadores</Typography>
          <Typography variant="body2">LTV: {formatBRL(customer.ltv || 0)}</Typography>
          <Typography variant="body2">Total de pedidos: {customer.total_pedidos ?? 0}</Typography>
          <Typography variant="body2">
            Último pedido: {customer.ultimo_pedido ? formatDate(customer.ultimo_pedido) : '—'}
          </Typography>
        </Stack>

        <Divider />

        <Stack spacing={1}>
          <Typography variant="subtitle2">Histórico de pedidos</Typography>
          <Stack spacing={1} sx={{ maxHeight: 300, overflow: 'auto' }}>
            {(orders || []).map((o) => (
              <Box key={o.id} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1 }}>
                <Typography variant="body2" fontWeight="bold">
                  Pedido #{o.numero_pedido ?? o.id}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Data: {o.dia_entrega || formatDate(o.created_at)} {o.horario || ''}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Status: {o.status || '—'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Valor: {formatBRL(o.valor || 0)}
                </Typography>
              </Box>
            ))}
            {(!orders || orders.length === 0) && (
              <Typography variant="body2" color="text.secondary">
                Nenhum pedido encontrado.
              </Typography>
            )}
          </Stack>
        </Stack>
      </Box>
    </Drawer>
  );
}
