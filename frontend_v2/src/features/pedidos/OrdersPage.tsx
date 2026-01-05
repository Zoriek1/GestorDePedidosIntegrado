/**
 * Orders Page - Main orders list view
 */

import { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Button,
  Stack,
  Chip,
  Menu,
  MenuItem,
  Divider,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { Refresh, Folder, DeleteSweep, Sort, FileDownload, FilterList, Route } from '@mui/icons-material';
import { useQueryClient } from '@tanstack/react-query';
import { usePedidos, useCalcularDistanciasLote, useOcultarPedidosConcluidos } from '../../api/endpoints/pedidos';
import type { PedidosFilters } from '../../api/endpoints/pedidos';
import { useStats } from '../../api/endpoints/stats';
import { OrderList } from './components/OrderList';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { createApiRequest } from '../../api/http';
import { useAuth } from '../auth/authStore';
import { useToast } from '../../components/system/useToast';
import { useConfirm } from '../../components/system/useConfirm';
import { OrdersKPIGrid } from './components/OrdersKPIGrid';
import { OrdersFilterToolbar } from './components/OrdersFilterToolbar';
import { OrdersSorting } from './components/OrdersSorting';
import { OrdersPagination } from './components/OrdersPagination';

export default function OrdersPage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  const [filters, setFilters] = useState<PedidosFilters>({
    status: '',
    search: '',
    sort_by: 'dia_entrega',
    sort_order: 'asc',
    page: 1,
    per_page: 20,
  });
  const [sortByDistance, setSortByDistance] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [filterMenuAnchor, setFilterMenuAnchor] = useState<null | HTMLElement>(null);

  const queryClient = useQueryClient();
  const { getAuthHeader, getUserRole } = useAuth();
  const { success, error: showError, info } = useToast();
  const confirm = useConfirm();
  
  const userRole = getUserRole() || 'admin'; // Default para admin se não especificado
  const isAdmin = userRole === 'admin';
  const isEntregador = userRole === 'entregador';
  
  // Entregadores só podem ver pedidos agendados e em rota
  const adjustedFilters = isEntregador 
    ? { ...filters, statuses: ['agendado', 'em_rota'] }
    : filters;
  
  const { data: pedidosData, isLoading: isLoadingPedidos, isFetching: isFetchingPedidos, error: pedidosError, refetch: refetchPedidos } = usePedidos(adjustedFilters);
  const { data: statsData, isFetching: isFetchingStats } = useStats();
  const calcDistanciasLote = useCalcularDistanciasLote();
  const ocultarConcluidos = useOcultarPedidosConcluidos();

  const isFetching = isFetchingPedidos || isFetchingStats;

  const handleRefresh = () => {
    // Use exact: false to invalidate all query variations (including filtered ones)
    queryClient.invalidateQueries({ queryKey: ['pedidos'], exact: false });
    queryClient.invalidateQueries({ queryKey: ['stats'], exact: false });
  };

  // Auto refresh a cada 30s (paridade com legado)
  useEffect(() => {
    const interval = setInterval(() => handleRefresh(), 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleOrderClick = () => {
    // TODO: Navigate to order details
    // Log removido em produção
  };

  const visiblePedidos = useMemo(() => {
    // Type guard: ensure pedidosData is an object with pedidos property
    if (!pedidosData || typeof pedidosData !== 'object' || !('pedidos' in pedidosData) || !Array.isArray(pedidosData.pedidos)) {
      return [];
    }
    const status = filters.status;
    // Ocultar pedidos concluídos por padrão (quando status é undefined, vazio ou 'todos')
    // Isso corresponde ao comportamento do frontend V1
    if (!status || status === 'todos') {
      return pedidosData.pedidos.filter((p) => p.status !== 'concluido');
    }
    if (status === 'concluido') {
      return pedidosData.pedidos.filter((p) => p.status === 'concluido');
    }
    if (status === 'pronto_entrega') {
      return pedidosData.pedidos.filter((p) => p.status === 'pronto_entrega');
    }
    if (status === 'pronto_retirada') {
      return pedidosData.pedidos.filter((p) => p.status === 'pronto_retirada');
    }
    // Para outros status, mostrar todos (exceto concluídos, mantendo consistência)
    return pedidosData.pedidos.filter((p) => p.status !== 'concluido');
  }, [pedidosData, filters.status]);

  const sortedPedidos = useMemo(() => {
    if (!visiblePedidos) return [];
    if (!sortByDistance) return visiblePedidos;
    return [...visiblePedidos].sort((a, b) => {
      const da = a.distancia_km ?? Number.MAX_VALUE;
      const db = b.distancia_km ?? Number.MAX_VALUE;
      return da - db;
    });
  }, [visiblePedidos, sortByDistance]);

  const handleExportSheet = async () => {
    try {
      const apiRequest = createApiRequest(getAuthHeader);
      info('Exportando planilha...');
      const response = await apiRequest<{ success: boolean; message?: string }>('/exportar-planilha', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!response.ok) throw new Error(response.message);
      success('Planilha atualizada com sucesso');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao exportar planilha';
      showError(message);
    }
  };

  const handleToggleSelectionMode = () => {
    setSelectionMode((prev) => {
      if (prev) {
        setSelectedIds(new Set());
      }
      return !prev;
    });
  };

  const handleToggleSelectPedido = (pedido: { id: number; tipo_pedido?: string }) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(pedido.id)) {
        next.delete(pedido.id);
      } else {
        if (pedido.tipo_pedido !== 'Entrega') return next;
        next.add(pedido.id);
      }
      return next;
    });
  };

  const handleCalcularDistanciasSelecionados = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      info('Selecione ao menos 1 pedido de entrega');
      return;
    }
    try {
      await calcDistanciasLote.mutateAsync({ pedidoIds: ids, forceRecalc: true });
      success('Distâncias recalculadas para selecionados');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao recalcular distâncias';
      showError(errorMessage);
    }
  };

  const handleIrParaMapa = () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      info('Selecione pedidos para roteirizar');
      return;
    }
    const query = `ids=${ids.join(',')}`;
    window.open(`/rota-entrega?${query}`, '_blank');
  };

  const handleOcultarConcluidos = async () => {
    const confirmed = await confirm({
      title: 'Ocultar pedidos concluídos',
      description: 'Todos os pedidos com status "concluído" serão ocultados do painel. Esta ação não deleta os pedidos, apenas os remove da visualização.',
      confirmColor: 'primary',
      confirmText: 'Ocultar',
    });
    if (!confirmed) return;

    try {
      const result = await ocultarConcluidos.mutateAsync();
      success(result.message || `${result.count} pedido(s) concluído(s) ocultado(s) do painel`);
      setFilterMenuAnchor(null); // Fechar menu após ação
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao ocultar pedidos concluídos';
      showError(errorMessage);
    }
  };

  const handleFilterMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setFilterMenuAnchor(event.currentTarget);
  };

  const handleFilterMenuClose = () => {
    setFilterMenuAnchor(null);
  };

  return (
    <Box>
      {(!navigator.onLine &&
        (((pedidosData as { __offline?: { stale?: boolean } })?.__offline?.stale === true) || 
         ((statsData as { __offline?: { stale?: boolean } })?.__offline?.stale === true))) && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Mostrando dados desatualizados (cache expirado) por falta de conexão.
        </Alert>
      )}
      {/* Indicador de atualização */}
      {isFetching && (
        <Box
          sx={{
            position: 'fixed',
            top: 16,
            right: 16,
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            bgcolor: 'background.paper',
            borderRadius: 1,
            p: 1,
            boxShadow: 2,
          }}
        >
          <CircularProgress size={16} />
          <Typography variant="caption" color="text.secondary">
            Atualizando...
          </Typography>
        </Box>
      )}

      {/* Header com ações rápidas */}
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2} gap={2} flexWrap="wrap">
        <Box>
          <Typography variant="h5" component="h1">
            Pedidos
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Gerencie todos os pedidos em um só lugar
          </Typography>
        </Box>
        <Stack 
          direction="row" 
          spacing={1} 
          alignItems="center" 
          flexWrap="wrap" 
          justifyContent="flex-end"
          sx={{ 
            gap: { xs: 0.5, sm: 1 },
          }}
        >
          {/* Botão Roteirizar - sempre visível no topo */}
          <Tooltip title={selectionMode ? 'Sair do modo de roteirização' : 'Selecionar pedidos para criar rota de entrega'}>
            <Button
              variant={selectionMode ? 'contained' : 'outlined'}
              size="small"
              color="primary"
              startIcon={<Route />}
              onClick={handleToggleSelectionMode}
              sx={{
                fontWeight: selectionMode ? 600 : 400,
              }}
            >
              {isMobile ? (selectionMode ? 'Sair' : 'Rota') : (selectionMode ? 'Sair do modo de rota' : 'Roteirizar')}
            </Button>
          </Tooltip>
          
          {/* Mobile: Menu de filtros */}
          {isMobile ? (
            <>
              <Tooltip title="Filtros e ações">
                <IconButton
                  onClick={handleFilterMenuOpen}
                  color="primary"
                  sx={{ 
                    border: '1px solid',
                    borderColor: 'divider',
                  }}
                >
                  <FilterList />
                </IconButton>
              </Tooltip>
              <Menu
                anchorEl={filterMenuAnchor}
                open={Boolean(filterMenuAnchor)}
                onClose={handleFilterMenuClose}
                anchorOrigin={{
                  vertical: 'bottom',
                  horizontal: 'right',
                }}
                transformOrigin={{
                  vertical: 'top',
                  horizontal: 'right',
                }}
              >
                <MenuItem 
                  onClick={() => {
                    setSortByDistance((prev) => !prev);
                    handleFilterMenuClose();
                  }}
                >
                  <Sort sx={{ mr: 1.5 }} />
                  {sortByDistance ? 'Ordem padrão' : 'Ordenar por distância'}
                </MenuItem>
                <MenuItem 
                  onClick={() => {
                    handleExportSheet();
                    handleFilterMenuClose();
                  }}
                >
                  <FileDownload sx={{ mr: 1.5 }} />
                  Exportar planilha
                </MenuItem>
                <MenuItem 
                  onClick={() => {
                    window.location.href = '/fontes-pedido';
                    handleFilterMenuClose();
                  }}
                >
                  <Folder sx={{ mr: 1.5 }} />
                  Fontes
                </MenuItem>
                <Divider />
                {isAdmin && (
                  <MenuItem 
                    onClick={() => {
                      handleOcultarConcluidos();
                    }}
                    disabled={ocultarConcluidos.isPending}
                  >
                    <DeleteSweep sx={{ mr: 1.5 }} />
                    {ocultarConcluidos.isPending ? 'Ocultando...' : 'Ocultar concluídos'}
                  </MenuItem>
                )}
              </Menu>
              <Tooltip title="Atualizar dados">
                <IconButton
                  onClick={handleRefresh}
                  disabled={isFetching}
                  color="primary"
                >
                  <Refresh />
                </IconButton>
              </Tooltip>
            </>
          ) : (
            /* Desktop: Botões completos */
            <>
              <Tooltip title={sortByDistance ? 'Voltar para ordem padrão' : 'Ordenar pedidos por distância da origem'}>
                <Button 
                  variant="outlined" 
                  size="small" 
                  startIcon={<Sort />}
                  onClick={() => setSortByDistance((prev) => !prev)}
                >
                  {sortByDistance ? 'Ordem padrão' : 'Ordenar por distância'}
                </Button>
              </Tooltip>
              <Tooltip title="Exportar lista de pedidos para planilha Excel">
                <Button 
                  variant="outlined" 
                  size="small" 
                  startIcon={<FileDownload />}
                  onClick={handleExportSheet}
                >
                  Exportar planilha
                </Button>
              </Tooltip>
              <Tooltip title="Gerenciar fontes de pedido (Catálogo, Site, WhatsApp)">
                <Button 
                  variant="outlined" 
                  size="small" 
                  startIcon={<Folder />} 
                  onClick={() => (window.location.href = '/fontes-pedido')}
                >
                  Fontes
                </Button>
              </Tooltip>
              {isAdmin && (
                <Tooltip title="Ocultar todos os pedidos concluídos do painel">
                  <span>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<DeleteSweep />}
                      onClick={handleOcultarConcluidos}
                      disabled={ocultarConcluidos.isPending}
                      color="secondary"
                    >
                      {ocultarConcluidos.isPending ? 'Ocultando...' : 'Ocultar concluídos'}
                    </Button>
                  </span>
                </Tooltip>
              )}
              <Tooltip title="Atualizar dados">
                <IconButton
                  onClick={handleRefresh}
                  disabled={isFetching}
                  color="primary"
                >
                  <Refresh />
                </IconButton>
              </Tooltip>
            </>
          )}
        </Stack>
      </Box>

      {/* Stats Cards */}
      {statsData?.stats && (
        <OrdersKPIGrid
          stats={{
            total: statsData.stats.total,
            agendados: statsData.stats.agendados,
            producao: statsData.stats.producao,
            prontos: statsData.stats.prontos,
            entregues: statsData.stats.entregues,
            atrasados: statsData.stats.atrasados,
          }}
        />
      )}

      {/* Filters */}
      <Paper
        sx={{
          p: { xs: 2, md: 3 },
          mb: 3,
        }}
      >
        {/* Ações do modo de roteirização */}
        {selectionMode && (
          <Stack 
            direction={{ xs: 'column', sm: 'row' }} 
            spacing={2} 
            alignItems={{ xs: 'stretch', sm: 'center' }} 
            justifyContent="space-between" 
            mb={2}
            sx={{
              p: 2,
              bgcolor: 'primary.50',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'primary.200',
            }}
          >
            <Stack 
              direction={{ xs: 'column', sm: 'row' }} 
              spacing={1} 
              alignItems={{ xs: 'stretch', sm: 'center' }}
              flexWrap="wrap"
              sx={{ width: { xs: '100%', sm: 'auto' } }}
            >
              <Button
                size="small"
                variant="outlined"
                onClick={handleCalcularDistanciasSelecionados}
                disabled={calcDistanciasLote.isPending}
                fullWidth={isMobile}
              >
                {calcDistanciasLote.isPending ? 'Calculando...' : 'Calcular distâncias'}
              </Button>
              <Button
                size="small"
                variant="contained"
                color="primary"
                onClick={handleIrParaMapa}
                disabled={selectedIds.size === 0}
                fullWidth={isMobile}
              >
                Ir para o mapa
              </Button>
            </Stack>
            <Chip
              color={selectedIds.size > 0 ? 'primary' : 'default'}
              label={`${selectedIds.size} selecionado(s) para rota`}
              sx={{ alignSelf: { xs: 'center', sm: 'auto' } }}
            />
          </Stack>
        )}
        <OrdersFilterToolbar
          search={filters.search || ''}
          status={filters.status || ''}
          onSearchChange={(val) => setFilters((prev) => ({ ...prev, search: val }))}
          onStatusChange={(status) => {
            setFilters((prev) => ({ ...prev, status: status || undefined }));
          }}
          onDateRangeChange={(start, end) => setFilters((prev) => ({ ...prev, data_inicio: start, data_fim: end }))}
        />
      </Paper>

      {/* Ordenação */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <OrdersSorting
          sortBy={filters.sort_by || 'dia_entrega'}
          sortOrder={filters.sort_order || 'asc'}
          onChange={(sortBy, sortOrder) => {
            setFilters((prev) => ({ ...prev, sort_by: sortBy, sort_order: sortOrder, page: 1 }));
          }}
        />
      </Paper>

      {/* Orders List */}
      {isLoadingPedidos ? (
        <Loading variant="skeleton" count={6} />
      ) : pedidosError ? (
        <ErrorState
          message={pedidosError.message || 'Erro ao carregar pedidos'}
          onRetry={() => refetchPedidos()}
        />
      ) : pedidosData && typeof pedidosData === 'object' && 'pedidos' in pedidosData && pedidosData.pedidos ? (
        <>
          <OrderList
            pedidos={sortedPedidos}
            onOrderClick={handleOrderClick}
            selectionMode={selectionMode}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelectPedido}
          />
          {pedidosData.total_pages && pedidosData.total_pages > 1 && (
            <OrdersPagination
              page={filters.page || 1}
              perPage={filters.per_page || 20}
              total={pedidosData.total}
              totalPages={pedidosData.total_pages}
              onPageChange={(page) => {
                setFilters((prev) => ({ ...prev, page }));
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              onPerPageChange={(perPage) => {
                setFilters((prev) => ({ ...prev, per_page: perPage, page: 1 }));
              }}
            />
          )}
        </>
      ) : (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="200px"
        >
          <Typography variant="body1" color="text.secondary">
            Nenhum pedido encontrado
          </Typography>
        </Box>
      )}
    </Box>
  );
}

