import { Box, Paper, Typography, useTheme } from '@mui/material';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { agruparPorCanal } from '../utils/salesAnalytics';

const LIGHT_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#a855f7'];
const DARK_COLORS = ['#818cf8', '#4ade80', '#fbbf24', '#f87171', '#22d3ee', '#c084fc'];

interface SalesChannelDonutProps {
  vendas: Pedido[];
}

export function SalesChannelDonut({ vendas }: SalesChannelDonutProps) {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const COLORS = isDark ? DARK_COLORS : LIGHT_COLORS;

  const data = agruparPorCanal(vendas).map((item) => ({
    name: item.canal,
    value: item.total,
  }));

  if (data.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Performance por Canal
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
        Performance por Canal
      </Typography>
      <Box sx={{ width: '100%', height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={2}
              label={({ name, percent }) => `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) =>
                new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value))
              }
              contentStyle={{
                backgroundColor: theme.palette.background.paper,
                color: theme.palette.text.primary,
                border: `1px solid ${theme.palette.divider}`,
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
}
