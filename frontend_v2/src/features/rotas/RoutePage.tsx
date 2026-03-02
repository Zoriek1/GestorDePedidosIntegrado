<<<<<<< HEAD
import { useMemo, useState, useEffect, useRef } from 'react';
=======
import { useMemo, useState, useEffect, useRef, useCallback } from 'react';
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
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
<<<<<<< HEAD
} from '@mui/material';
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
=======
  IconButton,
  Checkbox,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import ChevronLeft from '@mui/icons-material/ChevronLeft';
import ChevronRight from '@mui/icons-material/ChevronRight';
import Today from '@mui/icons-material/Today';
import DragIndicator from '@mui/icons-material/DragIndicator';
import MapIcon from '@mui/icons-material/Map';
import RouteIcon from '@mui/icons-material/Route';
import {
  GoogleMap,
  useJsApiLoader,
  Marker,
  InfoWindow,
  Polyline,
} from '@react-google-maps/api';
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
import dayjs from 'dayjs';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
<<<<<<< HEAD
import { DragIndicator } from '@mui/icons-material';
import { usePedidos, useCalcularDistanciasLote } from '../../api/endpoints/pedidos';
import { useCalcularRotaOtimizada, useRotaOtimizada, type RotaOtimizada } from '../../api/endpoints/rotas';
=======
import { usePedidos, useCalcularDistanciasLote } from '../../api/endpoints/pedidos';
import { useCalcularRotaOtimizada, useRotaOtimizada, useGerarRotaMaps, type RotaOtimizada } from '../../api/endpoints/rotas';
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../components/system/useToast';

<<<<<<< HEAD
// Ajuste padrão para ícones do Leaflet (evita erro de assets)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default as any).prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});
=======
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

// Cores de marcador por status
const STATUS_COLORS: Record<string, string> = {
  agendado: '#4285F4',
  em_producao: '#FF9800',
  pronto_entrega: '#4CAF50',
  pronto_retirada: '#4CAF50',
  em_rota: '#9C27B0',
  atrasado: '#F44336',
  concluido: '#9E9E9E',
};

function getMarkerIcon(status: string, selected: boolean) {
  const color = selected
    ? (STATUS_COLORS[status] || '#4285F4')
    : '#BDBDBD'; // cinza se não selecionado
  return {
    path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z',
    fillColor: color,
    fillOpacity: selected ? 1 : 0.5,
    strokeColor: selected ? '#fff' : '#999',
    strokeWeight: selected ? 1 : 0.5,
    scale: selected ? 1.5 : 1.2,
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
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14

// Componente SortableItem para cada pedido na lista
interface SortableItemProps {
  id: number;
<<<<<<< HEAD
  children: React.ReactNode;
}

function SortableItem({ id, children }: SortableItemProps) {
=======
  compact?: boolean;
  children: React.ReactNode;
}

function SortableItem({ id, compact, children }: SortableItemProps) {
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
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
<<<<<<< HEAD
      <Paper variant="outlined" sx={{ p: 1.5, position: 'relative' }}>
=======
      <Paper variant="outlined" sx={{ p: compact ? 0.75 : 1.5, position: 'relative' }}>
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
        {children}
        <Box
          sx={{
            position: 'absolute',
<<<<<<< HEAD
            top: 8,
            right: 8,
            cursor: 'grab',
            color: 'text.secondary',
            '&:active': {
              cursor: 'grabbing',
            },
=======
            top: compact ? 4 : 8,
            right: compact ? 4 : 8,
            cursor: 'grab',
            color: 'text.secondary',
            '&:active': { cursor: 'grabbing' },
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
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

<<<<<<< HEAD
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
=======
export default function RoutePage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  const [onlyAgendados, setOnlyAgendados] = useState(false);
  const [searchParams] = useSearchParams();
  const idsParam = searchParams.get('ids');
  const rotaIdParam = searchParams.get('rota_id');
<<<<<<< HEAD
  const hoje = dayjs().startOf('day').format('YYYY-MM-DD');
=======

  // --- Day selector state ---
  const [selectedDate, setSelectedDate] = useState(() => dayjs().startOf('day'));
  const dateStr = selectedDate.format('YYYY-MM-DD');
  const isToday = selectedDate.isSame(dayjs().startOf('day'), 'day');

  const goBack = () => setSelectedDate((d) => d.subtract(1, 'day'));
  const goForward = () => setSelectedDate((d) => d.add(1, 'day'));
  const goToday = () => setSelectedDate(dayjs().startOf('day'));

  // --- Selection state ---
  const [selectedPedidoIds, setSelectedPedidoIds] = useState<Set<number>>(new Set());
  const [showMap, setShowMap] = useState(false); // mobile map toggle

  const togglePedido = (id: number) => {
    setSelectedPedidoIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14

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
<<<<<<< HEAD
    data_inicio: hoje,
    data_fim: hoje,
=======
    data_inicio: dateStr,
    data_fim: dateStr,
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  });
  const calcLote = useCalcularDistanciasLote();
  const calcRota = useCalcularRotaOtimizada();
  const rotaQuery = useRotaOtimizada(rotaId);
<<<<<<< HEAD
=======
  const gerarRotaMaps = useGerarRotaMaps();
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  const { success, error: showError, info } = useToast();

  const pedidos = useMemo(() => {
    const base = data?.pedidos ?? [];
    if (selectedIds.length > 0) {
      return base.filter((p) => selectedIds.includes(p.id));
    }
    return base;
  }, [data?.pedidos, selectedIds]);

<<<<<<< HEAD
  // Filtro de visibilidade: apenas pedidos tipo 'Entrega' com dia_entrega == hoje
  const pedidosFiltrados = useMemo(() => {
    return pedidos.filter(p => 
      p.tipo_pedido === 'Entrega' && 
      p.dia_entrega === hoje
    );
  }, [pedidos, hoje]);

  // Estado para ordem dos pedidos após drag-and-drop
  // Usar chave baseada nos IDs para resetar quando pedidosFiltrados mudar estruturalmente
=======
  // Filtro: apenas pedidos tipo 'Entrega' com dia_entrega == data selecionada
  const pedidosFiltrados = useMemo(() => {
    return pedidos.filter(p =>
      p.tipo_pedido === 'Entrega' &&
      p.dia_entrega === dateStr
    );
  }, [pedidos, dateStr]);

  // Estado para ordem dos pedidos após drag-and-drop
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  const pedidosFiltradosKey = useMemo(
    () => pedidosFiltrados.map(p => p.id).join(','),
    [pedidosFiltrados]
  );
<<<<<<< HEAD
  
  const [pedidosOrdenados, setPedidosOrdenados] = useState<typeof pedidosFiltrados>(() => pedidosFiltrados);
  const prevKeyRef = useRef(pedidosFiltradosKey);

  // Resetar ordem quando lista de pedidos mudar estruturalmente
  // Usar requestAnimationFrame para evitar setState síncrono no render
  useEffect(() => {
    if (prevKeyRef.current !== pedidosFiltradosKey) {
      prevKeyRef.current = pedidosFiltradosKey;
      // Usar requestAnimationFrame para tornar assíncrono
      requestAnimationFrame(() => {
        setPedidosOrdenados([...pedidosFiltrados]);
=======

  const [pedidosOrdenados, setPedidosOrdenados] = useState<typeof pedidosFiltrados>(() => pedidosFiltrados);
  const prevKeyRef = useRef(pedidosFiltradosKey);

  useEffect(() => {
    if (prevKeyRef.current !== pedidosFiltradosKey) {
      prevKeyRef.current = pedidosFiltradosKey;
      requestAnimationFrame(() => {
        setPedidosOrdenados([...pedidosFiltrados]);
        // Select all by default when list changes
        setSelectedPedidoIds(new Set(pedidosFiltrados.map(p => p.id)));
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
      });
    }
  }, [pedidosFiltradosKey, pedidosFiltrados]);

<<<<<<< HEAD
=======
  // Initialize selection when first loaded
  useEffect(() => {
    if (pedidosFiltrados.length > 0 && selectedPedidoIds.size === 0) {
      setSelectedPedidoIds(new Set(pedidosFiltrados.map(p => p.id)));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pedidosFiltrados]);

>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  // Sensores para drag-and-drop
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

<<<<<<< HEAD
  // Handler para fim do drag
=======
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setPedidosOrdenados((items) => {
      const oldIndex = items.findIndex((item) => item.id === active.id);
      const newIndex = items.findIndex((item) => item.id === over.id);
<<<<<<< HEAD
      
=======

>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
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

<<<<<<< HEAD
  // Função para gerar URL do Google Maps
  // Nota: waypoints do backend vêm como [lon, lat] para GraphHopper
  // Google Maps precisa de [lat, lon], então invertemos
  const gerarGoogleMapsUrl = (rotaData: RotaOtimizada): string | null => {
    if (!rotaData?.origem || !rotaData?.waypoints || rotaData.waypoints.length === 0) {
      return null;
    }
    
    const origem = `${rotaData.origem.lat},${rotaData.origem.lon}`;
    // Waypoints vêm como [lon, lat] do backend, inverter para Google Maps [lat, lon]
    const waypoints = rotaData.waypoints
      .map(wp => `${wp[1]},${wp[0]}`) // Inverter: wp[1] é lat, wp[0] é lon
      .join('/');
    
    // Formato: /dir/origem/waypoint1/waypoint2/.../origem (retorno)
    return `https://www.google.com/maps/dir/${origem}/${waypoints}/${origem}`;
  };

  const googleMapsUrl = useMemo(() => {
    if (!rotaData) return null;
    return gerarGoogleMapsUrl(rotaData);
  }, [rotaData]);

  useEffect(() => {
    if (selectedIds.length > 0) {
      // Usar setTimeout para evitar setState síncrono em effect
=======
  const googleMapsUrl = rotaData?.google_maps_url ?? null;
  const stepByStepUrls = rotaData?.google_maps_step_by_step ?? [];

  const [showStepByStep, setShowStepByStep] = useState(false);

  useEffect(() => {
    if (selectedIds.length > 0) {
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
      setTimeout(() => {
        setOnlyAgendados(false);
      }, 0);
    }
  }, [selectedIds.length]);

<<<<<<< HEAD
  const handleCalcularDistancias = async () => {
    const ids = pedidosOrdenados.map((p) => p.id);
    if (ids.length === 0) {
      info('Nenhum pedido elegível para cálculo de distância');
=======
  // Selected pedido IDs in order
  const selectedIdsInOrder = useMemo(
    () => pedidosOrdenados.filter(p => selectedPedidoIds.has(p.id)).map(p => p.id),
    [pedidosOrdenados, selectedPedidoIds]
  );

  const allSelected = pedidosOrdenados.length > 0 && selectedPedidoIds.size === pedidosOrdenados.length;
  const someSelected = selectedPedidoIds.size > 0 && !allSelected;

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedPedidoIds(new Set());
    } else {
      setSelectedPedidoIds(new Set(pedidosOrdenados.map(p => p.id)));
    }
  };

  const handleCalcularDistancias = async () => {
    const ids = selectedIdsInOrder;
    if (ids.length === 0) {
      info('Selecione pelo menos 1 pedido');
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
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
<<<<<<< HEAD
    const ids = pedidosOrdenados.map((p) => p.id);
=======
    const ids = selectedIdsInOrder;
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
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

<<<<<<< HEAD
  const mapCenter = useMemo<[number, number]>(() => {
    if (rotaData?.origem) {
      return [rotaData.origem.lat, rotaData.origem.lon] as [number, number];
    }
    const firstWithCoords = pedidosOrdenados.find((p) => p.coords_lat && p.coords_lon);
    if (firstWithCoords) return [firstWithCoords.coords_lat!, firstWithCoords.coords_lon!] as [number, number];
    return [-16.6869, -49.2648] as [number, number]; // Goiânia, GO (fallback)
  }, [rotaData, pedidosOrdenados]);

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
            disabled={calcRota.isPending || pedidosOrdenados.length < 2}
          >
            {calcRota.isPending ? 'Otimizado...' : 'Otimizar rota'}
          </Button>
          {rotaData?.graphhopper_maps_url && (
            <Button
              variant="outlined"
              size="small"
              onClick={() => window.open(rotaData.graphhopper_maps_url as string, '_blank')}
            >
              Abrir no GraphHopper
            </Button>
          )}
          {googleMapsUrl && (
            <Button
              variant="outlined"
              size="small"
              onClick={() => window.open(googleMapsUrl, '_blank')}
            >
              Abrir no Google Maps
            </Button>
          )}
        </Stack>
=======
  const handleGerarRota = async () => {
    const ids = selectedIdsInOrder;
    if (ids.length < 2) {
      info('Selecione pelo menos 2 entregas para gerar rota');
      return;
    }
    try {
      const result = await gerarRotaMaps.mutateAsync(ids);
      if (result.google_maps_url) {
        window.open(result.google_maps_url, '_blank');
        success('Rota aberta no Google Maps');
      } else {
        showError('Não foi possível gerar a URL do Google Maps');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao gerar rota';
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
    return { lat: -16.6869, lng: -49.2648 };
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

  // Map section (reused for both desktop and mobile)
  const mapSection = (
    <Paper sx={{ height: isMobile ? 350 : 480, overflow: 'hidden' }}>
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
            .map((pedido, idx) => {
              const isSelected = selectedPedidoIds.has(pedido.id);
              return (
                <Marker
                  key={`pedido-${pedido.id}`}
                  position={{ lat: pedido.coords_lat!, lng: pedido.coords_lon! }}
                  icon={getMarkerIcon(pedido.status, isSelected)}
                  label={isSelected ? {
                    text: String(idx + 1),
                    color: '#fff',
                    fontSize: '11px',
                    fontWeight: 'bold',
                  } : undefined}
                  title={`#${pedido.id} - ${pedido.destinatario || pedido.cliente}`}
                  onClick={() => {
                    togglePedido(pedido.id);
                    setActiveInfoWindow(pedido.id);
                  }}
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
                        <strong>Status:</strong> {pedido.status}
                        {pedido.distancia_km && (
                          <>
                            <br />
                            <strong>Distância:</strong> {pedido.distancia_km.toFixed(2)} km
                          </>
                        )}
                        <br />
                        <Chip
                          label={isSelected ? 'Selecionado' : 'Não selecionado'}
                          size="small"
                          color={isSelected ? 'success' : 'default'}
                          sx={{ mt: 0.5 }}
                        />
                      </div>
                    </InfoWindow>
                  )}
                </Marker>
              );
            })}

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
  );

  return (
    <Box sx={{ px: isMobile ? 0.5 : 0 }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={isMobile ? 1 : 2} spacing={1} flexWrap="wrap">
        <Box>
          <Typography variant={isMobile ? 'h6' : 'h4'} component="h1">
            Rota de Entrega
          </Typography>
          {!isMobile && (
            <Typography variant="body2" color="text.secondary">
              Visualize mapa, waypoints e otimize trajetos
            </Typography>
          )}
        </Box>

        {/* Day selector */}
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <IconButton size="small" onClick={goBack} title="Dia anterior">
            <ChevronLeft fontSize={isMobile ? 'small' : 'medium'} />
          </IconButton>
          <Button
            size="small"
            variant={isToday ? 'contained' : 'outlined'}
            onClick={goToday}
            startIcon={<Today fontSize="small" />}
            sx={{
              minWidth: isMobile ? 120 : 160,
              textTransform: 'none',
              fontSize: isMobile ? '0.75rem' : undefined,
              px: isMobile ? 1 : 2,
            }}
          >
            {dateDisplay}
          </Button>
          <IconButton size="small" onClick={goForward} title="Próximo dia">
            <ChevronRight fontSize={isMobile ? 'small' : 'medium'} />
          </IconButton>
        </Stack>
      </Stack>

      {/* Action buttons */}
      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap mb={isMobile ? 1 : 2} sx={{ gap: isMobile ? 0.5 : 1 }}>
        <Button
          variant="outlined"
          size="small"
          onClick={() => setOnlyAgendados((prev) => !prev)}
          sx={{ fontSize: isMobile ? '0.7rem' : undefined, px: isMobile ? 1 : undefined }}
        >
          {onlyAgendados ? 'Todos' : 'Agendados'}
        </Button>
        <Button
          variant="outlined"
          size="small"
          onClick={handleCalcularDistancias}
          disabled={calcLote.isPending || isLoading || selectedPedidoIds.size === 0}
          sx={{ fontSize: isMobile ? '0.7rem' : undefined, px: isMobile ? 1 : undefined }}
        >
          {calcLote.isPending ? 'Calculando...' : 'Distâncias'}
        </Button>
        <Button
          variant="contained"
          size="small"
          onClick={handleOtimizarRota}
          disabled={calcRota.isPending || selectedPedidoIds.size < 2}
          sx={{ fontSize: isMobile ? '0.7rem' : undefined, px: isMobile ? 1 : undefined }}
        >
          {calcRota.isPending ? 'Otimizando...' : 'Otimizar'}
        </Button>
        <Button
          variant="contained"
          size="small"
          color="success"
          startIcon={<RouteIcon fontSize="small" />}
          onClick={handleGerarRota}
          disabled={gerarRotaMaps.isPending || selectedPedidoIds.size < 2}
          sx={{ fontSize: isMobile ? '0.7rem' : undefined, px: isMobile ? 1 : undefined }}
        >
          {gerarRotaMaps.isPending ? 'Gerando...' : `Rota (${selectedPedidoIds.size})`}
        </Button>
        {isMobile && (
          <Button
            variant="outlined"
            size="small"
            startIcon={<MapIcon fontSize="small" />}
            onClick={() => setShowMap((prev) => !prev)}
            sx={{ fontSize: isMobile ? '0.7rem' : undefined, px: isMobile ? 1 : undefined }}
          >
            {showMap ? 'Esconder' : 'Mapa'}
          </Button>
        )}
        {googleMapsUrl && (
          <Button
            variant="outlined"
            size="small"
            onClick={() => window.open(googleMapsUrl, '_blank')}
            sx={{ fontSize: isMobile ? '0.7rem' : undefined, px: isMobile ? 1 : undefined }}
          >
            Google Maps
          </Button>
        )}
        {stepByStepUrls.length > 0 && (
          <Button
            variant="outlined"
            size="small"
            onClick={() => setShowStepByStep((prev) => !prev)}
            sx={{ fontSize: isMobile ? '0.7rem' : undefined, px: isMobile ? 1 : undefined }}
          >
            {showStepByStep ? 'Esconder etapas' : 'Etapas'}
          </Button>
        )}
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
      </Stack>

      {isLoading ? (
        <Loading variant="skeleton" count={4} />
      ) : error ? (
        <ErrorState message="Erro ao carregar pedidos" onRetry={() => refetch()} />
      ) : (
<<<<<<< HEAD
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
                {pedidosOrdenados
                  .filter((p) => p.coords_lat && p.coords_lon)
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
                  const pedidoNoWaypoint = pedidosOrdenados.find(
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
              {pedidosOrdenados.length === 0 ? (
                <Box p={2}>
                  <Typography variant="body2" color="text.secondary">
                    Nenhum pedido de entrega para hoje.
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
                      {pedidosOrdenados.map((pedido) => (
                        <SortableItem key={pedido.id} id={pedido.id}>
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
                        </SortableItem>
                      ))}
                    </Stack>
                  </SortableContext>
                </DndContext>
              )}
            </Paper>
          </Grid>
        </Grid>
=======
        <>
          {/* Mobile: show map only when toggled */}
          {isMobile && showMap && (
            <Box mb={2}>
              {mapSection}
            </Box>
          )}

          <Grid container spacing={2}>
            {/* Desktop: always show map */}
            {!isMobile && (
              <Grid size={{ xs: 12, md: 7 }}>
                {mapSection}
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
            )}

            <Grid size={{ xs: 12, md: !isMobile ? 5 : 12 }}>
              {/* Mobile: step by step below list */}
              {isMobile && showStepByStep && stepByStepUrls.length > 0 && (
                <Paper variant="outlined" sx={{ mb: 2, p: 2 }}>
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

              <Paper sx={{ p: isMobile ? 1 : 2 }}>
                {pedidosOrdenados.length === 0 ? (
                  <Box p={1}>
                    <Typography variant={isMobile ? 'caption' : 'body2'} color="text.secondary">
                      Nenhum pedido de entrega para {isToday ? 'hoje' : selectedDate.format('DD/MM/YYYY')}.
                    </Typography>
                  </Box>
                ) : (
                  <>
                    {/* Select all header */}
                    <Stack direction="row" alignItems="center" spacing={0.5} mb={1}>
                      <Checkbox
                        checked={allSelected}
                        indeterminate={someSelected}
                        onChange={toggleSelectAll}
                        size="small"
                      />
                      <Typography variant="caption" color="text.secondary">
                        {selectedPedidoIds.size}/{pedidosOrdenados.length} selecionados
                      </Typography>
                    </Stack>

                    <DndContext
                      sensors={sensors}
                      collisionDetection={closestCenter}
                      onDragEnd={handleDragEnd}
                    >
                      <SortableContext
                        items={pedidosOrdenados.map(p => p.id)}
                        strategy={verticalListSortingStrategy}
                      >
                        <Stack spacing={isMobile ? 0.75 : 1.5}>
                          {pedidosOrdenados.map((pedido, idx) => (
                            <SortableItem key={pedido.id} id={pedido.id} compact={isMobile}>
                              <Stack direction="row" alignItems="flex-start" spacing={0.5}>
                                <Checkbox
                                  checked={selectedPedidoIds.has(pedido.id)}
                                  onChange={() => togglePedido(pedido.id)}
                                  size="small"
                                  sx={{ mt: -0.5, ml: -0.5, p: isMobile ? 0.25 : undefined }}
                                />
                                <Stack spacing={0.25} sx={{ flex: 1, minWidth: 0 }}>
                                  <Typography
                                    variant={isMobile ? 'body2' : 'subtitle1'}
                                    fontWeight="bold"
                                    sx={{ fontSize: isMobile ? '0.8rem' : undefined }}
                                  >
                                    {idx + 1}. #{pedido.id} · {pedido.destinatario || pedido.cliente}
                                  </Typography>
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    noWrap
                                    sx={{ fontSize: isMobile ? '0.7rem' : undefined }}
                                  >
                                    {pedido.endereco || `${pedido.rua || ''} ${pedido.numero || ''}`.trim()}
                                  </Typography>
                                  <Stack direction="row" spacing={0.5} alignItems="center">
                                    <Chip
                                      label={pedido.status}
                                      size="small"
                                      sx={{ fontSize: isMobile ? '0.65rem' : undefined, height: isMobile ? 20 : undefined }}
                                    />
                                    {pedido.distancia_km && (
                                      <Chip
                                        label={`${pedido.distancia_km.toFixed(1)} km`}
                                        size="small"
                                        color="info"
                                        sx={{ fontSize: isMobile ? '0.65rem' : undefined, height: isMobile ? 20 : undefined }}
                                      />
                                    )}
                                  </Stack>
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    sx={{ fontSize: isMobile ? '0.65rem' : undefined }}
                                  >
                                    {pedido.dia_entrega} {pedido.horario}
                                  </Typography>
                                </Stack>
                              </Stack>
                            </SortableItem>
                          ))}
                        </Stack>
                      </SortableContext>
                    </DndContext>
                  </>
                )}
              </Paper>
            </Grid>
          </Grid>
        </>
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
      )}
    </Box>
  );
}
