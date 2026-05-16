/**
 * Sales Chart Component
 * Gráfico de barras mostrando vendas por dia
 */

import { useMemo } from 'react';
import { Box, Paper, Typography, useMediaQuery, useTheme } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { agruparPorDia } from '../utils/salesAnalytics';

export interface SalesChartProps {
  vendas: Pedido[];
  startDate: string;
  endDate: string;
  compareVendas?: Pedido[];
  compareStartDate?: string;
  compareEndDate?: string;
  compareLabel?: string;
}

export function SalesChart({
  vendas,
  startDate,
  endDate,
  compareVendas,
  compareStartDate,
  compareEndDate,
  compareLabel = 'Período comparado',
}: SalesChartProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const isCompareMode = Boolean(compareVendas && compareStartDate && compareEndDate);

  const chartData = useMemo(() => {
    if (!isCompareMode) {
      return agruparPorDia(vendas, startDate, endDate).map((item) => ({
        label: item.label,
        valor: item.valor,
        quantidade: item.quantidade,
      }));
    }

    const serieA = agruparPorDia(vendas, startDate, endDate);
    const serieB = agruparPorDia(compareVendas || [], compareStartDate as string, compareEndDate as string);
    const maxLen = Math.max(serieA.length, serieB.length);

    return Array.from({ length: maxLen }).map((_, idx) => ({
      label: `D${idx + 1}`,
      valor: serieA[idx]?.valor || 0,
      quantidade: serieA[idx]?.quantidade || 0,
      valorComparado: serieB[idx]?.valor || 0,
      quantidadeComparado: serieB[idx]?.quantidade || 0,
    }));
  }, [vendas, startDate, endDate, compareVendas, compareStartDate, compareEndDate, isCompareMode]);

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
          <BarChart data={chartData} layout={isMobile ? 'vertical' : 'horizontal'}>
            <CartesianGrid strokeDasharray="3 3" />
            {isMobile ? (
              <>
                <XAxis type="number" />
                <YAxis type="category" dataKey="label" width={60} />
              </>
            ) : (
              <>
                <XAxis dataKey="label" />
                <YAxis yAxisId="left" orientation="left" />
                {!isCompareMode && <YAxis yAxisId="right" orientation="right" />}
              </>
            )}
            <Tooltip
              formatter={(value: number | undefined, name: string | undefined) => {
                // O name vem do prop 'name' do Bar component
                const numValue = typeof value === 'number' ? value : parseFloat(String(value || 0));
                const safeValue = isNaN(numValue) ? 0 : numValue;

                if (name && (name.includes('Valor') || name.includes('R$') || name.includes('Período'))) {
                  return [`R$ ${safeValue.toFixed(2).replace('.', ',')}`, name];
                }

                return [safeValue, name || 'Quantidade'];
              }}
            />
            <Legend />
            {isCompareMode ? (
              <>
                <Bar yAxisId={isMobile ? undefined : 'left'} dataKey="valor" fill="#8884d8" name="Período atual" />
                <Bar yAxisId={isMobile ? undefined : 'left'} dataKey="valorComparado" fill="#82ca9d" name={compareLabel} />
              </>
            ) : (
              <>
                <Bar yAxisId={isMobile ? undefined : 'left'} dataKey="valor" fill="#8884d8" name="Valor (R$)" />
                {!isMobile && <Bar yAxisId="right" dataKey="quantidade" fill="#82ca9d" name="Quantidade" />}
              </>
            )}
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
}
