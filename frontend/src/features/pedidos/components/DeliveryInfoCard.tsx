/**
 * DeliveryInfoCard — "visão do entregador"
 * Bloco que espelha o que vai para o entregador (tela + impressão): destinatário em
 * destaque, endereço, tipo + nome do local, detalhe do prédio (AP/Bloco/Torre/Andar),
 * ponto de referência, horário e telefone.
 *
 * Reusado no preview ao vivo da etapa Entrega do wizard e no card operacional do
 * entregador, para que ambos mostrem exatamente o mesmo formato.
 */

import { Box, Chip, Stack, Typography } from '@mui/material';
import HomeOutlinedIcon from '@mui/icons-material/HomeOutlined';
import ApartmentOutlinedIcon from '@mui/icons-material/ApartmentOutlined';
import StorefrontOutlinedIcon from '@mui/icons-material/StorefrontOutlined';
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import PhoneIcon from '@mui/icons-material/Phone';
import PrintOutlinedIcon from '@mui/icons-material/PrintOutlined';
import { getDetalheLocal, getTipoLocalLabel } from './OrderCardHelpers';

const TIPO_ICON = {
  casa: HomeOutlinedIcon,
  predio: ApartmentOutlinedIcon,
  comercial: StorefrontOutlinedIcon,
} as const;

export interface DeliveryInfoCardProps {
  destinatario?: string;
  endereco?: string;
  tipoLocal?: 'casa' | 'predio' | 'comercial' | string;
  nomeLocal?: string;
  apartamento?: string;
  bloco?: string;
  torre?: string;
  andar?: string;
  referencia?: string;
  horario?: string;
  telefone?: string;
  /** Esconde o cabeçalho "Visão do entregador" (quando já há um título externo). */
  hideHeader?: boolean;
}

export function DeliveryInfoCard({
  destinatario,
  endereco,
  tipoLocal = 'casa',
  nomeLocal,
  apartamento,
  bloco,
  torre,
  andar,
  referencia,
  horario,
  telefone,
  hideHeader = false,
}: DeliveryInfoCardProps) {
  const tipoKey = (tipoLocal as keyof typeof TIPO_ICON) in TIPO_ICON ? (tipoLocal as keyof typeof TIPO_ICON) : 'casa';
  const TipoIcon = TIPO_ICON[tipoKey];
  const detalhe = getDetalheLocal({ apartamento, bloco, torre, andar });
  const mostraLocal = tipoKey !== 'casa' && !!nomeLocal;

  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        p: 1.75,
        bgcolor: 'background.paper',
      }}
    >
      {!hideHeader && (
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
          <Stack direction="row" alignItems="center" spacing={0.5} sx={{ color: 'text.secondary' }}>
            <PrintOutlinedIcon sx={{ fontSize: 15 }} />
            <Typography variant="caption" sx={{ fontWeight: 700, letterSpacing: 0.4, textTransform: 'uppercase' }}>
              Visão do entregador
            </Typography>
          </Stack>
          <Chip
            size="small"
            color="primary"
            icon={<TipoIcon sx={{ fontSize: 14 }} />}
            label={getTipoLocalLabel(tipoLocal)}
            sx={{ fontWeight: 700 }}
          />
        </Stack>
      )}

      <Typography sx={{ fontWeight: 800, fontSize: '1.1rem', lineHeight: 1.2 }}>
        {destinatario || '—'}
      </Typography>

      {endereco && (
        <Stack direction="row" alignItems="flex-start" spacing={0.5} sx={{ mt: 0.5 }}>
          <PlaceOutlinedIcon sx={{ fontSize: 16, color: 'text.secondary', mt: '2px' }} />
          <Typography variant="body2" color="text.secondary">
            {endereco}
          </Typography>
        </Stack>
      )}

      {mostraLocal && (
        <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mt: 0.75 }}>
          <TipoIcon sx={{ fontSize: 16, color: 'primary.main' }} />
          <Typography variant="body2" sx={{ fontWeight: 700, color: 'primary.main' }}>
            {nomeLocal}
          </Typography>
        </Stack>
      )}

      {detalhe && (
        <Box
          sx={{
            display: 'inline-block',
            mt: 0.75,
            px: 1,
            py: 0.25,
            borderRadius: 1,
            bgcolor: 'action.selected',
            fontWeight: 700,
            fontSize: '0.8rem',
          }}
        >
          {detalhe}
        </Box>
      )}

      {referencia && (
        <Stack direction="row" alignItems="flex-start" spacing={0.5} sx={{ mt: 0.75 }}>
          <PlaceOutlinedIcon sx={{ fontSize: 15, color: 'text.secondary', mt: '2px' }} />
          <Typography variant="caption" color="text.secondary">
            Ref.: {referencia}
          </Typography>
        </Stack>
      )}

      {(horario || telefone) && (
        <Stack
          direction="row"
          justifyContent="space-between"
          sx={{ mt: 1, pt: 1, borderTop: '1px dashed', borderColor: 'divider', color: 'text.secondary' }}
        >
          {horario && (
            <Stack direction="row" alignItems="center" spacing={0.5}>
              <AccessTimeIcon sx={{ fontSize: 14 }} />
              <Typography variant="caption">{horario}</Typography>
            </Stack>
          )}
          {telefone && (
            <Stack direction="row" alignItems="center" spacing={0.5}>
              <PhoneIcon sx={{ fontSize: 14 }} />
              <Typography variant="caption">{telefone}</Typography>
            </Stack>
          )}
        </Stack>
      )}
    </Box>
  );
}

export default DeliveryInfoCard;
