import { Box, Paper, Typography, Stack } from '@mui/material';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { agruparPorProduto } from '../utils/salesAnalytics';

interface SalesTopProductsProps {
  vendas: Pedido[];
}

export function SalesTopProducts({ vendas }: SalesTopProductsProps) {
  const ranking = agruparPorProduto(vendas).slice(0, 5);

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Top 5 Produtos
      </Typography>
      {ranking.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          Sem dados para exibir
        </Typography>
      ) : (
        <Stack spacing={1.5} sx={{ mt: 1 }}>
          {ranking.map((item, index) => (
            <Box key={`${item.produto}-${index}`} sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2">
                {index + 1}. {item.produto}
              </Typography>
              <Typography variant="body2" fontWeight={600}>
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.total)}
              </Typography>
            </Box>
          ))}
        </Stack>
      )}
    </Paper>
  );
}
