import { Paper, Typography, Chip, Stack, Box } from '@mui/material';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { calcularValorBrutoPedido } from '../utils/valorEfetivo';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';

dayjs.locale('pt-br');

interface SalesCardProps {
  venda: Pedido;
}

const STATUS_COLORS: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  pago: 'success',
  realizado: 'success',
  parcial: 'warning',
  pendente: 'default',
};

export function SalesCard({ venda }: SalesCardProps) {
  const valorBruto = calcularValorBrutoPedido(venda);

  const formatMoney = (value: number) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);

  const statusKey = venda.status_pagamento?.toLowerCase().trim() || '';
  const chipColor = STATUS_COLORS[statusKey] ?? 'default';

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Typography variant="subtitle2" fontWeight="bold" noWrap sx={{ flex: 1, mr: 1 }}>
            {venda.cliente}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {dayjs(venda.created_at).format('DD/MM')}
          </Typography>
        </Box>

        {venda.destinatario !== venda.cliente && (
          <Chip
            label={`→ ${venda.destinatario}`}
            size="small"
            variant="outlined"
            sx={{ width: 'fit-content', fontSize: '0.7rem', height: 20 }}
          />
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body2" fontWeight="bold">
            {formatMoney(valorBruto)}
          </Typography>
          {statusKey && (
            <Chip
              label={venda.status_pagamento}
              size="small"
              color={chipColor}
              variant="outlined"
            />
          )}
        </Box>
      </Stack>
    </Paper>
  );
}
