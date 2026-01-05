import { useMemo, useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Chip,
  Stack,
  Button,
  Alert,
} from '@mui/material';
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { usePedidos, useCalcularDistanciasLote } from '../../api/endpoints/pedidos';
import { useCalcularRotaOtimizada, useRotaOtimizada, type RotaOtimizada } from '../../api/endpoints/rotas';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../components/system/useToast';

// Ajuste padrão para ícones do Leaflet (evita erro de assets)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default as any).prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Função para criar ícone customizado por status
function createStatusIcon(status: string): L.Icon {
  let color = 'blue'; // padrão
  
  if (status === 'agendado') {
    color = 'blue';
  } else if (status === 'em_producao') {
    color = 'orange';
  } else if (status === 'pronto_entrega' || status === 'pronto_retirada') {
    color = 'green';
  } else if (status === 'em_rota') {
    color = 'purple';
  } else if (status === 'atrasado') {
    color = 'red';
  } else if (status === 'concluido') {
    color = 'gray';
  }

  return L.icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${color}.png`,
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  });
}

export default function RoutePage() {
  const [onlyAgendados, setOnlyAgendados] = useState(false);
  const [searchParams] = useSearchParams();
  const idsParam = searchParams.get('ids');
  const rotaIdParam = searchParams.get('rota_id');

  const selectedIds = useMemo(
    () => (idsParam ? idsParam.split(',').map((id) => Number(id)).filter(Number.isFinite) : []),
    [idsParam],
  );
  const rotaId = useMemo(() => {
    const parsed = Number(rotaIdParam);
    return Number.isFinite(parsed) ? parsed : undefined;
  }, [rotaIdParam]);

  const { data, isLoading, error, refetch } = usePedidos({
    status: onlyAgendados ? 'agendado' : undefined,
  });
  const calcLote = useCalcularDistanciasLote();
  const calcRota = useCalcularRotaOtimizada();
  const rotaQuery = useRotaOtimizada(rotaId);
  const { success, error: showError, info } = useToast();

  const pedidos = useMemo(() => {
    const base = data?.pedidos ?? [];
    if (selectedIds.length > 0) {
      return base.filter((p) => selectedIds.includes(p.id));
    }
    return base;
  }, [data?.pedidos, selectedIds]);

  const rotaData: RotaOtimizada | undefined = useMemo(() => {
    if (calcRota.data) return calcRota.data;
    if (rotaQuery.data) return rotaQuery.data;
    return undefined;
  }, [calcRota.data, rotaQuery.data]);

  useEffect(() => {
    if (selectedIds.length > 0) {
      // Usar setTimeout para evitar setState síncrono em effect
      setTimeout(() => {
        setOnlyAgendados(false);
      }, 0);
    }
  }, [selectedIds.length]);

  const handleCalcularDistancias = async () => {
    const ids = pedidos.filter((p) => p.tipo_pedido === 'Entrega').map((p) => p.id);
    if (ids.length === 0) {
      info('Nenhum pedido elegível para cálculo de distância');
      return;
    }
    try {
      await calcLote.mutateAsync({ pedidoIds: ids, forceRecalc: true });
      success('Distâncias recalculadas');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao calcular distâncias';
      showError(errorMessage);
    }
  };

  const handleOtimizarRota = async () => {
    const ids = pedidos.filter((p) => p.tipo_pedido === 'Entrega').map((p) => p.id);
    if (ids.length < 2) {
      info('Selecione pelo menos 2 entregas para otimizar');
      return;
    }
    try {
      await calcRota.mutateAsync({ pedidoIds: ids });
      success('Rota otimizada');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao otimizar rota';
      showError(errorMessage);
    }
  };

  const mapCenter = useMemo<[number, number]>(() => {
    if (rotaData?.origem) {
      return [rotaData.origem.lat, rotaData.origem.lon] as [number, number];
    }
    const firstWithCoords = pedidos.find((p) => p.coords_lat && p.coords_lon);
    if (firstWithCoords) return [firstWithCoords.coords_lat!, firstWithCoords.coords_lon!] as [number, number];
    return [-23.5489, -46.6388] as [number, number]; // fallback
  }, [rotaData, pedidos]);

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2} spacing={2} flexWrap="wrap">
        <Box>
          <Typography variant="h4" component="h1">
            Rota de Entrega
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Visualize mapa, waypoints e otimize trajetos
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Button variant="outlined" size="small" onClick={() => setOnlyAgendados((prev) => !prev)}>
            {onlyAgendados ? 'Mostrar todos' : 'Somente agendados'}
          </Button>
          <Button
            variant="outlined"
            size="small"
            onClick={handleCalcularDistancias}
            disabled={calcLote.isPending || isLoading}
          >
            {calcLote.isPending ? 'Calculando...' : 'Calcular distâncias'}
          </Button>
          <Button
            variant="contained"
            size="small"
            onClick={handleOtimizarRota}
            disabled={calcRota.isPending || pedidos.length < 2}
          >
            {calcRota.isPending ? 'Otimizado...' : 'Otimizar rota'}
          </Button>
          {rotaData?.graphhopper_maps_url && (
            <Button
              variant="outlined"
              size="small"
              onClick={() => window.open(rotaData.graphhopper_maps_url as string, '_blank')}
            >
              Abrir no mapa externo
            </Button>
          )}
        </Stack>
      </Stack>

      {isLoading ? (
        <Loading variant="skeleton" count={4} />
      ) : error ? (
        <ErrorState message="Erro ao carregar pedidos" onRetry={() => refetch()} />
      ) : (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 7 }}>
            <Paper sx={{ height: 480, overflow: 'hidden' }}>
              <MapContainer center={mapCenter} zoom={12} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                
                {/* Origem (Floricultura) */}
                {rotaData?.origem && (
                  <Marker position={[rotaData.origem.lat, rotaData.origem.lon]}>
                    <Popup>
                      <strong>Origem (Floricultura)</strong>
                    </Popup>
                  </Marker>
                )}
                
                {/* Marcadores dos pedidos com coordenadas calculadas */}
                {pedidos
                  .filter((p) => p.coords_lat && p.coords_lon && p.tipo_pedido === 'Entrega')
                  .map((pedido) => (
                    <Marker
                      key={`pedido-${pedido.id}`}
                      position={[pedido.coords_lat!, pedido.coords_lon!]}
                      icon={createStatusIcon(pedido.status)}
                    >
                      <Popup>
                        <Box>
                          <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                            Pedido #{pedido.id}
                          </Typography>
                          <Typography variant="body2">
                            <strong>Cliente:</strong> {pedido.cliente}
                          </Typography>
                          {pedido.destinatario && (
                            <Typography variant="body2">
                              <strong>Destinatário:</strong> {pedido.destinatario}
                            </Typography>
                          )}
                          <Typography variant="body2">
                            <strong>Endereço:</strong> {pedido.endereco || `${pedido.rua || ''} ${pedido.numero || ''}`.trim()}
                          </Typography>
                          <Typography variant="body2">
                            <strong>Data/Hora:</strong> {pedido.dia_entrega} {pedido.horario}
                          </Typography>
                          <Typography variant="body2">
                            <strong>Status:</strong> {pedido.status}
                          </Typography>
                          {pedido.distancia_km && (
                            <Typography variant="body2">
                              <strong>Distância:</strong> {pedido.distancia_km.toFixed(2)} km
                            </Typography>
                          )}
                        </Box>
                      </Popup>
                    </Marker>
                  ))}
                
                {/* Waypoints da rota otimizada */}
                {rotaData?.waypoints?.map((wp, idx) => {
                  // Verificar se já existe um marcador de pedido nesta posição
                  const pedidoNoWaypoint = pedidos.find(
                    (p) => p.coords_lat && p.coords_lon && 
                    Math.abs(p.coords_lat - wp[0]) < 0.0001 && 
                    Math.abs(p.coords_lon - wp[1]) < 0.0001
                  );
                  
                  // Só mostrar waypoint se não houver pedido já marcado
                  if (pedidoNoWaypoint) return null;
                  
                  return (
                    <Marker key={`waypoint-${idx}`} position={[wp[0], wp[1]]}>
                      <Popup>Waypoint {idx + 1} - Pedido #{rotaData.sequencia_pedidos?.[idx] ?? ''}</Popup>
                    </Marker>
                  );
                })}
                
                {/* Linha da rota otimizada */}
                {rotaData?.waypoints && rotaData.waypoints.length > 1 && (
                  <Polyline 
                    positions={rotaData.waypoints.map((wp) => [wp[0], wp[1]])} 
                    pathOptions={{ color: 'green', weight: 3, opacity: 0.7 }} 
                  />
                )}
              </MapContainer>
            </Paper>
            {selectedIds.length > 0 && (
              <Alert severity="info" sx={{ mt: 2 }}>
                Visualizando IDs: {selectedIds.join(', ')}. Clique em “Otimizar rota” para gerar caminho.
              </Alert>
            )}
          </Grid>

          <Grid size={{ xs: 12, md: 5 }}>
            <Paper sx={{ p: 2 }}>
              <Stack spacing={1.5}>
                {pedidos.map((pedido) => (
                  <Paper key={pedido.id} variant="outlined" sx={{ p: 1.5 }}>
                    <Stack spacing={0.5}>
                      <Typography variant="subtitle1" fontWeight="bold">
                        #{pedido.id} · {pedido.destinatario || pedido.cliente}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {pedido.endereco || `${pedido.rua || ''} ${pedido.numero || ''}`.trim()}
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip label={pedido.status} size="small" />
                        {pedido.distancia_km && (
                          <Chip label={`${pedido.distancia_km.toFixed(1)} km`} size="small" color="info" />
                        )}
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        Data/Hora: {pedido.dia_entrega} {pedido.horario}
                      </Typography>
                    </Stack>
                  </Paper>
                ))}
                {pedidos.length === 0 && (
                  <Box p={2}>
                    <Typography variant="body2" color="text.secondary">
                      Nenhum pedido encontrado para roteirização.
                    </Typography>
                  </Box>
                )}
              </Stack>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
