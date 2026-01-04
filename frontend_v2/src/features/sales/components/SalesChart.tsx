/**
 * Sales Chart Component
 * Gráfico de barras mostrando vendas por dia
 */

import { useMemo } from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import dayjs from 'dayjs';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { calcularValorBrutoPedido } from '../utils/valorEfetivo';

export interface SalesChartProps {
  vendas: Pedido[];
  startDate: string;
  endDate: string;
}

export function SalesChart({ vendas, startDate, endDate }: SalesChartProps) {
  const chartData = useMemo(() => {
    const start = dayjs(startDate);
    const end = dayjs(endDate);
    const days: Record<string, { date: string; valor: number; quantidade: number }> = {};

    // Inicializar todos os dias do período
    let current = start;
    while (current.isBefore(end) || current.isSame(end, 'day')) {
      const dateKey = current.format('YYYY-MM-DD');
      days[dateKey] = {
        date: current.format('DD/MM'),
        valor: 0,
        quantidade: 0,
      };
      current = current.add(1, 'day');
    }

    // Agregar vendas por dia
    vendas.forEach((venda) => {
      const vendaDate = dayjs(venda.created_at || venda.dia_entrega);
      const dateKey = vendaDate.format('YYYY-MM-DD');
      
      if (days[dateKey]) {
        days[dateKey].valor += calcularValorBrutoPedido(venda);
        days[dateKey].quantidade += 1;
      }
    });

    return Object.values(days).sort((a, b) => {
      const dateA = dayjs(a.date, 'DD/MM');
      const dateB = dayjs(b.date, 'DD/MM');
      return dateA.isBefore(dateB) ? -1 : 1;
    });
  }, [vendas, startDate, endDate]);

  if (chartData.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Nenhum dado para exibir no gráfico
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Vendas por Dia
      </Typography>
      <Box sx={{ width: '100%', height: 300, mt: 2, minWidth: 0, minHeight: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis yAxisId="left" orientation="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip
              formatter={(value: number | undefined, name: string | undefined) => {
                // O name vem do prop 'name' do Bar component
                // A barra roxa tem name="Valor (R$)" e a verde tem name="Quantidade"
                const numValue = typeof value === 'number' ? value : parseFloat(String(value || 0));
                const safeValue = isNaN(numValue) ? 0 : numValue;
                
                // Verificar se é a barra de valor (roxo) - contém "Valor" ou "R$"
                if (name && (name.includes('Valor') || name.includes('R$') || name === 'valor')) {
                  return [`R$ ${safeValue.toFixed(2).replace('.', ',')}`, 'Valor'];
                }
                
                // Caso contrário, é quantidade
                return [safeValue, 'Quantidade'];
              }}
            />
            <Legend />
            <Bar yAxisId="left" dataKey="valor" fill="#8884d8" name="Valor (R$)" />
            <Bar yAxisId="right" dataKey="quantidade" fill="#82ca9d" name="Quantidade" />
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
}
