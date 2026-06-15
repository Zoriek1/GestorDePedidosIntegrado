/**
 * Step 3 - Dados do Produto
 * O que será entregue
 */

import { useState, useEffect } from 'react';
import { useFormContext, Controller, useWatch } from 'react-hook-form';
import {
  Box,
  TextField,
  Typography,
  Stack,
  Grid,
  Button,
  FormHelperText,
  Autocomplete,
} from '@mui/material';
import { FloristDatePicker } from '../FloristDatePicker';
import LocalFloristIcon from '@mui/icons-material/LocalFlorist';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import AddIcon from '@mui/icons-material/Add';
import dayjs from 'dayjs';
import { CurrencyInput } from '../../../../components/form';
import { TimeSlotDialog } from '../TimeSlotDialog';
import type { PedidoFormData } from '../../schemas';
import { getFloristHoliday } from '../../utils/floristHolidays';
import { useArranjoSugestoes, usePromoverArranjo } from '../../services/catalogoApi';
import { useToast } from '../../../../components/system/useToast';

/** Debounce simples para não bater no endpoint a cada tecla (CAT-01). */
function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

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

  // CAT-01: autocomplete do catálogo de arranjos para o campo `produto`.
  const produtoAtual = useWatch({ control, name: 'produto' }) || '';
  const produtoDebounced = useDebouncedValue(produtoAtual.trim(), 300);
  const { data: sugestoesArranjo = [] } = useArranjoSugestoes(
    produtoDebounced,
    produtoDebounced.length >= 2
  );
  const promoverArranjo = usePromoverArranjo();
  const toast = useToast();
  const jaNoCatalogo = sugestoesArranjo.some(
    (s) => s.toLowerCase() === produtoAtual.trim().toLowerCase()
  );

  const selectedHoliday = diaEntrega ? getFloristHoliday(dayjs(diaEntrega)) : null;

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
            {/* Descrição do Produto — combobox do catálogo curado (CAT-01) */}
            <Controller
              name="produto"
              control={control}
              render={({ field }) => (
                <Box>
                  <Autocomplete
                    freeSolo
                    options={sugestoesArranjo}
                    inputValue={field.value || ''}
                    onInputChange={(_e, value) => field.onChange(value)}
                    onChange={(_e, value) => field.onChange(value || '')}
                    filterOptions={(opts) => opts}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="Descrição do Produto"
                        placeholder="Ex: Buquê de 12 rosas vermelhas com folhagens"
                        multiline
                        minRows={2}
                        fullWidth
                        required
                        error={!!errors.produto}
                        helperText={
                          errors.produto?.message ||
                          'Sugestões do catálogo aparecem ao digitar; nome novo é sempre aceito'
                        }
                      />
                    )}
                  />
                  {produtoAtual.trim().length >= 2 && !jaNoCatalogo && (
                    <Button
                      size="small"
                      startIcon={<AddIcon />}
                      sx={{ mt: 0.5, textTransform: 'none' }}
                      disabled={promoverArranjo.isPending}
                      onClick={async () => {
                        const nome = produtoAtual.trim();
                        try {
                          await promoverArranjo.mutateAsync(nome);
                          toast.success(`"${nome}" adicionado ao catálogo`);
                        } catch (e) {
                          toast.error(
                            e instanceof Error ? e.message : 'Erro ao adicionar ao catálogo'
                          );
                        }
                      }}
                    >
                      Adicionar "{produtoAtual.trim()}" ao catálogo
                    </Button>
                  )}
                </Box>
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
                  <FloristDatePicker
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
              {selectedHoliday ? (
                <Box
                  sx={{
                    mt: 1,
                    px: 1.25,
                    py: 0.75,
                    borderRadius: 1,
                    backgroundColor: `${selectedHoliday.color}1f`,
                    color: selectedHoliday.color,
                    fontWeight: 600,
                    fontSize: 13,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.75,
                  }}
                >
                  <LocalFloristIcon fontSize="small" /> {selectedHoliday.name}
                  {selectedHoliday.tier === 'peak' && ' — pico de demanda'}
                </Box>
              ) : null}
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

