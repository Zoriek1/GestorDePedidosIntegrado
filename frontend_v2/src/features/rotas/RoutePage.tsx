import { useMemo, useState, useEffect, useRef, useCallback } from 'react';
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
  IconButton,
} from '@mui/material';
import ChevronLeft from '@mui/icons-material/ChevronLeft';
import ChevronRight from '@mui/icons-material/ChevronRight';
import Today from '@mui/icons-material/Today';
import DragIndicator from '@mui/icons-material/DragIndicator';
import {
  GoogleMap,
  useJsApiLoader,
  Marker,
  InfoWindow,
  Polyline,
} from '@react-google-maps/api';
import dayjs from 'dayjs';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { usePedidos, useCalcularDistanciasLote } from '../../api/endpoints/pedidos';
import { useCalcularRotaOtimizada, useRotaOtimizada, type RotaOtimizada } from '../../api/endpoints/rotas';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../components/system/useToast';

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

// Cores de marcador por status
const STATUS_COLORS: Record<string, string> = {
  agendado: '#4285F4',      // azul
  em_producao: '#FF9800',   // laranja
  pronto_entrega: '#4CAF50', // verde
  pronto_retirada: '#4CAF50',
  em_rota: '#9C27B0',       // roxo
  atrasado: '#F44336',      // vermelho
  concluido: '#9E9E9E',     // cinza
};

function getMarkerIcon(status: string) {
  const color = STATUS_COLORS[status] || '#4285F4';
  return {
    path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z',
    fillColor: color,
    fillOpacity: 1,
    strokeColor: '#fff',
    strokeWeight: 1,
    scale: 1.5,
    anchor: { x: 12, y: 22 } as google.maps.Point,
  };
}

const ORIGIN_ICON = {
  path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z',
  fillColor: '#E91E63',
  fillOpacity: 1,
  strokeColor: '#fff',
  strokeWeight: 2,
  scale: 2,
  anchor: { x: 12, y: 22 } as google.maps.Point,
};

const MAP_CONTAINER_STYLE = { height: '100%', width: '100%' };

// Componente SortableItem para cada pedido na lista
interface SortableItemProps {
  id: number;
  children: React.ReactNode;
}

function SortableItem({ id, children }: SortableItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <Paper variant="outlined" sx={{ p: 1.5, position: 'relative' }}>
        {children}
        <Box
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            cursor: 'grab',
            color: 'text.secondary',
            '&:active': {
              cursor: 'grabbing',
            },
          }}
          {...attributes}
          {...listeners}
        >
          <DragIndicator fontSize="small" />
        </Box>
      </Paper>
    </div>
  );
}

export default function RoutePage() {
  const [onlyAgendados, setOnlyAgendados] = useState(false);
  const [searchParams] = useSearchParams();
  const idsParam = searchParams.get('ids');
  const rotaIdParam = searchParams.get('rota_id');

  // --- Day selector state ---
  const [selectedDate, setSelectedDate] = useState(() => dayjs().startOf('day'));
  const dateStr = selectedDate.format('YYYY-MM-DD');
  const isToday = selectedDate.isSame(dayjs().startOf('day'), 'day');

  const goBack = () => setSelectedDate((d) => d.subtract(1, 'day'));
  const goForward = () => setSelectedDate((d) => d.add(1, 'day'));
  const goToday = () => setSelectedDate(dayjs().startOf('day'));

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
    data_inicio: dateStr,
    data_fim: dateStr,
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

  // Filtro: apenas pedidos tipo 'Entrega' com dia_entrega == data selecionada
  const pedidosFiltrados = useMemo(() => {
    return pedidos.filter(p =>
      p.tipo_pedido === 'Entrega' &&
      p.dia_entrega === dateStr
    );
  }, [pedidos, dateStr]);

  // Estado para ordem dos pedidos após drag-and-drop
  const pedidosFiltradosKey = useMemo(
    () => pedidosFiltrados.map(p => p.id).join(','),
    [pedidosFiltrados]
  );

  const [pedidosOrdenados, setPedidosOrdenados] = useState<typeof pedidosFiltrados>(() => pedidosFiltrados);
  const prevKeyRef = useRef(pedidosFiltradosKey);

  useEffect(() => {
    if (prevKeyRef.current !== pedidosFiltradosKey) {
      prevKeyRef.current = pedidosFiltradosKey;
      requestAnimationFrame(() => {
        setPedidosOrdenados([...pedidosFiltrados]);
      });
    }
  }, [pedidosFiltradosKey, pedidosFiltrados]);

  // Sensores para drag-and-drop
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setPedidosOrdenados((items) => {
      const oldIndex = items.findIndex((item) => item.id === active.id);
      const newIndex = items.findIndex((item) => item.id === over.id);

      const newItems = [...items];
      const [removed] = newItems.splice(oldIndex, 1);
      newItems.splice(newIndex, 0, removed);
      return newItems;
    });
  };

  const rotaData: RotaOtimizada | undefined = useMemo(() => {
    if (calcRota.data) return calcRota.data;
    if (rotaQuery.data) return rotaQuery.data;
    return undefined;
  }, [calcRota.data, rotaQuery.data]);

  const googleMapsUrl = rotaData?.google_maps_url ?? null;
  const stepByStepUrls = rotaData?.google_maps_step_by_step ?? [];

  const [showStepByStep, setShowStepByStep] = useState(false);

  useEffect(() => {
    if (selectedIds.length > 0) {
      setTimeout(() => {
        setOnlyAgendados(false);
      }, 0);
    }
  }, [selectedIds.length]);

  const handleCalcularDistancias = async () => {
    const ids = pedidosOrdenados.map((p) => p.id);
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
    const ids = pedidosOrdenados.map((p) => p.id);
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

  // --- Google Maps ---
  const { isLoaded: mapsLoaded } = useJsApiLoader({
    googleMapsApiKey: GOOGLE_MAPS_API_KEY,
  });

  const mapCenter = useMemo(() => {
    if (rotaData?.origem) {
      return { lat: rotaData.origem.lat, lng: rotaData.origem.lon };
    }
    const firstWithCoords = pedidosOrdenados.find((p) => p.coords_lat && p.coords_lon);
    if (firstWithCoords) return { lat: firstWithCoords.coords_lat!, lng: firstWithCoords.coords_lon! };
    return { lat: -16.6869, lng: -49.2648 }; // Goiânia fallback
  }, [rotaData, pedidosOrdenados]);

  const [activeInfoWindow, setActiveInfoWindow] = useState<number | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);

  const onMapLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
  }, []);

  // Fit bounds when data changes
  useEffect(() => {
    if (!mapRef.current) return;
    const points: { lat: number; lng: number }[] = [];
    if (rotaData?.origem) {
      points.push({ lat: rotaData.origem.lat, lng: rotaData.origem.lon });
    }
    pedidosOrdenados.forEach((p) => {
      if (p.coords_lat && p.coords_lon) {
        points.push({ lat: p.coords_lat, lng: p.coords_lon });
      }
    });
    if (points.length > 1) {
      const bounds = new google.maps.LatLngBounds();
      points.forEach((pt) => bounds.extend(pt));
      mapRef.current.fitBounds(bounds, 50);
    }
  }, [rotaData, pedidosOrdenados]);

  // Polyline path for optimized route
  const routePath = useMemo(() => {
    if (!rotaData?.waypoints || rotaData.waypoints.length < 2) return [];
    const path = rotaData.waypoints.map((wp) => ({ lat: wp[0], lng: wp[1] }));
    // Add origin at start and end if available
    if (rotaData.origem) {
      const origin = { lat: rotaData.origem.lat, lng: rotaData.origem.lon };
      path.unshift(origin);
      path.push(origin);
    }
    return path;
  }, [rotaData]);

  // Format date for display
  const dateDisplay = useMemo(() => {
    if (isToday) return `Hoje, ${selectedDate.format('DD/MM')}`;
    return selectedDate.format('ddd, DD/MM/YYYY');
  }, [selectedDate, isToday]);

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

        {/* Day selector */}
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <IconButton size="small" onClick={goBack} title="Dia anterior">
            <ChevronLeft />
          </IconButton>
          <Button
            size="small"
            variant={isToday ? 'contained' : 'outlined'}
            onClick={goToday}
            startIcon={<Today />}
            sx={{ minWidth: 160, textTransform: 'none' }}
          >
            {dateDisplay}
          </Button>
          <IconButton size="small" onClick={goForward} title="Próximo dia">
            <ChevronRight />
          </IconButton>
        </Stack>

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
            disabled={calcRota.isPending || pedidosOrdenados.length < 2}
          >
            {calcRota.isPending ? 'Otimizando...' : 'Otimizar rota'}
          </Button>
          {googleMapsUrl && (
            <Button
              variant="outlined"
              size="small"
              onClick={() => window.open(googleMapsUrl, '_blank')}
            >
              Abrir no Google Maps
            </Button>
          )}
          {stepByStepUrls.length > 0 && (
            <Button
              variant="outlined"
              size="small"
              onClick={() => setShowStepByStep((prev) => !prev)}
            >
              {showStepByStep ? 'Esconder etapas' : 'Entrega a entrega'}
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
              {!GOOGLE_MAPS_API_KEY ? (
                <Box display="flex" alignItems="center" justifyContent="center" height="100%">
                  <Alert severity="warning">
                    Configure <code>VITE_GOOGLE_MAPS_API_KEY</code> no .env para exibir o mapa.
                  </Alert>
                </Box>
              ) : !mapsLoaded ? (
                <Box display="flex" alignItems="center" justifyContent="center" height="100%">
                  <Loading variant="spinner" />
                </Box>
              ) : (
                <GoogleMap
                  mapContainerStyle={MAP_CONTAINER_STYLE}
                  center={mapCenter}
                  zoom={12}
                  onLoad={onMapLoad}
                  options={{
                    streetViewControl: false,
                    mapTypeControl: false,
                    fullscreenControl: true,
                  }}
                >
                  {/* Origem (Floricultura) */}
                  {rotaData?.origem && (
                    <Marker
                      position={{ lat: rotaData.origem.lat, lng: rotaData.origem.lon }}
                      icon={ORIGIN_ICON}
                      title="Floricultura (Origem)"
                      onClick={() => setActiveInfoWindow(-1)}
                    >
                      {activeInfoWindow === -1 && (
                        <InfoWindow onCloseClick={() => setActiveInfoWindow(null)}>
                          <div><strong>Origem (Floricultura)</strong></div>
                        </InfoWindow>
                      )}
                    </Marker>
                  )}

                  {/* Marcadores dos pedidos */}
                  {pedidosOrdenados
                    .filter((p) => p.coords_lat && p.coords_lon)
                    .map((pedido, idx) => (
                      <Marker
                        key={`pedido-${pedido.id}`}
                        position={{ lat: pedido.coords_lat!, lng: pedido.coords_lon! }}
                        icon={getMarkerIcon(pedido.status)}
                        label={{
                          text: String(idx + 1),
                          color: '#fff',
                          fontSize: '11px',
                          fontWeight: 'bold',
                        }}
                        title={`#${pedido.id} - ${pedido.destinatario || pedido.cliente}`}
                        onClick={() => setActiveInfoWindow(pedido.id)}
                      >
                        {activeInfoWindow === pedido.id && (
                          <InfoWindow onCloseClick={() => setActiveInfoWindow(null)}>
                            <div style={{ maxWidth: 220 }}>
                              <strong>Pedido #{pedido.id}</strong>
                              <br />
                              <strong>Cliente:</strong> {pedido.cliente}
                              {pedido.destinatario && (
                                <>
                                  <br />
                                  <strong>Destinatário:</strong> {pedido.destinatario}
                                </>
                              )}
                              <br />
                              <strong>Endereço:</strong> {pedido.endereco || `${pedido.rua || ''} ${pedido.numero || ''}`.trim()}
                              <br />
                              <strong>Data/Hora:</strong> {pedido.dia_entrega} {pedido.horario}
                              <br />
                              <strong>Status:</strong> {pedido.status}
                              {pedido.distancia_km && (
                                <>
                                  <br />
                                  <strong>Distância:</strong> {pedido.distancia_km.toFixed(2)} km
                                </>
                              )}
                            </div>
                          </InfoWindow>
                        )}
                      </Marker>
                    ))}

                  {/* Linha da rota otimizada */}
                  {routePath.length > 1 && (
                    <Polyline
                      path={routePath}
                      options={{ strokeColor: '#4CAF50', strokeWeight: 4, strokeOpacity: 0.8 }}
                    />
                  )}
                </GoogleMap>
              )}
            </Paper>
            {showStepByStep && stepByStepUrls.length > 0 && (
              <Paper variant="outlined" sx={{ mt: 2, p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Navegação entrega a entrega
                </Typography>
                <Stack spacing={0.5}>
                  {stepByStepUrls.map((s) => (
                    <Button
                      key={s.step}
                      variant="text"
                      size="small"
                      sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                      onClick={() => window.open(s.url, '_blank')}
                    >
                      {s.step}. {s.label}
                    </Button>
                  ))}
                </Stack>
              </Paper>
            )}
            {selectedIds.length > 0 && (
              <Alert severity="info" sx={{ mt: 2 }}>
                Visualizando IDs: {selectedIds.join(', ')}. Clique em "Otimizar rota" para gerar caminho.
              </Alert>
            )}
          </Grid>

          <Grid size={{ xs: 12, md: 5 }}>
            <Paper sx={{ p: 2 }}>
              {pedidosOrdenados.length === 0 ? (
                <Box p={2}>
                  <Typography variant="body2" color="text.secondary">
                    Nenhum pedido de entrega para {isToday ? 'hoje' : selectedDate.format('DD/MM/YYYY')}.
                  </Typography>
                </Box>
              ) : (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={pedidosOrdenados.map(p => p.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    <Stack spacing={1.5}>
                      {pedidosOrdenados.map((pedido, idx) => (
                        <SortableItem key={pedido.id} id={pedido.id}>
                          <Stack spacing={0.5}>
                            <Typography variant="subtitle1" fontWeight="bold">
                              {idx + 1}. #{pedido.id} · {pedido.destinatario || pedido.cliente}
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
                        </SortableItem>
                      ))}
                    </Stack>
                  </SortableContext>
                </DndContext>
              )}
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
