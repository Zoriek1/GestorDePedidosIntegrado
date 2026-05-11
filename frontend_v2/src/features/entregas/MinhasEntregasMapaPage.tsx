import { useMemo, useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Button,
  Chip,
  Alert,
  Divider,
  IconButton,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import LocalShipping from '@mui/icons-material/LocalShipping';
import CheckCircle from '@mui/icons-material/CheckCircle';
import Map from '@mui/icons-material/Map';
import ArrowBack from '@mui/icons-material/ArrowBack';
import { GoogleMap, useJsApiLoader, Marker } from '@react-google-maps/api';
import { useAuth } from '../auth/authStore';
import { useMinhasEntregas, useFinalizarEntrega } from './services/entregasApi';
import { Loading } from '../../components/common/Loading';
import { useToast } from '../../components/system/useToast';
import { isAdmin } from '../auth/roleHelpers';

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

const moneyBRL = (n?: number) =>
  typeof n === 'number'
    ? n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : '—';

export default function MinhasEntregasMapaPage() {
  const { getUser } = useAuth();
  const user = getUser();
  const isAdminUser = isAdmin(user?.role);
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const toast = useToast();

  const { data, isLoading, isError, refetch } = useMinhasEntregas();
  const finalizar = useFinalizarEntrega();
  const [busyId, setBusyId] = useState<number | null>(null);

  const pedidos = useMemo(() => data?.pedidos ?? [], [data?.pedidos]);

  const center = useMemo(() => {
    const withCoords = pedidos.filter((p) => p.coords_lat && p.coords_lon);
    if (!withCoords.length) return { lat: -23.5505, lng: -46.6333 }; // SP default
    const lat = withCoords.reduce((s, p) => s + (p.coords_lat || 0), 0) / withCoords.length;
    const lng = withCoords.reduce((s, p) => s + (p.coords_lon || 0), 0) / withCoords.length;
    return { lat, lng };
  }, [pedidos]);

  const { isLoaded: mapsLoaded } = useJsApiLoader({
    googleMapsApiKey: GOOGLE_MAPS_API_KEY,
  });

  // Mantém referência do mapa para forçar resize/recentro quando o container
  // ganha tamanho depois do mount (problema clássico em layouts flex no mobile).
  const mapRef = useRef<google.maps.Map | null>(null);
  const onMapLoad = (map: google.maps.Map) => {
    mapRef.current = map;
  };

  // Quando pedidos chegam ou o viewport muda, reaplicar o center.
  useEffect(() => {
    if (!mapRef.current || !mapsLoaded) return;
    const m = mapRef.current;
    // pequeno delay garante que o container já tem largura/altura final
    const t = window.setTimeout(() => {
      google.maps.event.trigger(m, 'resize');
      m.setCenter(center);
    }, 50);
    return () => window.clearTimeout(t);
  }, [center, mapsLoaded, isMobile, pedidos.length]);

  const handleFinalizar = async (id: number) => {
    setBusyId(id);
    try {
      await finalizar.mutateAsync(id);
      const pedido = pedidos.find((p) => p.id === id);
      const taxa = pedido?.taxa_entrega || 0;
      toast.success(`Entrega finalizada · ${moneyBRL(taxa)} adicionado ao seu saldo`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Falha ao finalizar entrega');
    } finally {
      setBusyId(null);
    }
  };

  if (!user || (!isAdminUser && user.role !== 'entregador')) {
    return (
      <Box p={3}>
        <Alert severity="warning">Esta página é para entregadores.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      <Stack direction="row" alignItems="center" spacing={1} p={2}>
        <IconButton onClick={() => navigate(-1)} size="small">
          <ArrowBack />
        </IconButton>
        <LocalShipping color="primary" />
        <Typography variant="h6" flex={1}>
          Minhas entregas{data?.entregador_id && isAdminUser ? ` · #${data.entregador_id}` : ''}
        </Typography>
        <Chip label={`${pedidos.length} entrega(s)`} size="small" />
      </Stack>

      <Box
        sx={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          gap: 1,
          px: 1,
          pb: 1,
        }}
      >
        {/* Altura fixa em px/vh: o GoogleMap usa height:100% e colapsa se o pai só tem minHeight */}
        <Paper
          sx={{
            flex: 1,
            // Altura em PX (vh resolve pra 0 em alguns contextos no mobile,
            // e o GoogleMap captura o tamanho no mount sem re-medir).
            height: isMobile ? 360 : 520,
            overflow: 'hidden',
          }}
        >
          {!GOOGLE_MAPS_API_KEY ? (
            <Box p={3} textAlign="center" color="text.secondary">
              <Map sx={{ fontSize: 48, opacity: 0.5 }} />
              <Typography variant="caption" display="block">
                Configure VITE_GOOGLE_MAPS_API_KEY no .env para exibir o mapa.
              </Typography>
            </Box>
          ) : !mapsLoaded ? (
            <Loading />
          ) : (
            <GoogleMap
              mapContainerStyle={{ width: '100%', height: '100%' }}
              center={center}
              zoom={12}
              onLoad={onMapLoad}
              options={{
                streetViewControl: false,
                mapTypeControl: false,
                fullscreenControl: !isMobile,
                gestureHandling: 'greedy',
              }}
            >
              {pedidos
                .filter((p) => p.coords_lat && p.coords_lon)
                .map((p) => (
                  <Marker
                    key={p.id}
                    position={{ lat: p.coords_lat!, lng: p.coords_lon! }}
                    label={String(p.id)}
                  />
                ))}
            </GoogleMap>
          )}
        </Paper>

        <Paper sx={{ width: isMobile ? '100%' : 380, maxHeight: '80vh', overflowY: 'auto' }}>
          {isLoading && <Loading />}
          {isError && (
            <Box p={2}>
              <Alert severity="error" action={<Button onClick={() => refetch()}>Tentar novamente</Button>}>
                Falha ao carregar
              </Alert>
            </Box>
          )}
          {!isLoading && pedidos.length === 0 && (
            <Box p={3} textAlign="center" color="text.secondary">
              <Typography variant="body2">Nenhuma entrega atribuída a você.</Typography>
              <Button sx={{ mt: 2 }} variant="outlined" onClick={() => navigate('/')}>
                Voltar
              </Button>
            </Box>
          )}
          {pedidos.map((p, i) => (
            <Box key={p.id}>
              {i > 0 && <Divider />}
              <Box p={2}>
                <Stack direction="row" alignItems="center" spacing={1} mb={0.5}>
                  <Typography variant="subtitle2" fontWeight={700}>
                    #{p.id} — {p.destinatario || p.cliente}
                  </Typography>
                  <Chip
                    size="small"
                    label={moneyBRL(p.taxa_entrega)}
                    color="success"
                    variant="outlined"
                  />
                </Stack>
                <Typography variant="caption" color="text.secondary" display="block">
                  {p.dia_entrega} {p.horario && `· ${p.horario}`}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  {p.endereco || `${p.rua || ''} ${p.numero || ''}, ${p.bairro || ''}`}
                </Typography>
                <Stack direction="row" spacing={1} mt={1}>
                  {p.coords_lat && p.coords_lon && (
                    <Button
                      size="small"
                      variant="outlined"
                      component="a"
                      href={`https://www.google.com/maps/dir/?api=1&destination=${p.coords_lat},${p.coords_lon}`}
                      target="_blank"
                      rel="noopener"
                    >
                      Rotear
                    </Button>
                  )}
                  <Button
                    size="small"
                    variant="contained"
                    color="success"
                    startIcon={<CheckCircle />}
                    onClick={() => handleFinalizar(p.id)}
                    disabled={busyId === p.id}
                  >
                    Finalizar entrega
                  </Button>
                </Stack>
              </Box>
            </Box>
          ))}
        </Paper>
      </Box>
    </Box>
  );
}
