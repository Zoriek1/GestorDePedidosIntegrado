/**
 * Step 3 - Dados do Produto
 * O que será entregue
 */

import { useFormContext, Controller } from 'react-hook-form';
import {
  Box,
  TextField,
  Typography,
  Stack,
} from '@mui/material';
import LocalFloristIcon from '@mui/icons-material/LocalFlorist';
import { CurrencyInput } from '../../../../components/form';
import type { PedidoFormData } from '../../schemas';

export function Step3Produto() {
  const {
    control,
    formState: { errors },
  } = useFormContext<PedidoFormData>();

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 3 }}>
        <LocalFloristIcon color="primary" />
        <Typography variant="h6" component="h2">
          Dados do Produto
        </Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Descreva o produto e adicione a mensagem do cartão.
      </Typography>

      <Stack spacing={3}>
        {/* Descrição do Produto */}
        <Controller
          name="produto"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="Descrição do Produto"
              placeholder="Ex: Buquê de 12 rosas vermelhas com folhagens"
              multiline
              rows={3}
              fullWidth
              required
              error={!!errors.produto}
              helperText={errors.produto?.message}
            />
          )}
        />

        {/* Flores e Cores (opcional) */}
        <Controller
          name="flores_cor"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="Flores e Cores (detalhamento)"
              placeholder="Ex: Rosas vermelhas, astromélias brancas, folhagens"
              fullWidth
              error={!!errors.flores_cor}
              helperText={errors.flores_cor?.message}
            />
          )}
        />

        {/* Mensagem do Cartão */}
        <Controller
          name="mensagem"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="Mensagem do Cartão"
              placeholder="Digite a dedicatória que irá no cartão…"
              multiline
              minRows={3}
              maxRows={8}
              fullWidth
              error={!!errors.mensagem}
              helperText={
                errors.mensagem?.message ||
                `${field.value?.length || 0}/1000 caracteres`
              }
              inputProps={{ maxLength: 1000 }}
            />
          )}
        />

        {/* Valor do Produto */}
        <Controller
          name="valor"
          control={control}
          render={({ field }) => (
            <CurrencyInput
              {...field}
              label="Valor do Produto"
              fullWidth
              required
              error={!!errors.valor}
              helperText={errors.valor?.message || 'Valor em reais'}
            />
          )}
        />
      </Stack>
    </Box>
  );
}

export default Step3Produto;

