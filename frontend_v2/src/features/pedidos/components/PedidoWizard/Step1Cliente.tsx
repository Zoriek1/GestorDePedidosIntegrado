/**
 * Step 1 - Dados do Cliente
 * Quem está fazendo o pedido (remetente)
 */

import { useFormContext, Controller, useWatch } from 'react-hook-form';
import {
  Box,
  TextField,
  Typography,
  Stack,
  FormControlLabel,
  Checkbox,
  Collapse,
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import { PhoneInput } from '../../../../components/form';
import type { PedidoFormData } from '../../schemas';

export function Step1Cliente() {
  const {
    control,
    setValue,
    formState: { errors },
  } = useFormContext<PedidoFormData>();

  const origemAnuncio = useWatch({ control, name: 'origem_anuncio' });

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 3 }}>
        <PersonIcon color="primary" />
        <Typography variant="h6" component="h2">
          Dados do Cliente
        </Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Informe os dados de quem está fazendo o pedido (remetente).
      </Typography>

      <Stack spacing={3}>
        {/* Nome do Cliente */}
        <Controller
          name="cliente"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="Nome do Cliente"
              placeholder="Ex: Maria Silva"
              fullWidth
              required
              error={!!errors.cliente}
              helperText={errors.cliente?.message}
              autoFocus
            />
          )}
        />

        {/* Telefone/WhatsApp */}
        <Controller
          name="telefone_cliente"
          control={control}
          render={({ field }) => (
            <PhoneInput
              {...field}
              label="Telefone/WhatsApp"
              fullWidth
              required
              error={!!errors.telefone_cliente}
              helperText={errors.telefone_cliente?.message || 'Formato: (00) 00000-0000'}
            />
          )}
        />

        {/* Origem: anúncio Meta Ads */}
        <Controller
          name="origem_anuncio"
          control={control}
          render={({ field }) => (
            <FormControlLabel
              control={
                <Checkbox
                  checked={field.value ?? false}
                  onChange={(e) => {
                    field.onChange(e.target.checked);
                    if (!e.target.checked) setValue('fbclid', '');
                  }}
                />
              }
              label="Pedido vindo de anúncio?"
            />
          )}
        />

        <Collapse in={origemAnuncio}>
          <Controller
            name="fbclid"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Facebook Click ID (fbclid)"
                placeholder="Ex: AbCdEfGhIjKlMnOpQrStUvWxYz"
                fullWidth
                required={origemAnuncio}
                error={!!errors.fbclid}
                helperText={errors.fbclid?.message || 'Cole o fbclid da mensagem do WhatsApp'}
              />
            )}
          />
        </Collapse>
      </Stack>
    </Box>
  );
}

export default Step1Cliente;

