/**
 * Order Card component
 */

import { Card, CardContent, Typography, Box, Chip } from '@mui/material';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale/pt-BR';

interface OrderCardProps {
  pedido: Pedido;
  onClick?: () => void;
}

const statusColors: Record<string, 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'> = {
  agendado: 'info',
  producao: 'warning',
  pronto: 'success',
  entregue: 'secondary',
  cancelado: 'error',
  concluido: 'secondary',
};

const statusLabels: Record<string, string> = {
  agendado: 'Agendado',
  producao: 'Em Produção',
  pronto: 'Pronto',
  entregue: 'Entregue',
  cancelado: 'Cancelado',
  concluido: 'Concluído',
};

export function OrderCard({ pedido, onClick }: OrderCardProps) {
  const statusColor = statusColors[pedido.status] || 'default';
  const statusLabel = statusLabels[pedido.status] || pedido.status;

  const formatDate = (dateStr: string) => {
    try {
      return format(new Date(dateStr), "dd/MM/yyyy", { locale: ptBR });
    } catch {
      return dateStr;
    }
  };

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
            <strong>Data:</strong> {formatDate(pedido.dia_entrega)} às {pedido.horario}
          </Typography>
          {pedido.tipo_pedido === 'Entrega' && pedido.endereco && (
            <Typography variant="body2" color="text.secondary">
              <strong>Endereço:</strong> {pedido.endereco}
            </Typography>
          )}
          {pedido.valor && (
            <Typography variant="body2">
              <strong>Valor:</strong> R$ {pedido.valor}
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

