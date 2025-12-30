/**
 * Orders Page - Main orders list view
 */

import { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Grid,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import { Refresh } from '@mui/icons-material';
import { useQueryClient } from '@tanstack/react-query';
import { usePedidos } from '../../api/endpoints/pedidos';
import type { PedidosFilters } from '../../api/endpoints/pedidos';
import { useStats } from '../../api/endpoints/stats';
import { OrderList } from './components/OrderList';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';

const STATUS_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'agendado', label: 'Agendado' },
  { value: 'producao', label: 'Em Produção' },
  { value: 'pronto', label: 'Pronto' },
  { value: 'entregue', label: 'Entregue' },
  { value: 'cancelado', label: 'Cancelado' },
  { value: 'concluido', label: 'Concluído' },
];

export default function OrdersPage() {
  const [filters, setFilters] = useState<PedidosFilters>({
    status: '',
    search: '',
  });

  const queryClient = useQueryClient();
  const { data: pedidosData, isLoading: isLoadingPedidos, isFetching: isFetchingPedidos, error: pedidosError, refetch: refetchPedidos } = usePedidos(filters);
  const { data: statsData, isLoading: isLoadingStats, isFetching: isFetchingStats, error: statsError } = useStats();

  const isFetching = isFetchingPedidos || isFetchingStats;

  const handleRefresh = () => {
    // Use exact: false to invalidate all query variations (including filtered ones)
    queryClient.invalidateQueries({ queryKey: ['pedidos'], exact: false });
    queryClient.invalidateQueries({ queryKey: ['stats'], exact: false });
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters((prev) => ({ ...prev, search: e.target.value }));
  };

  const handleStatusChange = (e: any) => {
    setFilters((prev) => ({ ...prev, status: e.target.value || undefined }));
  };

  const handleOrderClick = (pedido: any) => {
    // TODO: Navigate to order details in Phase 1.1
    console.log('Order clicked:', pedido);
  };

  return (
    <Box>
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

      {/* Header com botão Atualizar */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5" component="h1">
          Pedidos
        </Typography>
        <Tooltip title="Atualizar dados">
          <span>
            <IconButton
              onClick={handleRefresh}
              disabled={isFetching}
              color="primary"
            >
              <Refresh />
            </IconButton>
          </span>
        </Tooltip>
      </Box>

      {/* Stats Cards */}
      {statsData?.stats && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="div">
                  {statsData.stats.total}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="div">
                  {statsData.stats.agendados}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Agendados
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="div">
                  {statsData.stats.producao}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Em Produção
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="div">
                  {statsData.stats.prontos}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Prontos
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="div">
                  {statsData.stats.entregues}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Entregues
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="div">
                  {statsData.stats.atrasados}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Atrasados
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <TextField
              fullWidth
              label="Buscar pedidos"
              placeholder="Cliente, destinatário, produto..."
              value={filters.search || ''}
              onChange={handleSearchChange}
              variant="outlined"
              size="small"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select
                value={filters.status || ''}
                onChange={handleStatusChange}
                label="Status"
              >
                {STATUS_OPTIONS.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Orders List */}
      {isLoadingPedidos ? (
        <Loading variant="skeleton" count={6} />
      ) : pedidosError ? (
        <ErrorState
          message={pedidosError.message || 'Erro ao carregar pedidos'}
          onRetry={() => refetchPedidos()}
        />
      ) : pedidosData?.pedidos ? (
        <OrderList
          pedidos={pedidosData.pedidos}
          onOrderClick={handleOrderClick}
        />
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

