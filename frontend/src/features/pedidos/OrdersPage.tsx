/**
 * Orders Page - Main orders list view
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  ToggleButton,
  ToggleButtonGroup,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { Refresh, DeleteSweep, FileDownload, FilterList, Route, Print, ViewList, ViewKanban, SearchOff } from '@mui/icons-material';
import { useQueryClient } from '@tanstack/react-query';
import { usePedidos, useCalcularDistanciasLote, useOcultarPedidosConcluidos } from '../../api/endpoints/pedidos';
import type { PedidosFilters } from '../../api/endpoints/pedidos';
import { useStats } from '../../api/endpoints/stats';
import { OrderList } from './components/OrderList';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { createApiRequest } from '../../api/http';
import { useAuth } from '../auth/authStore';
import { useStoreKey, tenantKey } from '../../lib/tenantKey';
import { useToast } from '../../components/system/useToast';
import { useConfirm } from '../../components/system/useConfirm';
import { OrdersKPIGrid } from './components/OrdersKPIGrid';
import { OrdersFilterToolbar } from './components/OrdersFilterToolbar';
import { OrdersPagination } from './components/OrdersPagination';
import { KanbanBoard } from './components/KanbanBoard';
import { EntregadorHome } from '../entregas/EntregadorHome';
import { usePedidoPrintService } from './services/PedidoPrintService';
import type { PrintLayout } from './services/IPedidoPrintService';

type ViewMode = 'lista' | 'quadro';

const MAX_BATCH_PRINT = 100;

export default function OrdersPage() {
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  const [filters, setFilters] = useState<PedidosFilters>({
    status: '',
    search: '',
    sort_by: 'dia_entrega',
    sort_order: 'asc', // Mais próximos primeiro (asc = datas mais próximas primeiro: hoje antes de amanhã)
    page: 1,
    // Sem per_page no estado inicial: o valor é derivado de `effectivePerPage` (ver
    // abaixo). Modo operação (filtro ativo) carrega o conjunto inteiro; só a visão
    // global "Tudo" mantém um teto de segurança.
  });
  const [selectionMode, setSelectionMode] = useState<null | 'route' | 'print'>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [printLayout, setPrintLayout] = useState<PrintLayout>(4);
  const [filterMenuAnchor, setFilterMenuAnchor] = useState<null | HTMLElement>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('lista');

  const queryClient = useQueryClient();
  const { getAuthHeader, getUserRole } = useAuth();
  const storeKey = useStoreKey();
  const { success, error: showError, info } = useToast();
  const confirm = useConfirm();
  const printService = usePedidoPrintService();
  
  const userRole = getUserRole() || 'admin'; // Default para admin se não especificado
  const isAdmin = userRole === 'admin';
  const isEntregador = userRole === 'entregador';
  const canOcultarConcluidos = isAdmin || userRole === 'vendedor';
  
  // Modo operação: qualquer filtro de data/status/busca ativo → carrega o conjunto
  // inteiro (per_page indefinido = backend devolve o array todo, sem total_pages, e a
  // paginação some sozinha). Visão global "Tudo" sem filtro → teto de segurança pra
  // não puxar o histórico inteiro no PWA (200, ou o que o usuário escolher no seletor).
  const hasActiveFilter = Boolean(
    filters.status || filters.data_inicio || filters.data_fim || filters.search
  );
  const effectivePerPage = hasActiveFilter ? undefined : (filters.per_page ?? 200);

  // Entregadores só podem ver pedidos agendados e em rota
  const adjustedFilters = isEntregador
    ? { ...filters, statuses: ['agendado', 'em_rota'], per_page: effectivePerPage }
    : { ...filters, per_page: effectivePerPage };
  
  const { data: pedidosData, isLoading: isLoadingPedidos, isFetching: isFetchingPedidos, error: pedidosError, refetch: refetchPedidos } = usePedidos(adjustedFilters);
  const { data: statsData, isFetching: isFetchingStats } = useStats();
  const calcDistanciasLote = useCalcularDistanciasLote();
  const ocultarConcluidos = useOcultarPedidosConcluidos();

  const isFetching = isFetchingPedidos || isFetchingStats;

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedidos'), exact: false });
    queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'stats'), exact: false });
  };

  const handleOrderClick = (pedido: { id: number }) => {
    navigate(`/pedidos/${pedido.id}`);
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

  const handleExportSheet = async () => {
    try {
      const apiRequest = createApiRequest(getAuthHeader);
      info('Exportando planilha…');
      const response = await apiRequest<{ success: boolean; message?: string }>('/pedidos/exportar-planilha', {
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

  const setMode = (mode: null | 'route' | 'print') => {
    setSelectionMode(mode);
    setSelectedIds(new Set());
  };

  const handleToggleRouteMode = () => {
    setMode(selectionMode === 'route' ? null : 'route');
  };

  const handleTogglePrintMode = () => {
    setMode(selectionMode === 'print' ? null : 'print');
  };

  const handleToggleSelectPedido = (pedido: { id: number; tipo_pedido?: string }) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(pedido.id)) {
        next.delete(pedido.id);
      } else {
        // Em modo rota só aceita Entrega; em modo impressão aceita qualquer tipo
        if (selectionMode === 'route' && pedido.tipo_pedido !== 'Entrega') return next;
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

  const handleImprimirSelecionados = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      info('Selecione ao menos 1 pedido para imprimir');
      return;
    }
    if (ids.length > MAX_BATCH_PRINT) {
      showError(`Máximo de ${MAX_BATCH_PRINT} pedidos por lote`);
      return;
    }
    try {
      await printService.printBatch(ids, printLayout);
      success('Impressão iniciada');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao imprimir em lote';
      showError(errorMessage);
    }
  };

  // Seleção em massa para impressão (limitada ao teto do lote).
  const handleSelecionarTodos = () => {
    const ids = visiblePedidos.map((p) => p.id).slice(0, MAX_BATCH_PRINT);
    setSelectedIds(new Set(ids));
    if (visiblePedidos.length > MAX_BATCH_PRINT) {
      info(`Selecionados os primeiros ${MAX_BATCH_PRINT} pedidos (limite por lote)`);
    }
  };

  const handleSelecionarNaoImpressos = () => {
    const ids = visiblePedidos
      .filter((p) => !p.impresso)
      .map((p) => p.id)
      .slice(0, MAX_BATCH_PRINT);
    setSelectedIds(new Set(ids));
    if (ids.length === 0) {
      info('Nenhum pedido não impresso na lista atual');
    }
  };

  const handleLimparSelecao = () => setSelectedIds(new Set());

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

  // Entregador tem visão dedicada (#7): só as entregas dele, sem a lista geral "Todos".
  if (isEntregador) {
    return <EntregadorHome />;
  }

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
          {/* Alternar Lista / Quadro (Kanban) */}
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            size="small"
            onChange={(_e, v: ViewMode | null) => {
              if (v) {
                setViewMode(v);
                setMode(null); // sai de seleção de rota/impressão ao trocar de visão
              }
            }}
          >
            <ToggleButton value="lista" aria-label="Visão em lista">
              <ViewList fontSize="small" sx={{ mr: { xs: 0, sm: 0.5 } }} />
              {!isMobile && 'Lista'}
            </ToggleButton>
            <ToggleButton value="quadro" aria-label="Visão em quadro">
              <ViewKanban fontSize="small" sx={{ mr: { xs: 0, sm: 0.5 } }} />
              {!isMobile && 'Quadro'}
            </ToggleButton>
          </ToggleButtonGroup>

          {/* Roteirizar e Imprimir lote só fazem sentido na visão em lista */}
          {viewMode === 'lista' && (
            <>
              {/* Botão Roteirizar */}
              <Tooltip title={selectionMode === 'route' ? 'Sair do modo de roteirização' : 'Selecionar entregas para criar rota'}>
                <Button
                  variant={selectionMode === 'route' ? 'contained' : 'outlined'}
                  size="small"
                  color="primary"
                  startIcon={<Route />}
                  onClick={handleToggleRouteMode}
                  sx={{ fontWeight: selectionMode === 'route' ? 600 : 400 }}
                >
                  {isMobile
                    ? (selectionMode === 'route' ? 'Sair' : 'Rota')
                    : (selectionMode === 'route' ? 'Sair do modo de rota' : 'Roteirizar')}
                </Button>
              </Tooltip>

              {/* Botão Imprimir lote */}
              <Tooltip title={selectionMode === 'print' ? 'Sair do modo de impressão em lote' : `Selecionar até ${MAX_BATCH_PRINT} pedidos (moldura 1, 2 ou 4 por folha A4)`}>
                <Button
                  variant={selectionMode === 'print' ? 'contained' : 'outlined'}
                  size="small"
                  color="primary"
                  startIcon={<Print />}
                  onClick={handleTogglePrintMode}
                  sx={{ fontWeight: selectionMode === 'print' ? 600 : 400 }}
                >
                  {isMobile
                    ? (selectionMode === 'print' ? 'Sair' : 'Lote')
                    : (selectionMode === 'print' ? 'Sair do modo de impressão' : 'Imprimir lote')}
                </Button>
              </Tooltip>
            </>
          )}

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
                    handleExportSheet();
                    handleFilterMenuClose();
                  }}
                >
                  <FileDownload sx={{ mr: 1.5 }} />
                  Exportar planilha
                </MenuItem>
                <Divider />
                {canOcultarConcluidos && (
                  <MenuItem
                    onClick={() => {
                      handleOcultarConcluidos();
                    }}
                    disabled={ocultarConcluidos.isPending}
                  >
                    <DeleteSweep sx={{ mr: 1.5 }} />
                    {ocultarConcluidos.isPending ? 'Ocultando…' : 'Ocultar concluídos'}
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
              {canOcultarConcluidos && (
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
                      {ocultarConcluidos.isPending ? 'Ocultando…' : 'Ocultar concluídos'}
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
            emRota: statsData.stats.emRota,
            atrasados: statsData.stats.atrasados,
          }}
          activeStatus={filters.status || ''}
          onFilterByStatus={(status) => updateFilters({ status: status || undefined })}
        />
      )}

      {/* Filters */}
      <Paper
        sx={{
          p: { xs: 2, md: 3 },
          mb: 3,
        }}
      >
        {/* Barra de ações do modo de seleção */}
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
              {selectionMode === 'route' && (
                <>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={handleCalcularDistanciasSelecionados}
                    disabled={calcDistanciasLote.isPending || selectedIds.size === 0}
                    fullWidth={isMobile}
                  >
                    {calcDistanciasLote.isPending ? 'Calculando…' : 'Calcular distâncias'}
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
                </>
              )}
              {selectionMode === 'print' && (
                <>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={handleSelecionarTodos}
                    fullWidth={isMobile}
                  >
                    Selecionar todos
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={handleSelecionarNaoImpressos}
                    fullWidth={isMobile}
                  >
                    Não impressos
                  </Button>
                  <Button
                    size="small"
                    variant="text"
                    color="inherit"
                    onClick={handleLimparSelecao}
                    disabled={selectedIds.size === 0}
                    fullWidth={isMobile}
                  >
                    Limpar
                  </Button>
                  <ToggleButtonGroup
                    size="small"
                    exclusive
                    value={printLayout}
                    onChange={(_e, val) => { if (val) setPrintLayout(val as PrintLayout); }}
                    aria-label="Moldura (pedidos por folha)"
                    fullWidth={isMobile}
                  >
                    <ToggleButton value={1} aria-label="1 por página">1/pág</ToggleButton>
                    <ToggleButton value={2} aria-label="2 por página">2/pág</ToggleButton>
                    <ToggleButton value={4} aria-label="4 por página">4/pág</ToggleButton>
                  </ToggleButtonGroup>
                  <Tooltip
                    title={
                      selectedIds.size === 0
                        ? `Selecione 1 a ${MAX_BATCH_PRINT} pedidos`
                        : selectedIds.size > MAX_BATCH_PRINT
                          ? `Máximo de ${MAX_BATCH_PRINT} pedidos por lote`
                          : `${Math.ceil(selectedIds.size / printLayout)} folha(s) A4 — ${printLayout} por folha`
                    }
                  >
                    <span>
                      <Button
                        size="small"
                        variant="contained"
                        color="primary"
                        startIcon={<Print />}
                        onClick={handleImprimirSelecionados}
                        disabled={selectedIds.size === 0 || selectedIds.size > MAX_BATCH_PRINT}
                        fullWidth={isMobile}
                      >
                        Imprimir {selectedIds.size > 0 ? `(${selectedIds.size})` : 'selecionados'}
                      </Button>
                    </span>
                  </Tooltip>
                </>
              )}
            </Stack>
            <Stack direction="column" spacing={0.5} alignItems={{ xs: 'center', sm: 'flex-end' }}>
              <Chip
                color={selectedIds.size > 0 ? 'primary' : 'default'}
                label={
                  selectionMode === 'route'
                    ? `${selectedIds.size} selecionado(s) para rota`
                    : `${selectedIds.size} selecionado(s) para imprimir`
                }
              />
              {selectionMode === 'print' && (
                <Typography variant="caption" color="text.secondary">
                  Até {MAX_BATCH_PRINT} pedidos · {printLayout} por folha A4
                </Typography>
              )}
            </Stack>
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

      {/* Conteúdo: Quadro (Kanban) ou Lista */}
      {viewMode === 'quadro' ? (
        <KanbanBoard
          filters={{
            search: filters.search,
            data_inicio: filters.data_inicio,
            data_fim: filters.data_fim,
          }}
        />
      ) : isLoadingPedidos ? (
        <Loading variant="skeleton" count={6} />
      ) : pedidosError ? (
        <ErrorState
          message={pedidosError.message || 'Erro ao carregar pedidos'}
          onRetry={() => refetchPedidos()}
        />
      ) : pedidosData && typeof pedidosData === 'object' && 'pedidos' in pedidosData && pedidosData.pedidos ? (
        <>
          <OrderList
            pedidos={visiblePedidos}
            onOrderClick={handleOrderClick}
            selectionMode={selectionMode !== null}
            selectionKind={selectionMode ?? 'route'}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelectPedido}
          />
          {(pedidosData.total_pages ?? 0) > 1 && (
            <OrdersPagination
              page={filters.page || 1}
              perPage={effectivePerPage ?? 200}
              total={pedidosData.total}
              totalPages={pedidosData.total_pages ?? 1}
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
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          minHeight="200px"
          gap={1}
        >
          <SearchOff sx={{ fontSize: 48, color: 'text.disabled' }} />
          <Typography variant="h6" color="text.secondary">
            Nenhum pedido encontrado
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Tente ajustar os filtros ou crie um novo pedido
          </Typography>
        </Box>
      )}

    </Box>
  );
}

