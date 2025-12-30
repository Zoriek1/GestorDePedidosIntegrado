/**
 * Order Card component
 */

import { Card, CardContent, Typography, Box, Chip } from '@mui/material';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { formatDateBR } from '../../../lib/format/date';
import { formatBRL } from '../../../lib/format/currency';
import { getStatusColor, getStatusLabel } from '../useCases/orderMapping';

interface OrderCardProps {
  pedido: Pedido;
  onClick?: () => void;
}

export function OrderCard({ pedido, onClick }: OrderCardProps) {
  const statusColor = getStatusColor(pedido.status);
  const statusLabel = getStatusLabel(pedido.status);

  return (
    <Card
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? { boxShadow: 4 } : {},
        transition: 'box-shadow 0.2s',
      }}
      onClick={onClick}
    >
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
          <Box>
            <Typography variant="h6" component="div" gutterBottom>
              {pedido.cliente} → {pedido.destinatario}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {pedido.produto}
            </Typography>
          </Box>
          <Chip
            label={statusLabel}
            color={statusColor}
            size="small"
          />
        </Box>

        <Box display="flex" flexDirection="column" gap={1}>
          <Typography variant="body2">
            <strong>Data:</strong> {formatDateBR(pedido.dia_entrega)} às {pedido.horario}
          </Typography>
          {pedido.tipo_pedido === 'Entrega' && pedido.endereco && (
            <Typography variant="body2" color="text.secondary">
              <strong>Endereço:</strong> {pedido.endereco}
            </Typography>
          )}
          {pedido.valor && (
            <Typography variant="body2">
              <strong>Valor:</strong> {formatBRL(pedido.valor)}
            </Typography>
          )}
          {pedido.distancia_km && (
            <Typography variant="body2" color="text.secondary">
              <strong>Distância:</strong> {pedido.distancia_km.toFixed(2)} km
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

