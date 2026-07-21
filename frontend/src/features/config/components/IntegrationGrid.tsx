import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Box, Typography } from '@mui/material';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Loading } from '../../../components/common/Loading';
import { useToast } from '../../../components/system/useToast';
import { useIntegrationSettings, useOAuthDisconnect } from '../hooks/useConfig';
import { IntegrationFieldService } from '../services/configService';
import { createApiRequest } from '../../../api/http';
import { useAuth } from '../../auth/authStore';
import { useStoreKey, tenantKey } from '../../../lib/tenantKey';
import { INTEGRATION_CHANNELS } from '../constants';
import { IntegrationCard } from './IntegrationCard';
import { IntegrationModal } from './IntegrationModal';
import { OAuthCard } from './OAuthCard';
import { useNuvemshopConfig, useNuvemshopInstall } from '../../../api/endpoints/nuvemshop';
import { useBlingStatus, useBlingInstall } from '../../../api/endpoints/bling';

export function IntegrationGrid() {
  const { config, isLoading, error } = useIntegrationSettings();
  const { getAuthHeader } = useAuth();
  const storeKey = useStoreKey();
  const [searchParams] = useSearchParams();
  const [modalChannel, setModalChannel] = useState<string | null>(null);
  const toast = useToast();

  const apiRequest = createApiRequest(getAuthHeader);

  const nuvemshopConfig = useNuvemshopConfig();
  const nuvemshopInstall = useNuvemshopInstall();
  const blingStatus = useBlingStatus();
  const blingInstall = useBlingInstall();
  const nuvemshopDisconnect = useOAuthDisconnect('nuvemshop');
  const blingDisconnect = useOAuthDisconnect('bling');

  const { data: validationEntries } = useQuery({
    queryKey: tenantKey(storeKey, 'config', 'integration-validation'),
    queryFn: () => IntegrationFieldService.getValidationLogEntries(apiRequest),
    staleTime: 30_000,
  });

  const channelStatuses = useMemo(() => {
    if (!validationEntries) return {} as Record<string, { channel: string; ok: boolean | null; last_test_at: string | null; error: string | null }>;
    const map: Record<string, { channel: string; ok: boolean | null; last_test_at: string | null; error: string | null }> = {};
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
    return map;
  }, [validationEntries]);

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

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6">Integrações da loja</Typography>
        <Typography variant="body2" color="text.secondary">
          Configuração do tenant {config.store.name} ({config.store.slug}). Os segredos são
          armazenados criptografados e nunca retornam em texto puro.
        </Typography>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' },
          gap: 2,
        }}
      >
        {INTEGRATION_CHANNELS.filter(c => c.type === 'field').map(channel => (
          <IntegrationCard
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
        />
        <OAuthCard
          provider="bling"
          label="Bling"
          connected={Boolean(blingStatus.data?.connected)}
          onConnect={() => blingInstall.mutate()}
          onDisconnect={() => blingDisconnect.mutate()}
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
    </Box>
  );
}