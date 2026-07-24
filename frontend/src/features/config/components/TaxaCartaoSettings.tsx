import { useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  IconButton,
  Grid,
  InputAdornment,
  Alert,
  Divider,
  Stack,
} from '@mui/material';
import { Add, Delete, Save } from '@mui/icons-material';
import { useForm, useFieldArray, Controller } from 'react-hook-form';
import { useTaxaCartaoConfig } from '../hooks/useConfig';
import { TaxaCartaoConfig } from '../services/configService';
import { Loading } from '../../../components/common/Loading';
import { useToast } from '../../../components/system/useToast';

export function TaxaCartaoSettings() {
  const { config, isLoading, error, updateConfig, isUpdating } = useTaxaCartaoConfig();
  const { success, error: showError } = useToast();

  const { control, handleSubmit, reset } = useForm<TaxaCartaoConfig>({
    defaultValues: {
      debito_pct: 0,
      credito: [],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'credito',
    keyName: '_fieldId',
  });

  useEffect(() => {
    if (config) {
      reset({
        debito_pct: Number(config.debito_pct ?? 0),
        credito: (config.credito ?? []).map((f) => ({
          parcelas: Number(f.parcelas),
          taxa_pct: Number(f.taxa_pct),
        })),
      });
    }
  }, [config, reset]);

  const onSubmit = async (data: TaxaCartaoConfig) => {
    try {
      const payload: TaxaCartaoConfig = {
        debito_pct: Number(data.debito_pct ?? 0),
        credito: (data.credito ?? [])
          .map((f) => ({
            parcelas: Number(f.parcelas),
            taxa_pct: Number(f.taxa_pct),
          }))
          .filter((f) => Number.isFinite(f.parcelas) && f.parcelas >= 1)
          .sort((a, b) => a.parcelas - b.parcelas),
      };
      await updateConfig(payload);
      success('Taxas de cartão salvas');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao salvar taxas de cartão');
    }
  };

  if (isLoading) return <Loading />;
  if (error) return <Alert severity="error">{(error as Error).message}</Alert>;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Taxas do Cartão
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Configure a taxa cobrada pelo adquirente em débito e em cada faixa de parcelas do crédito.
          O valor é descontado do "Valor Líquido" do pedido e da base da comissão.
        </Typography>

        <form onSubmit={handleSubmit(onSubmit)}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Controller
                name="debito_pct"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Taxa do Débito"
                    type="number"
                    fullWidth
                    inputProps={{ step: '0.01', min: 0, max: 100 }}
                    InputProps={{
                      endAdornment: <InputAdornment position="end">%</InputAdornment>,
                    }}
                    helperText="% cobrado em cada transação no débito"
                  />
                )}
              />
            </Grid>
          </Grid>

          <Divider sx={{ my: 3 }} />

          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="subtitle1">Crédito por número de parcelas</Typography>
            <Button
              startIcon={<Add />}
              variant="outlined"
              size="small"
              onClick={() => {
                const next = (fields[fields.length - 1] as unknown as { parcelas?: number })?.parcelas;
                append({ parcelas: Number(next || 0) + 1, taxa_pct: 0 });
              }}
            >
              Adicionar parcela
            </Button>
          </Box>

          <Stack spacing={2}>
            {fields.map((field, index) => (
              <Box
                key={field._fieldId}
                sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}
              >
                <Controller
                  name={`credito.${index}.parcelas`}
                  control={control}
                  render={({ field: f }) => (
                    <TextField
                      {...f}
                      label="Parcelas"
                      type="number"
                      size="small"
                      sx={{ width: 110 }}
                      inputProps={{ min: 1, max: 24, step: 1 }}
                    />
                  )}
                />
                <Controller
                  name={`credito.${index}.taxa_pct`}
                  control={control}
                  render={({ field: f }) => (
                    <TextField
                      {...f}
                      label="Taxa"
                      type="number"
                      size="small"
                      sx={{ width: 140 }}
                      inputProps={{ step: '0.01', min: 0, max: 100 }}
                      InputProps={{
                        endAdornment: <InputAdornment position="end">%</InputAdornment>,
                      }}
                    />
                  )}
                />
                <IconButton color="error" onClick={() => remove(index)} size="small" sx={{ mt: 1 }}>
                  <Delete />
                </IconButton>
              </Box>
            ))}
            {fields.length === 0 && (
              <Alert severity="info">
                Nenhuma faixa configurada. Adicione ao menos a faixa de 1 parcela (à vista).
              </Alert>
            )}
          </Stack>

          <Box mt={3} display="flex" justifyContent="flex-end">
            <Button
              type="submit"
              variant="contained"
              color="primary"
              startIcon={<Save />}
              disabled={isUpdating}
            >
              {isUpdating ? 'Salvando…' : 'Salvar taxas'}
            </Button>
          </Box>
        </form>
      </CardContent>
    </Card>
  );
}
