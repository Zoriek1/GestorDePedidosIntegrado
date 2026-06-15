import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Stack, Button, CircularProgress, Paper } from '@mui/material';
import LocalShipping from '@mui/icons-material/LocalShipping';
import MapIcon from '@mui/icons-material/Map';
import { useMinhasEntregas } from './services/entregasApi';
import { OrderCard } from '../pedidos/components/OrderCard';
import { groupOrdersByDate } from '../pedidos/utils/dateGrouping';

/**
 * Home dedicada do entregador (#7): em vez da lista geral de pedidos ("Todos"), mostra só as
 * entregas atribuídas a ele, com atalhos para "Pegar entregas" (painel inline na rota) e o mapa.
 */
export function EntregadorHome() {
  const navigate = useNavigate();
  const { data, isLoading } = useMinhasEntregas();
  const pedidos = useMemo(
    () => (data?.pedidos ?? []).filter((p) => !p.deleted_at),
    [data?.pedidos]
  );

  // Agrupa e ordena por dia de entrega (ATRASADOS, HOJE, AMANHÃ, …) como no resto do app,
  // em vez de uma lista achatada de todos os pedidos.
  const grupos = useMemo(() => groupOrdersByDate(pedidos), [pedidos]);

  const goPickup = () => navigate('/rota-entrega', { state: { pickup: true } });

  return (
    <Box>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        flexWrap="wrap"
        gap={1}
        mb={2}
      >
        <Typography variant="h5" component="h1">
          Minhas entregas
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<MapIcon />} onClick={() => navigate('/entregador/mapa')}>
            Mapa
          </Button>
          <Button variant="contained" startIcon={<LocalShipping />} onClick={goPickup}>
            Pegar entregas
          </Button>
        </Stack>
      </Stack>

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : pedidos.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary" gutterBottom>
            Você não tem entregas atribuídas no momento.
          </Typography>
          <Button variant="contained" startIcon={<LocalShipping />} sx={{ mt: 1 }} onClick={goPickup}>
            Pegar entregas
          </Button>
        </Paper>
      ) : (
        <Stack spacing={2}>
          {grupos.map((grupo) => (
            <Box key={grupo.label}>
              <Typography
                variant="overline"
                color="text.secondary"
                sx={{ fontWeight: 700, display: 'block', mb: 0.5 }}
              >
                {grupo.label} · {grupo.pedidos.length}
              </Typography>
              <Stack spacing={1.5}>
                {grupo.pedidos.map((p) => (
                  <OrderCard key={p.id} pedido={p} operacional />
                ))}
              </Stack>
            </Box>
          ))}
        </Stack>
      )}
    </Box>
  );
}

export default EntregadorHome;
