import { useCallback, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Box, Typography, Stack, TextField, Grid, useMediaQuery, useTheme } from '@mui/material';
import { SalesCard } from './components/SalesCard';
import { usePedidos } from '../../api/endpoints/pedidos';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { SalesKPIGrid } from './components/SalesKPIGrid';
import { SalesTable } from './components/SalesTable';
import { SalesPeriodFilter } from './components/SalesPeriodFilter';
import { SalesChart } from './components/SalesChart';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { SalesChannelDonut } from './components/SalesChannelDonut';
import { SalesByHourChart } from './components/SalesByHourChart';
import { SalesTopProducts } from './components/SalesTopProducts';
import { SalesMetaProgress } from './components/SalesMetaProgress';
import { calcularTotais } from './utils/salesAnalytics';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';

// Configurar locale pt-br para dayjs
dayjs.locale('pt-br');

export default function SalesPage() {
  // Calcular primeiro e último dia do mês atual (inclusive)
  // Backend vai adicionar 1 dia ao último dia para tornar fim_exclusivo
  const now = dayjs();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [searchParams, setSearchParams] = useSearchParams();

  const [compareEnabled, setCompareEnabled] = useState(false);
  const [compareStartDate, setCompareStartDate] = useState(
    now.subtract(1, 'month').startOf('month').format('YYYY-MM-DD')
  );
  const [compareEndDate, setCompareEndDate] = useState(
    now.subtract(1, 'month').endOf('month').format('YYYY-MM-DD')
  );

  const [searchValue, setSearchValue] = useState('');
  const debouncedSearch = useDebouncedValue(searchValue, 400);

  const { data, isLoading, error, refetch } = usePedidos({
    data_inicio: startDate,
    data_fim: endDate, // Último dia do mês (inclusive) - backend adiciona 1 dia para tornar exclusivo
    search: debouncedSearch || undefined,
    filtrar_por_criacao: true, // Filtrar por created_at
  });

  // Período é o mês atual inteiro (parcial até hoje)? Reusado na projeção e no comparativo.
  const isMesAtual = useMemo(() => {
    const start = dayjs(startDate);
    const end = dayjs(endDate);
    return start.isSame(now.startOf('month'), 'day') && end.isSame(now.endOf('month'), 'day');
  }, [startDate, endDate, now]);

  const prevStartDate = useMemo(
    () => dayjs(startDate).subtract(1, 'month').format('YYYY-MM-DD'),
    [startDate]
  );
  // Quando o período é o mês atual (parcial), limita a janela anterior ao mesmo intervalo de
  // dias (MTD): dia 1 do mês anterior até o mesmo dia-do-mês de hoje — evita comparar um mês
  // parcial contra um mês cheio (#15).
  const prevEndDate = useMemo(() => {
    if (isMesAtual) {
      const prevMonthStart = dayjs(startDate).subtract(1, 'month').startOf('month');
      const dia = Math.min(now.date(), prevMonthStart.daysInMonth());
      return prevMonthStart.date(dia).format('YYYY-MM-DD');
    }
    return dayjs(endDate).subtract(1, 'month').format('YYYY-MM-DD');
  }, [startDate, endDate, isMesAtual, now]);

  const { data: previousData } = usePedidos(
    {
      data_inicio: prevStartDate,
      data_fim: prevEndDate,
      search: debouncedSearch || undefined,
      filtrar_por_criacao: true,
    },
    { enabled: true }
  );

  const { data: compareData } = usePedidos(
    {
      data_inicio: compareStartDate,
      data_fim: compareEndDate,
      search: debouncedSearch || undefined,
      filtrar_por_criacao: true,
    },
    { enabled: compareEnabled }
  );

  // Filtrar cancelados e soft-deleted (defensivo para contagem de vendas)
  const vendas = useMemo(() => {
    const pedidos = data?.pedidos || [];
    return pedidos.filter(
      (p) => p.status?.toLowerCase().trim() !== 'cancelado' && !p.deleted_at
    );
  }, [data?.pedidos]);

  const vendasAnterior = useMemo(() => {
    const pedidos = previousData?.pedidos || [];
    return pedidos.filter(
      (p) => p.status?.toLowerCase().trim() !== 'cancelado' && !p.deleted_at
    );
  }, [previousData?.pedidos]);

  const vendasComparacao = useMemo(() => {
    if (!compareEnabled) return [];
    const pedidos = compareData?.pedidos || [];
    return pedidos.filter(
      (p) => p.status?.toLowerCase().trim() !== 'cancelado' && !p.deleted_at
    );
  }, [compareEnabled, compareData?.pedidos]);

  const baseTotals = useMemo(() => calcularTotais(vendas), [vendas]);

  const projecaoFaturamento = useMemo(() => {
    if (!isMesAtual) return undefined;
    const start = dayjs(startDate);
    const diasNoMes = now.daysInMonth();
    const diasDecorridos = Math.min(now.diff(start, 'day') + 1, diasNoMes);
    if (diasDecorridos <= 0) return undefined;
    const mediaDiaria = baseTotals.totalVendasBruto / diasDecorridos;
    return mediaDiaria * diasNoMes;
  }, [baseTotals.totalVendasBruto, startDate, isMesAtual, now]);

  const kpis = useMemo(() => ({
    ...baseTotals,
    projecaoFaturamento,
  }), [baseTotals, projecaoFaturamento]);

  const comparativoLabel = useMemo(
    () => `${dayjs(prevStartDate).format('MMM')}${isMesAtual ? ' (parcial)' : ''}`,
    [prevStartDate, isMesAtual]
  );
  const comparativo = useMemo(() => {
    const prevTotals = calcularTotais(vendasAnterior);
    const calcPct = (atual: number, anterior: number) => {
      if (!anterior || Number.isNaN(anterior)) return null;
      return ((atual - anterior) / anterior) * 100;
    };
    return {
      quantidade: calcPct(baseTotals.quantidade, prevTotals.quantidade),
      totalVendasBruto: calcPct(baseTotals.totalVendasBruto, prevTotals.totalVendasBruto),
      totalRecebido: calcPct(baseTotals.totalRecebido, prevTotals.totalRecebido),
      totalEfetivo: calcPct(baseTotals.totalEfetivo, prevTotals.totalEfetivo),
      ticketMedioEfetivo: calcPct(baseTotals.ticketMedioEfetivo, prevTotals.ticketMedioEfetivo),
      projecaoFaturamento: projecaoFaturamento !== undefined ? calcPct(projecaoFaturamento, prevTotals.totalVendasBruto) : null,
    };
  }, [vendasAnterior, baseTotals, projecaoFaturamento]);

  // Formatar período em português
  const periodoFormatado = useMemo(() => {
    const start = dayjs(startDate);
    const end = dayjs(endDate);
    if (start.month() === end.month() && start.year() === end.year()) {
      return start.format('MMMM [de] YYYY');
    }
    return `${start.format('DD/MM/YYYY')} - ${end.format('DD/MM/YYYY')}`;
  }, [startDate, endDate]);

  return (
    <Box>
      <Stack 
        direction={{ xs: 'column', md: 'row' }} 
        alignItems={{ xs: 'flex-start', md: 'center' }} 
        justifyContent="space-between" 
        gap={2} 
        mb={2}
      >
        <Typography variant="h4" component="h1">
          Vendas - {periodoFormatado}
        </Typography>
        <TextField
          size="small"
          placeholder="Buscar por cliente, destinatário ou produto"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
        />
      </Stack>

      <Box sx={{ mb: 3 }}>
        <SalesPeriodFilter
          startDate={startDate}
          endDate={endDate}
          compareEnabled={compareEnabled}
          compareStartDate={compareStartDate}
          compareEndDate={compareEndDate}
          onChange={(start, end) => {
            setStartDate(start);
            setEndDate(end);
          }}
          onCompareToggle={(enabled) => setCompareEnabled(enabled)}
          onCompareChange={(start, end) => {
            setCompareStartDate(start);
            setCompareEndDate(end);
          }}
        />
      </Box>

      {isLoading ? (
        <Loading variant="skeleton" count={3} />
      ) : error ? (
        <ErrorState message="Erro ao carregar vendas" onRetry={() => refetch()} />
      ) : (
        <>
          <SalesKPIGrid kpis={kpis} comparativo={comparativo} comparativoLabel={comparativoLabel} />
          <SalesMetaProgress startDate={startDate} totalBruto={kpis.totalVendasBruto} />
          <SalesChart
            vendas={vendas}
            startDate={startDate}
            endDate={endDate}
            compareVendas={compareEnabled ? vendasComparacao : undefined}
            compareStartDate={compareEnabled ? compareStartDate : undefined}
            compareEndDate={compareEnabled ? compareEndDate : undefined}
            compareLabel={compareEnabled ? 'Período comparado' : undefined}
          />
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid size={{ xs: 12, md: 6 }} sx={{ minWidth: 0 }}>
              <SalesChannelDonut vendas={vendas} />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }} sx={{ minWidth: 0 }}>
              <SalesTopProducts vendas={vendas} />
            </Grid>
            <Grid size={{ xs: 12 }} sx={{ minWidth: 0 }}>
              <SalesByHourChart vendas={vendas} />
            </Grid>
          </Grid>
          {isMobile ? (
            <Grid container spacing={1.5}>
              {vendas.length === 0 ? (
                <Grid size={12}>
                  <Typography variant="body2" color="text.secondary" textAlign="center" py={4}>
                    Nenhuma venda encontrada para este mês
                  </Typography>
                </Grid>
              ) : (
                vendas.map((venda) => (
                  <Grid size={{ xs: 12, sm: 6 }} key={venda.id}>
                    <SalesCard venda={venda} />
                  </Grid>
                ))
              )}
            </Grid>
          ) : (
            <SalesTable vendas={vendas} />
          )}
        </>
      )}
    </Box>
  );
}
