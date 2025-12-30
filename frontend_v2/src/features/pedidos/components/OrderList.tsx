/**
 * Order List component
 */

import { Grid, Box, Typography } from '@mui/material';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { OrderCard } from './OrderCard';

interface OrderListProps {
  pedidos: Pedido[];
  onOrderClick?: (pedido: Pedido) => void;
}

export function OrderList({ pedidos, onOrderClick }: OrderListProps) {
  if (pedidos.length === 0) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="200px"
        p={3}
      >
        <Typography variant="body1" color="text.secondary">
          Nenhum pedido encontrado
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container spacing={2}>
      {pedidos.map((pedido) => (
        <Grid size={{ xs: 12, sm: 6, md: 4 }} key={pedido.id}>
          <OrderCard
            pedido={pedido}
            onClick={onOrderClick ? () => onOrderClick(pedido) : undefined}
          />
        </Grid>
      ))}
    </Grid>
  );
}

