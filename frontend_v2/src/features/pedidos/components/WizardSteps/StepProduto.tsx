/**
 * Step 3 - Dados do Produto
 * O que será entregue
 */

import { useState } from 'react';
import { useFormContext, Controller, useWatch } from 'react-hook-form';
import {
  Box,
  TextField,
  Typography,
  Stack,
  Grid,
  Button,
  FormHelperText,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import LocalFloristIcon from '@mui/icons-material/LocalFlorist';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import dayjs from 'dayjs';
import { CurrencyInput } from '../../../../components/form';
import { TimeSlotDialog } from '../TimeSlotDialog';
import type { PedidoFormData } from '../../schemas';

// ============================================================================
// Componente
// ============================================================================

export function StepProduto() {
  const {
    control,
    setValue,
    formState: { errors },
  } = useFormContext<PedidoFormData>();

  const [showTimeDialog, setShowTimeDialog] = useState(false);
  const diaEntrega = useWatch({ control, name: 'dia_entrega' });
  const horario = useWatch({ control, name: 'horario' });

  const handleSelectSlot = (slot: string) => {
    setValue('horario', slot, { shouldValidate: true });
    setShowTimeDialog(false);
  };

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 3 }}>
        <LocalFloristIcon color="primary" />
        <Typography variant="h6" component="h2">
          Produto e Agendamento
        </Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Descreva o produto e informe quando será entregue.
      </Typography>

      <Stack spacing={2.5}>
        {/* Grid 1: Dados do Item */}
        <Box>
          <Typography variant="subtitle1" fontWeight="medium" sx={{ mb: 2 }}>
            Dados do Item
          </Typography>
          <Stack spacing={2.5}>
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

            <Grid container spacing={2}>
              {/* Flores e Cores (opcional) */}
              <Grid size={{ xs: 12, md: 6 }}>
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
              </Grid>

              {/* Valor */}
              <Grid size={{ xs: 12, md: 6 }}>
                <Controller
                  name="valor"
                  control={control}
                  render={({ field }) => (
                    <CurrencyInput
                      {...field}
                      label="Valor Total (R$)"
                      fullWidth
                      required
                      error={!!errors.valor}
                      helperText={errors.valor?.message || 'Valor em reais'}
                    />
                  )}
                />
              </Grid>
            </Grid>
          </Stack>
        </Box>

        {/* Grid 2: Agendamento */}
        <Box>
          <Typography variant="subtitle1" fontWeight="medium" sx={{ mb: 2 }}>
            Agendamento
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Controller
                name="dia_entrega"
                control={control}
                render={({ field }) => (
                  <DatePicker
                    label="Data de Entrega"
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
              <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Button
                  variant={horario ? 'contained' : 'outlined'}
                  color={errors.horario ? 'error' : 'primary'}
                  onClick={() => setShowTimeDialog(true)}
                  disabled={!diaEntrega}
                  startIcon={<AccessTimeIcon />}
                  sx={{ 
                    height: 56, 
                    flex: 1,
                    justifyContent: 'flex-start',
                    px: 2,
                  }}
                  fullWidth
                >
                  {horario ? `Horário: ${horario}` : 'Selecionar Horário *'}
                </Button>
                {errors.horario && (
                  <FormHelperText error sx={{ ml: 1.5 }}>
                    {errors.horario.message}
                  </FormHelperText>
                )}
                {!diaEntrega && (
                  <FormHelperText sx={{ ml: 1.5 }}>
                    Selecione a data primeiro
                  </FormHelperText>
                )}
              </Box>
            </Grid>
          </Grid>
        </Box>
      </Stack>

      {/* Modal de seleção de horário */}
      <TimeSlotDialog
        open={showTimeDialog}
        onClose={() => setShowTimeDialog(false)}
        date={diaEntrega || dayjs().format('YYYY-MM-DD')}
        onSelectSlot={handleSelectSlot}
        currentSlot={horario}
      />
    </Box>
  );
}

export default StepProduto;

