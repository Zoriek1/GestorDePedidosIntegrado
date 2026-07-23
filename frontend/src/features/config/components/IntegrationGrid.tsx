import { useEffect, useMemo, useState } from 'react';
import { Alert, Box, Button, Stack, Typography } from '@mui/material';
import { FlaskConical } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Loading } from '../../../components/common/Loading';
import { useToast } from '../../../components/system/useToast';
import {
  useIntegrationSettings,
  useOAuthDisconnect,
  useTestChannel,
} from '../hooks/useConfig';
import { IntegrationFieldService } from '../services/configService';
import { createApiRequest } from '../../../api/http';
import { useAuth } from '../../auth/authStore';
import { useStoreKey, tenantKey } from '../../../lib/tenantKey';
import { INTEGRATION_CHANNELS, type ChannelDef } from '../constants';
import type { IntegrationSettingsConfig, ChannelStatus } from '../services/configService';
import { IntegrationCard } from './IntegrationCard';
import { IntegrationModal } from './IntegrationModal';
import { OAuthCard } from './OAuthCard';
import { BlingAdvancedModal } from './BlingAdvancedModal';
import { MarketingDiagnosticsModal } from './MarketingDiagnosticsModal';
import { NuvemshopAdvancedModal } from './NuvemshopAdvancedModal';
import { useNuvemshopConfig, useNuvemshopInstall } from '../../../api/endpoints/nuvemshop';
import { useBlingStatus, useBlingInstall } from '../../../api/endpoints/bling';

function IntegrationCardWithTest({
  channel,
  config,
  status,
  onOpenModal,
}: {
  channel: ChannelDef;
  config: IntegrationSettingsConfig;
  status: ChannelStatus | null | undefined;
  onOpenModal: () => void;
}) {
  const toast = useToast();
  const testMutation = useTestChannel(channel.id);

  const handleTest = async () => {
    if (!channel.fields) return false;
    try {
      const result = await testMutation.mutateAsync({ fields: channel.fields });
      if (result.ok) {
        toast.success(`${channel.label}: credenciais validadas`);
      } else {
        toast.error(
          result.errors[0] ?? `${channel.label}: 1 ou mais credenciais falharam`,
        );
      }
      return result.ok;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erro ao testar credenciais');
      return false;
    }
  };

  return (
    <IntegrationCard
      channel={channel}
      config={config}
      status={status}
      onOpenModal={onOpenModal}
      onTest={handleTest}
      testing={testMutation.isPending}
    />
  );
}

function useChannelValidationStatus(channelId: string) {
  const { getAuthHeader } = useAuth();
  const storeKey = useStoreKey();
  const apiRequest = createApiRequest(getAuthHeader);
  return useQuery({
    queryKey: tenantKey(storeKey, 'config', 'integration-status', channelId),
    queryFn: () => IntegrationFieldService.getChannelValidationStatus(apiRequest, channelId),
    staleTime: 30_000,
  });
}

export function IntegrationGrid() {
  const { config, isLoading, error } = useIntegrationSettings();
  const { getAuthHeader } = useAuth();
  const storeKey = useStoreKey();
  const [searchParams] = useSearchParams();
  const [modalChannel, setModalChannel] = useState<string | null>(null);
  const [advancedModal, setAdvancedModal] = useState<'nuvemshop' | 'bling' | 'marketing' | null>(
    null,
  );
  const toast = useToast();

  const apiRequest = createApiRequest(getAuthHeader);

  const nuvemshopConfig = useNuvemshopConfig();
  const nuvemshopInstall = useNuvemshopInstall();
  const blingStatus = useBlingStatus();
  const blingInstall = useBlingInstall();
  const nuvemshopDisconnect = useOAuthDisconnect('nuvemshop');
  const blingDisconnect = useOAuthDisconnect('bling');

  const metaStatus = useChannelValidationStatus('meta_capi');
  const ga4Status = useChannelValidationStatus('ga4');
  const utmifyStatus = useChannelValidationStatus('utmify');
  const dadosOpStatus = useChannelValidationStatus('dados_operacionais');
  const mercadoPagoStatus = useChannelValidationStatus('mercado_pago');
  const nuvemshopStatus = useChannelValidationStatus('nuvemshop');
  const blingStatusChannel = useChannelValidationStatus('bling');

  const statusByChannel = useMemo<Record<string, ChannelStatus | null | undefined>>(
    () => ({
      meta_capi: metaStatus.data,
      ga4: ga4Status.data,
      utmify: utmifyStatus.data,
      dados_operacionais: dadosOpStatus.data,
      mercado_pago: mercadoPagoStatus.data,
      nuvemshop: nuvemshopStatus.data,
      bling: blingStatusChannel.data,
    }),
    [
      metaStatus.data,
      ga4Status.data,
      utmifyStatus.data,
      dadosOpStatus.data,
      mercadoPagoStatus.data,
      nuvemshopStatus.data,
      blingStatusChannel.data,
    ],
  );

  const { data: validationEntries } = useQuery({
    queryKey: tenantKey(storeKey, 'config', 'integration-validation'),
    queryFn: () => IntegrationFieldService.getValidationLogEntries(apiRequest),
    staleTime: 30_000,
  });

  const channelStatuses = useMemo(() => {
    const fallback: Record<string, ChannelStatus | null | undefined> = statusByChannel;
    if (!validationEntries) return fallback;
    const map: Record<string, ChannelStatus> = {};
    for (const entry of validationEntries) {
      const existing = map[entry.channel];
      if (!existing || entry.validated_at > (existing.last_test_at ?? '')) {
        map[entry.channel] = {
          channel: entry.channel,
          ok: entry.ok,
          last_test_at: entry.validated_at,
          error: entry.error,
        };
      }
    }
    return { ...fallback, ...map };
  }, [validationEntries, statusByChannel]);

  useEffect(() => {
    if (searchParams.get('nuvemshop') === 'connected') {
      toast.success('Nuvemshop conectado com sucesso');
      window.history.replaceState({}, '', '/configuracoes');
    }
    if (searchParams.get('bling') === 'connected') {
      toast.success('Bling conectado com sucesso');
      window.history.replaceState({}, '', '/configuracoes');
    }
  }, [searchParams, toast]);

  if (isLoading) return <Loading />;
  if (error) return <Alert severity="error">{(error as Error).message}</Alert>;
  if (!config) return <Alert severity="error">Configurações não encontradas</Alert>;

  const selectedChannel = INTEGRATION_CHANNELS.find(c => c.id === modalChannel);

  const handleOAuthTest = async (
    channelId: 'nuvemshop' | 'bling',
    label: string,
  ) => {
    const ok =
      channelId === 'nuvemshop'
        ? Boolean(nuvemshopConfig.data?.connected)
        : Boolean(blingStatus.data?.connected);
    if (!ok) {
      toast.error(`${label} não está conectado`);
      return false;
    }
    toast.success(`${label}: conexão OAuth ativa`);
    return true;
  };

  return (
    <Box>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        spacing={1}
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography variant="h6">Integrações da loja</Typography>
          <Typography variant="body2" color="text.secondary">
            Configuração do tenant {config.store.name} ({config.store.slug}). Os segredos são
            armazenados criptografados e nunca retornam em texto puro.
          </Typography>
        </Box>
        {/* Único caminho de teste para GA4 e Google Ads (testable: false em constants.ts). */}
        <Button
          variant="outlined"
          size="small"
          startIcon={<FlaskConical size={16} />}
          onClick={() => setAdvancedModal('marketing')}
          sx={{ flexShrink: 0 }}
        >
          Diagnóstico de marketing
        </Button>
      </Stack>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' },
          gap: 2,
        }}
      >
        {INTEGRATION_CHANNELS.filter(c => c.type === 'field').map(channel => (
          <IntegrationCardWithTest
            key={channel.id}
            channel={channel}
            config={config}
            status={channelStatuses[channel.id]}
            onOpenModal={() => setModalChannel(channel.id)}
          />
        ))}

        <OAuthCard
          provider="nuvemshop"
          label="Nuvemshop"
          connected={Boolean(nuvemshopConfig.data?.connected)}
          onConnect={() => nuvemshopInstall.mutate()}
          onDisconnect={() => nuvemshopDisconnect.mutate()}
          onTest={() => handleOAuthTest('nuvemshop', 'Nuvemshop')}
          testing={false}
          onOpenAdvanced={() => setAdvancedModal('nuvemshop')}
          subtitle={
            nuvemshopConfig.data?.connected
              ? `Loja #${nuvemshopConfig.data.store_id}${
                  nuvemshopConfig.data.default_vendedor_name
                    ? ` · ${nuvemshopConfig.data.default_vendedor_name}`
                    : ''
                }`
              : undefined
          }
        />
        <OAuthCard
          provider="bling"
          label="Bling"
          connected={Boolean(blingStatus.data?.connected)}
          onConnect={() => blingInstall.mutate()}
          onDisconnect={() => blingDisconnect.mutate()}
          onTest={() => handleOAuthTest('bling', 'Bling')}
          testing={false}
          onOpenAdvanced={() => setAdvancedModal('bling')}
        />
      </Box>

      {selectedChannel && selectedChannel.type === 'field' && (
        <IntegrationModal
          open
          channel={selectedChannel}
          config={config}
          onClose={() => setModalChannel(null)}
        />
      )}

      {/* Montados sob demanda: cada modal dispara suas próprias queries (vendedores,
          cadastros do Bling, outbox de marketing) e não devem rodar ao abrir a aba. */}
      {advancedModal === 'nuvemshop' && (
        <NuvemshopAdvancedModal open onClose={() => setAdvancedModal(null)} />
      )}
      {advancedModal === 'bling' && (
        <BlingAdvancedModal open onClose={() => setAdvancedModal(null)} />
      )}
      {advancedModal === 'marketing' && (
        <MarketingDiagnosticsModal open onClose={() => setAdvancedModal(null)} />
      )}
    </Box>
  );
}
