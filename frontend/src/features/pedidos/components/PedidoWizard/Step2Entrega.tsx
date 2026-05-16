/**
 * Step 2 - Dados da Entrega
 * Onde e quando será entregue
 */

import { useFormContext, Controller, useWatch } from 'react-hook-form';
import {
  Box,
  TextField,
  Typography,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Collapse,
  FormHelperText,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import dayjs from 'dayjs';
import type { PedidoFormData } from '../../schemas';
import { TIPOS_PEDIDO } from '../../schemas';

export function Step2Entrega() {
  const {
    control,
    setValue,
    formState: { errors },
  } = useFormContext<PedidoFormData>();

  // Watch tipo_pedido para mostrar/esconder endereço
  const tipoPedido = useWatch({ control, name: 'tipo_pedido' });
  const isEntrega = tipoPedido === 'Entrega';

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 3 }}>
        <LocalShippingIcon color="primary" />
        <Typography variant="h6" component="h2">
          Dados da Entrega
        </Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Informe quando e onde o pedido será entregue.
      </Typography>

      <Stack spacing={3}>
        {/* Tipo de Pedido */}
        <Controller
          name="tipo_pedido"
          control={control}
          render={({ field }) => (
            <FormControl fullWidth required error={!!errors.tipo_pedido}>
              <InputLabel>Tipo de Pedido</InputLabel>
              <Select {...field} label="Tipo de Pedido">
                {TIPOS_PEDIDO.map((tipo) => (
                  <MenuItem key={tipo} value={tipo}>
                    {tipo}
                  </MenuItem>
                ))}
              </Select>
              {errors.tipo_pedido && (
                <FormHelperText>{errors.tipo_pedido.message}</FormHelperText>
              )}
            </FormControl>
          )}
        />

        {/* Destinatário */}
        <Controller
          name="destinatario"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="Nome do Destinatário"
              placeholder="Quem vai receber as flores"
              fullWidth
              required
              error={!!errors.destinatario}
              helperText={errors.destinatario?.message}
            />
          )}
        />

        {/* Data e Horário */}
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Controller
              name="dia_entrega"
              control={control}
              render={({ field }) => (
                <DatePicker
                  label="Data da Entrega"
                  value={field.value ? dayjs(field.value) : null}
                  onChange={(newValue) => {
                    setValue('dia_entrega', newValue ? newValue.format('YYYY-MM-DD') : '');
                  }}
                  minDate={dayjs()}
                  slotProps={{
                    textField: {
                      fullWidth: true,
                      required: true,
                      error: !!errors.dia_entrega,
                      helperText: errors.dia_entrega?.message,
                    },
                  }}
                />
              )}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Controller
              name="horario"
              control={control}
              render={({ field }) => (
                <TimePicker
                  label="Horário da Entrega"
                  value={field.value ? dayjs(`2000-01-01 ${field.value}`) : null}
                  onChange={(newValue) => {
                    setValue('horario', newValue ? newValue.format('HH:mm') : '');
                  }}
                  ampm={false}
                  slotProps={{
                    textField: {
                      fullWidth: true,
                      required: true,
                      error: !!errors.horario,
                      helperText: errors.horario?.message || 'Formato: HH:MM',
                    },
                  }}
                />
              )}
            />
          </Grid>
        </Grid>

        {/* Campos de Endereço - Apenas para Entrega */}
        <Collapse in={isEntrega}>
          <Stack spacing={2}>
            <Typography variant="subtitle2" color="text.secondary">
              Endereço de Entrega
            </Typography>

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Controller
                  name="cep"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="CEP"
                      placeholder="00000-000"
                      fullWidth
                      error={!!errors.cep}
                      helperText={errors.cep?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 8 }}>
                <Controller
                  name="rua"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Rua/Logradouro"
                      placeholder="Nome da rua"
                      fullWidth
                      required={isEntrega}
                      error={!!errors.rua}
                      helperText={errors.rua?.message}
                    />
                  )}
                />
              </Grid>
            </Grid>

            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Controller
                  name="numero"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Número"
                      placeholder="123"
                      fullWidth
                      required={isEntrega}
                      error={!!errors.numero}
                      helperText={errors.numero?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 4 }}>
                <Controller
                  name="bairro"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Bairro"
                      fullWidth
                      error={!!errors.bairro}
                      helperText={errors.bairro?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 5 }}>
                <Controller
                  name="cidade"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Cidade"
                      fullWidth
                      required={isEntrega}
                      error={!!errors.cidade}
                      helperText={errors.cidade?.message}
                    />
                  )}
                />
              </Grid>
            </Grid>

            {/* Quadra e Lote - opcionais para loteamentos */}
            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 4 }}>
                <Controller
                  name="quadra"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Quadra"
                      placeholder="Ex: 5"
                      fullWidth
                      error={!!errors.quadra}
                      helperText={errors.quadra?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 4 }}>
                <Controller
                  name="lote"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Lote"
                      placeholder="Ex: 12"
                      fullWidth
                      error={!!errors.lote}
                      helperText={errors.lote?.message}
                    />
                  )}
                />
              </Grid>
            </Grid>

            <Controller
              name="obs_entrega"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Ponto de Referência / Observações de Entrega"
                  placeholder="Ex: Casa amarela, portão preto"
                  multiline
                  rows={2}
                  fullWidth
                  error={!!errors.obs_entrega}
                  helperText={errors.obs_entrega?.message}
                />
              )}
            />
          </Stack>
        </Collapse>
      </Stack>
    </Box>
  );
}

export default Step2Entrega;

