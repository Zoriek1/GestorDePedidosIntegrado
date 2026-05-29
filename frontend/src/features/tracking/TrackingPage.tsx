/**
 * Página pública de acompanhamento do pedido (cliente final).
 * Sem login, fora do AppShell. Consome /api/pedidos/track/<token> (token assinado),
 * que devolve apenas campos públicos (whitelist) — nenhum dado sensível.
 */

import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Container,
  Paper,
  Typography,
  Stack,
  Chip,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
  Divider,
} from '@mui/material';
import { LocalFlorist, CalendarMonth, Schedule } from '@mui/icons-material';
import { getApiBaseUrl } from '../../api/http';
import { BrandLogo } from '../../layout/BrandLogo';

interface PublicPedido {
  status: string;
  status_key: string;
  tipo_pedido: string;
  destinatario: string;
  produto: string;
  dia_entrega: string;
  janela: string;
}

type Estado = 'carregando' | 'ok' | 'nao_encontrado' | 'erro';

interface TrackResult {
  pedido?: PublicPedido;
  notFound?: boolean;
}

const POLL_MS = 60_000;

// Passos do acompanhamento, por tipo de pedido.
const STEPS_ENTREGA = ['Confirmado', 'Em preparação', 'Saiu para entrega', 'Entregue'];
const STEPS_RETIRADA = ['Confirmado', 'Em preparação', 'Pronto para retirada', 'Retirado'];

/** Mapeia o status interno para o índice do passo atual (0..3). */
function activeStep(statusKey: string, isRetirada: boolean): number {
  if (isRetirada) {
    switch (statusKey) {
      case 'agendado':
        return 0;
      case 'em_producao':
        return 1;
      case 'pronto_retirada':
      case 'pronto_entrega':
        return 2;
      case 'concluido':
        return 3;
      default:
        return 0;
    }
  }
  switch (statusKey) {
    case 'agendado':
      return 0;
    case 'em_producao':
    case 'pronto_entrega':
      return 1;
    case 'em_rota':
      return 2;
    case 'concluido':
      return 3;
    default:
      return 0;
  }
}

export default function TrackingPage() {
  const { token } = useParams<{ token: string }>();

  const { data, isPending, isError } = useQuery<TrackResult>({
    queryKey: ['track', token],
    enabled: !!token,
    refetchInterval: POLL_MS, // atualiza o status periodicamente
    retry: 1,
    queryFn: async () => {
      // Fetch cru (sem o client de http.ts, que injeta JWT). getApiBaseUrl() garante
      // a base correta tanto em prod (mesma origem) quanto em dev (proxy do Vite).
      const res = await fetch(`${getApiBaseUrl()}/pedidos/track/${encodeURIComponent(token!)}`, {
        headers: { Accept: 'application/json' },
      });
      if (res.status === 404) return { notFound: true };
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      const json = await res.json();
      if (!json?.pedido) return { notFound: true };
      return { pedido: json.pedido as PublicPedido };
    },
  });

  const pedido = data?.pedido ?? null;
  const estado: Estado = !token
    ? 'nao_encontrado'
    : isPending
      ? 'carregando'
      : isError
        ? 'erro'
        : data?.notFound || !pedido
          ? 'nao_encontrado'
          : 'ok';

  const isRetirada = (pedido?.tipo_pedido || '').toLowerCase().includes('retirada');
  const steps = isRetirada ? STEPS_RETIRADA : STEPS_ENTREGA;
  const passo = pedido ? activeStep(pedido.status_key, isRetirada) : 0;

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: 'background.default',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        py: { xs: 3, sm: 6 },
        px: 2,
      }}
    >
      {/* Cabeçalho de marca */}
      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 3 }}>
        <BrandLogo size={40} color="#143d28" />
        <Box>
          <Typography
            variant="h5"
            sx={{ color: 'primary.main', lineHeight: 1.1, fontWeight: 700 }}
          >
            Plante uma Flor
          </Typography>
          <Typography variant="caption" sx={{ color: 'secondary.dark', letterSpacing: 1 }}>
            ACOMPANHE SEU PEDIDO
          </Typography>
        </Box>
      </Stack>

      <Container maxWidth="sm" disableGutters>
        <Paper sx={{ p: { xs: 2.5, sm: 4 } }}>
          {estado === 'carregando' && (
            <Box display="flex" justifyContent="center" py={6}>
              <CircularProgress />
            </Box>
          )}

          {(estado === 'nao_encontrado' || estado === 'erro') && (
            <Stack spacing={1.5} alignItems="center" py={5} textAlign="center">
              <LocalFlorist sx={{ fontSize: 48, color: 'secondary.main' }} />
              <Typography variant="h6" sx={{ color: 'primary.main' }}>
                {estado === 'nao_encontrado' ? 'Pedido não encontrado' : 'Não foi possível carregar'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {estado === 'nao_encontrado'
                  ? 'O link pode estar incorreto ou ter expirado. Confira a mensagem que você recebeu.'
                  : 'Tente novamente em alguns instantes.'}
              </Typography>
            </Stack>
          )}

          {estado === 'ok' && pedido && (
            <Stack spacing={3}>
              <Stack spacing={1} alignItems="center" textAlign="center">
                <Chip
                  label={pedido.status}
                  color="primary"
                  sx={{ fontWeight: 700, px: 1, fontSize: '0.95rem' }}
                />
                <Typography variant="h6" sx={{ color: 'primary.main', mt: 0.5 }}>
                  {pedido.produto || 'Seu pedido'}
                </Typography>
                {pedido.destinatario && (
                  <Typography variant="body2" color="text.secondary">
                    Para: <strong>{pedido.destinatario}</strong>
                  </Typography>
                )}
              </Stack>

              <Divider />

              <Stack spacing={1.2}>
                {pedido.dia_entrega && (
                  <Stack direction="row" spacing={1} alignItems="center">
                    <CalendarMonth sx={{ fontSize: 20, color: 'secondary.dark' }} />
                    <Typography variant="body2">
                      {isRetirada ? 'Retirada' : 'Entrega'} em <strong>{pedido.dia_entrega}</strong>
                    </Typography>
                  </Stack>
                )}
                {pedido.janela && (
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Schedule sx={{ fontSize: 20, color: 'secondary.dark' }} />
                    <Typography variant="body2">
                      Horário: <strong>{pedido.janela}</strong>
                    </Typography>
                  </Stack>
                )}
              </Stack>

              <Stepper activeStep={passo} alternativeLabel>
                {steps.map((label) => (
                  <Step key={label}>
                    <StepLabel>{label}</StepLabel>
                  </Step>
                ))}
              </Stepper>
            </Stack>
          )}
        </Paper>

        <Typography
          variant="caption"
          display="block"
          textAlign="center"
          color="text.secondary"
          sx={{ mt: 3 }}
        >
          Plante uma Flor 🌹 Floricultura
        </Typography>
      </Container>
    </Box>
  );
}
