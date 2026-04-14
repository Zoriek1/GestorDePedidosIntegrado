import React, { useEffect } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  FormControl, 
  FormLabel, 
  RadioGroup, 
  FormControlLabel, 
  Radio, 
  TextField, 
  Button, 
  IconButton,
  Grid,
  InputAdornment,
  Alert,
  Divider,
  Stack
} from '@mui/material';
import { Add, Delete, Save } from '@mui/icons-material';
import { useForm, useFieldArray, Controller, useWatch } from 'react-hook-form';
import { useTaxaEntregaConfig } from '../hooks/useConfig';
import { TaxaEntregaConfig } from '../services/configService';
import { Loading } from '../../../components/common/Loading';
import { useToast } from '../../../components/system/useToast';

export function TaxaEntregaSettings() {
  const { config, isLoading, error, updateConfig, isUpdating } = useTaxaEntregaConfig();
  const { success, error: showError } = useToast();

  const { control, handleSubmit, reset } = useForm<TaxaEntregaConfig>({
    defaultValues: {
      tipo: 'faixas',
      faixas: [],
      valor_por_km: 2.50,
      taxa_base: 5.00,
      taxa_minima: 5.00,
      taxa_maxima: 50.00,
    }
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "faixas"
  });

  // Load initial data
  useEffect(() => {
    if (config) {
      reset(config);
    }
  }, [config, reset]);

  const tipo = useWatch({ control, name: "tipo" });

  const onSubmit = async (data: TaxaEntregaConfig) => {
    try {
        // Converter strings para números se necessário
        const formattedData = {
            ...data,
            valor_por_km: Number(data.valor_por_km),
            taxa_base: Number(data.taxa_base),
            taxa_minima: Number(data.taxa_minima),
            taxa_maxima: Number(data.taxa_maxima),
            faixas: data.faixas?.map(f => ({
                ...f,
                de_km: Number(f.de_km || 0),
                ate_km: f.ate_km === null || f.ate_km === undefined || String(f.ate_km) === '' ? null : Number(f.ate_km),
                taxa: Number(f.taxa)
            }))
        };

        await updateConfig(formattedData);
        success('Configurações salvas com sucesso');
    } catch (err) {
        showError(err instanceof Error ? err.message : 'Erro ao salvar');
    }
  };

  if (isLoading) return <Loading />;
  if (error) return <Alert severity="error">{error.message}</Alert>;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Cálculo de Taxa de Entrega
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Defina como o sistema deve calcular o valor da entrega com base na distância.
        </Typography>

        <form onSubmit={handleSubmit(onSubmit)}>
          <FormControl component="fieldset" margin="normal">
            <FormLabel component="legend">Método de Cálculo</FormLabel>
            <Controller
              name="tipo"
              control={control}
              render={({ field }) => (
                <RadioGroup row {...field}>
                  <FormControlLabel value="faixas" control={<Radio />} label="Por Faixas de Distância" />
                  <FormControlLabel value="por_km" control={<Radio />} label="Valor por KM" />
                </RadioGroup>
              )}
            />
          </FormControl>

          <Divider sx={{ my: 2 }} />

          {tipo === 'por_km' && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="taxa_base"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Taxa Base (R$)"
                      type="number"
                      fullWidth
                      InputProps={{
                        startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                      }}
                      helperText="Valor inicial fixo"
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="valor_por_km"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Valor por KM (R$)"
                      type="number"
                      fullWidth
                      InputProps={{
                        startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                      }}
                      helperText="Adicionado a cada KM de distância"
                    />
                  )}
                />
              </Grid>
            </Grid>
          )}

          {tipo === 'faixas' && (
            <Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="subtitle1">Faixas de Distância</Typography>
                <Button 
                  startIcon={<Add />} 
                  variant="outlined" 
                  size="small"
                  onClick={() => append({ de_km: 0, ate_km: 5, taxa: 10, descricao: '' })}
                >
                  Adicionar Faixa
                </Button>
              </Box>

              <Stack spacing={2}>
                {fields.map((field, index) => (
                  <Box key={field.id} sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: { xs: 'wrap', md: 'nowrap' } }}>
                    <Controller
                      name={`faixas.${index}.de_km`}
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="De (km)"
                          type="number"
                          size="small"
                          sx={{ width: { xs: '45%', md: 100 } }}
                        />
                      )}
                    />
                    <Controller
                      name={`faixas.${index}.ate_km`}
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="Até (km)"
                          type="number"
                          size="small"
                          sx={{ width: { xs: '45%', md: 100 } }}
                          helperText={field.value === null || field.value === undefined || field.value === '' ? "Infinito" : ""}
                          placeholder="∞"
                        />
                      )}
                    />
                    <Controller
                      name={`faixas.${index}.taxa`}
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="Valor (R$)"
                          type="number"
                          size="small"
                          sx={{ width: { xs: '100%', md: 120 } }}
                          InputProps={{
                            startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                          }}
                        />
                      )}
                    />
                     <Controller
                      name={`faixas.${index}.descricao`}
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="Descrição (Opcional)"
                          size="small"
                          fullWidth
                        />
                      )}
                    />
                    <IconButton color="error" onClick={() => remove(index)} size="small" sx={{ mt: 1 }}>
                      <Delete />
                    </IconButton>
                  </Box>
                ))}
                {fields.length === 0 && (
                    <Alert severity="info">Nenhuma faixa definida. Adicione faixas para configurar os preços.</Alert>
                )}
              </Stack>
            </Box>
          )}

          <Divider sx={{ my: 3 }} />

          <Typography variant="subtitle2" gutterBottom>Limites Globais</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="taxa_minima"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Taxa Mínima (R$)"
                    type="number"
                    fullWidth
                    size="small"
                    InputProps={{
                      startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                    }}
                    helperText="Nenhuma entrega será menor que este valor"
                  />
                )}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Controller
                name="taxa_maxima"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Taxa Máxima (R$)"
                    type="number"
                    fullWidth
                    size="small"
                    InputProps={{
                      startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                    }}
                    helperText="Nenhuma entrega será maior que este valor"
                  />
                )}
              />
            </Grid>
          </Grid>

          <Box mt={3} display="flex" justifyContent="flex-end">
            <Button
              type="submit"
              variant="contained"
              color="primary"
              startIcon={<Save />}
              disabled={isUpdating}
            >
              {isUpdating ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </Box>
        </form>
      </CardContent>
    </Card>
  );
}
