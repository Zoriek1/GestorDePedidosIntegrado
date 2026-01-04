import { useMemo, useState } from 'react';
import { Box, Typography, Stack, TextField } from '@mui/material';
import { usePedidos } from '../../api/endpoints/pedidos';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { SalesKPIGrid } from './components/SalesKPIGrid';
import { SalesTable } from './components/SalesTable';
import { SalesPeriodFilter } from './components/SalesPeriodFilter';
import { SalesChart } from './components/SalesChart';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { 
  calcularValorBrutoPedido, 
  calcularValorRecebidoPedido, 
  calcularValorEfetivoComFrete 
} from './utils/valorEfetivo';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';

// Configurar locale pt-br para dayjs
dayjs.locale('pt-br');

export default function SalesPage() {
  // Calcular primeiro e último dia do mês atual (inclusive)
  // Backend vai adicionar 1 dia ao último dia para tornar fim_exclusivo
  const now = dayjs();
  const [startDate, setStartDate] = useState(now.startOf('month').format('YYYY-MM-DD'));
  const [endDate, setEndDate] = useState(now.endOf('month').format('YYYY-MM-DD'));

  const [searchValue, setSearchValue] = useState('');
  const debouncedSearch = useDebouncedValue(searchValue, 400);

  const { data, isLoading, error, refetch } = usePedidos({
    data_inicio: startDate,
    data_fim: endDate, // Último dia do mês (inclusive) - backend adiciona 1 dia para tornar exclusivo
    search: debouncedSearch || undefined,
    filtrar_por_criacao: true, // Filtrar por created_at
  });

  // Filtrar cancelados no frontend (defensivo) e alertar se backend retornou cancelados
  const vendas = useMemo(() => {
    const pedidos = data?.pedidos || [];
    const cancelados = pedidos.filter((p) => p.status?.toLowerCase().trim() === 'cancelado');
    
    // Alertar se backend retornou cancelados (indica bug no filtro server-side)
    if (cancelados.length > 0) {
      console.warn(
        `[VENDAS] Backend retornou ${cancelados.length} pedido(s) cancelado(s). ` +
        `Isso indica um bug no filtro server-side. IDs: ${cancelados.map(p => p.id).join(', ')}`
      );
    }
    
    return pedidos.filter((p) => p.status?.toLowerCase().trim() !== 'cancelado');
  }, [data?.pedidos]);

  // Calcular KPIs usando helper centralizado
  const kpis = useMemo(() => {
    const quantidade = vendas.length;
    
    // Total de vendas no mês (bruto - soma de todos os valores)
    const totalVendasBruto = vendas.reduce((sum, venda) => {
      return sum + calcularValorBrutoPedido(venda);
    }, 0);
    
    // Total recebido (considera status de pagamento: parcial=50%, pendente=0%, realizado=100%)
    const totalRecebido = vendas.reduce((sum, venda) => {
      return sum + calcularValorRecebidoPedido(venda);
    }, 0);
    
    // Total efetivo (valor bruto - frete)
    const totalEfetivo = vendas.reduce((sum, venda) => {
      return sum + calcularValorEfetivoComFrete(venda);
    }, 0);

    return {
      quantidade,
      totalVendasBruto,
      totalRecebido,
      totalEfetivo,
    };
  }, [vendas]);

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
          onChange={(start, end) => {
            setStartDate(start);
            setEndDate(end);
          }}
        />
      </Box>

      {isLoading ? (
        <Loading variant="skeleton" count={3} />
      ) : error ? (
        <ErrorState message="Erro ao carregar vendas" onRetry={() => refetch()} />
      ) : (
        <>
          <SalesKPIGrid kpis={kpis} />
          <SalesChart vendas={vendas} startDate={startDate} endDate={endDate} />
          <SalesTable vendas={vendas} />
        </>
      )}
    </Box>
  );
}
