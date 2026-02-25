import { Box, Paper, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { agruparPorHora } from '../utils/salesAnalytics';

interface SalesByHourChartProps {
  vendas: Pedido[];
}

export function SalesByHourChart({ vendas }: SalesByHourChartProps) {
  const data = agruparPorHora(vendas);

  if (data.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Vendas por Hora
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Sem dados para exibir
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Vendas por Hora
      </Typography>
      <Box sx={{ width: '100%', height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'valor') {
                  return [
                    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value),
                    'Valor',
                  ];
                }
                return [value, 'Quantidade'];
              }}
            />
            <Bar dataKey="quantidade" fill="#22c55e" name="Quantidade" />
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
}
