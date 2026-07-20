import { useEffect } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { Save } from 'lucide-react';
import { Controller, useForm } from 'react-hook-form';
import { Loading } from '../../../components/common/Loading';
import { useConfirm } from '../../../components/system/useConfirm';
import { useToast } from '../../../components/system/useToast';
import { useIntegrationSettings } from '../hooks/useConfig';
import type { IntegrationSettingsPayload } from '../services/configService';

const defaults: IntegrationSettingsPayload = {
  marketing_dispatch_enabled: false,
  meta_pixel_id: '',
  meta_capi_access_token: '',
  ga4_measurement_id: '',
  ga4_api_secret: '',
  ga4_validate_only: false,
  google_datamanager_enabled: false,
  google_ads_customer_id: '',
  google_ads_conversion_action_id: '',
  utmify_enabled: false,
  utmify_api_token: '',
  utmify_platform: 'WhatsAppManual',
  utmify_is_test: false,
  endereco_floricultura: '',
  loja_cep: '',
};

function SecretField(props: {
  name: keyof IntegrationSettingsPayload;
  label: string;
  control: ReturnType<typeof useForm<IntegrationSettingsPayload>>['control'];
  hasSecret: boolean;
}) {
  const confirm = useConfirm();
  return (
    <Controller
      name={props.name}
      control={props.control}
      render={({ field }) => (
        <Stack spacing={1}>
          <TextField
            {...field}
            value={field.value ?? ''}
            label={props.label}
            type="password"
            fullWidth
            autoComplete="new-password"
            helperText="Deixe o valor mascarado para manter a credencial atual."
          />
          {props.hasSecret && (
            <Button
              color="error"
              size="small"
              sx={{ alignSelf: 'flex-start' }}
              onClick={async () => {
                const approved = await confirm({
                  title: `Remover ${props.label}`,
                  description: 'A integração deixará de funcionar até uma nova credencial ser salva.',
                  confirmText: 'Remover credencial',
                  confirmColor: 'error',
                });
                if (approved) field.onChange(null);
              }}
            >
              Remover credencial
            </Button>
          )}
        </Stack>
      )}
    />
  );
}

export function IntegrationSettings() {
  const { config, isLoading, error, updateConfig, isUpdating } = useIntegrationSettings();
  const toast = useToast();
  const { control, handleSubmit, reset } = useForm<IntegrationSettingsPayload>({
    defaultValues: defaults,
  });

  useEffect(() => {
    if (!config) return;
    const {
      store: _store,
      configured: _configured,
      has_meta_capi_access_token: _hasMeta,
      has_ga4_api_secret: _hasGa4,
      has_utmify_api_token: _hasUtmify,
      ...formConfig
    } = config;
    reset(formConfig);
  }, [config, reset]);

  const submit = async (values: IntegrationSettingsPayload) => {
    try {
      const payload = { ...values };
      for (const [field, hasSecret] of [
        ['meta_capi_access_token', config?.has_meta_capi_access_token],
        ['ga4_api_secret', config?.has_ga4_api_secret],
        ['utmify_api_token', config?.has_utmify_api_token],
      ] as const) {
        if (hasSecret && payload[field] === '') payload[field] = config?.[field] ?? null;
      }
      await updateConfig(payload);
      toast.success('Integrações atualizadas');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erro ao atualizar integrações');
    }
  };

  if (isLoading) return <Loading />;
  if (error) return <Alert severity="error">{(error as Error).message}</Alert>;

  return (
    <form onSubmit={handleSubmit(submit)}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h6">Integrações da loja</Typography>
          <Typography variant="body2" color="text.secondary">
            Configuração do tenant {config?.store.name} ({config?.store.slug}). Os segredos são
            armazenados criptografados e nunca retornam em texto puro.
          </Typography>
        </Box>

        <Alert severity="info">
          Nuvemshop e Bling continuam nas abas próprias porque usam conexão OAuth. Esta tela reúne
          as credenciais e os destinos que pertencem à loja.
        </Alert>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Meta e marketing</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 2 }}>
              <Box sx={{ gridColumn: { md: '1 / -1' } }}>
                <Controller name="marketing_dispatch_enabled" control={control} render={({ field }) => (
                  <FormControlLabel control={<Switch checked={field.value} onChange={(_, value) => field.onChange(value)} />} label="Enviar conversões de marketing" />
                )} />
              </Box>
              <Box>
                <Controller name="meta_pixel_id" control={control} render={({ field }) => <TextField {...field} value={field.value ?? ''} label="Meta Pixel ID" fullWidth />} />
              </Box>
              <Box>
                <SecretField name="meta_capi_access_token" label="Meta CAPI Access Token" control={control} hasSecret={Boolean(config?.has_meta_capi_access_token)} />
              </Box>
            </Box>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Google Analytics e Ads</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 2 }}>
              <Box>
                <Controller name="ga4_measurement_id" control={control} render={({ field }) => <TextField {...field} value={field.value ?? ''} label="GA4 Measurement ID" fullWidth />} />
              </Box>
              <Box>
                <SecretField name="ga4_api_secret" label="GA4 API Secret" control={control} hasSecret={Boolean(config?.has_ga4_api_secret)} />
              </Box>
              <Box>
                <Controller name="google_ads_customer_id" control={control} render={({ field }) => <TextField {...field} value={field.value ?? ''} label="Google Ads Customer ID" fullWidth />} />
              </Box>
              <Box>
                <Controller name="google_ads_conversion_action_id" control={control} render={({ field }) => <TextField {...field} value={field.value ?? ''} label="Conversion Action ID" fullWidth />} />
              </Box>
              <Box>
                <Controller name="ga4_validate_only" control={control} render={({ field }) => (
                  <FormControlLabel control={<Switch checked={field.value} onChange={(_, value) => field.onChange(value)} />} label="GA4 somente validação" />
                )} />
              </Box>
              <Box>
                <Controller name="google_datamanager_enabled" control={control} render={({ field }) => (
                  <FormControlLabel control={<Switch checked={field.value} onChange={(_, value) => field.onChange(value)} />} label="Google Data Manager ativo" />
                )} />
              </Box>
            </Box>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>UTMify</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 2 }}>
              <Box sx={{ gridColumn: { md: '1 / -1' } }}>
                <Controller name="utmify_enabled" control={control} render={({ field }) => (
                  <FormControlLabel control={<Switch checked={field.value} onChange={(_, value) => field.onChange(value)} />} label="UTMify ativa" />
                )} />
              </Box>
              <Box>
                <SecretField name="utmify_api_token" label="UTMify API Token" control={control} hasSecret={Boolean(config?.has_utmify_api_token)} />
              </Box>
              <Box>
                <Controller name="utmify_platform" control={control} render={({ field }) => <TextField {...field} value={field.value ?? ''} label="Plataforma" fullWidth />} />
              </Box>
              <Box sx={{ gridColumn: { md: '1 / -1' } }}>
                <Controller name="utmify_is_test" control={control} render={({ field }) => (
                  <FormControlLabel control={<Switch checked={field.value} onChange={(_, value) => field.onChange(value)} />} label="Ambiente de teste" />
                )} />
              </Box>
            </Box>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Dados operacionais da loja</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' }, gap: 2 }}>
              <Box>
                <Controller name="endereco_floricultura" control={control} render={({ field }) => <TextField {...field} value={field.value ?? ''} label="Endereço de origem" fullWidth />} />
              </Box>
              <Box>
                <Controller name="loja_cep" control={control} render={({ field }) => <TextField {...field} value={field.value ?? ''} label="CEP da loja" placeholder="00000-000" fullWidth />} />
              </Box>
            </Box>
          </CardContent>
        </Card>

        <Divider />
        <Box display="flex" justifyContent="flex-end">
          <Button type="submit" variant="contained" startIcon={<Save />} disabled={isUpdating}>
            {isUpdating ? 'Salvando…' : 'Salvar integrações'}
          </Button>
        </Box>
      </Stack>
    </form>
  );
}
