/**
 * Step 1 - Dados do Cliente
 * Quem está fazendo o pedido (remetente)
 */

import { useFormContext, Controller } from 'react-hook-form';
import {
  Box,
  TextField,
  Typography,
  Stack,
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import { PhoneInput } from '../../../../components/form';
import type { PedidoFormData } from '../../schemas';

export function Step1Cliente() {
  const {
    control,
    formState: { errors },
  } = useFormContext<PedidoFormData>();

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
      </Stack>
    </Box>
  );
}

export default Step1Cliente;

