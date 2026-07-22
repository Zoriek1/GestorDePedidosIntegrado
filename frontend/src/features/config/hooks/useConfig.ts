import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../auth/authStore';
import { createApiRequest } from '../../../api/http';
import { tenantKey } from '../../../lib/tenantKey';
import {
  ConfigService,
  IntegrationFieldService,
  IntegrationSettingsPayload,
  IntegrationSettingsService,
  TaxaEntregaConfig,
  TaxaCartaoConfig,
  type ChannelStatus,
} from '../services/configService';

export function useTaxaEntregaConfig() {
  const { getAuthHeader, getUser } = useAuth();
  const queryClient = useQueryClient();
  const apiRequest = createApiRequest(getAuthHeader);
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');

  const query = useQuery({
    queryKey: tenantKey(storeKey, 'config', 'taxa-entrega'),
    queryFn: () => ConfigService.getTaxaEntrega(apiRequest),
  });

  const mutation = useMutation({
    mutationFn: (config: TaxaEntregaConfig) => ConfigService.updateTaxaEntrega(apiRequest, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'config', 'taxa-entrega') });
    },
  });

  return {
    config: query.data,
    isLoading: query.isLoading,
    error: query.error,
    updateConfig: mutation.mutateAsync,
    isUpdating: mutation.isPending,
  };
}

export function useTaxaCartaoConfig() {
  const { getAuthHeader, getUser } = useAuth();
  const queryClient = useQueryClient();
  const apiRequest = createApiRequest(getAuthHeader);
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');

  const query = useQuery({
    queryKey: tenantKey(storeKey, 'config', 'taxa-cartao'),
    queryFn: () => ConfigService.getTaxaCartao(apiRequest),
    staleTime: 5 * 60 * 1000,
  });

  const mutation = useMutation({
    mutationFn: (config: TaxaCartaoConfig) => ConfigService.updateTaxaCartao(apiRequest, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'config', 'taxa-cartao') });
    },
  });

  return {
    config: query.data,
    isLoading: query.isLoading,
    error: query.error,
    updateConfig: mutation.mutateAsync,
    isUpdating: mutation.isPending,
  };
}

export function useIntegrationSettings() {
  const { getAuthHeader, getUser } = useAuth();
  const queryClient = useQueryClient();
  const apiRequest = createApiRequest(getAuthHeader);

  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  const integrationsKey = tenantKey(storeKey, 'config', 'integrations');

  const query = useQuery({
    queryKey: integrationsKey,
    queryFn: () => IntegrationSettingsService.get(apiRequest),
  });
  const mutation = useMutation({
    mutationFn: (config: IntegrationSettingsPayload) =>
      IntegrationSettingsService.update(apiRequest, config),
    onSuccess: (config) => {
      queryClient.setQueryData(integrationsKey, config);
    },
  });

  return {
    config: query.data,
    isLoading: query.isLoading,
    error: query.error,
    updateConfig: mutation.mutateAsync,
    isUpdating: mutation.isPending,
  };
}

// --- E6: per-field hooks ---

export function usePatchField() {
  const { getAuthHeader, getUser } = useAuth();
  const queryClient = useQueryClient();
  const apiRequest = createApiRequest(getAuthHeader);

  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  const integrationsKey = tenantKey(storeKey, 'config', 'integrations');

  return useMutation({
    mutationFn: ({ channel, field, value }: { channel: string; field: string; value: unknown }) =>
      IntegrationFieldService.patchChannelField(apiRequest, channel, field, value),
    onSuccess: (config) => {
      queryClient.setQueryData(integrationsKey, config);
    },
  });
}

export function useValidateField() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useMutation({
    mutationFn: ({ channel, field, value }: { channel: string; field: string; value?: string }) =>
      IntegrationFieldService.validateChannelField(apiRequest, channel, field, value),
  });
}

export function useTestChannel(channelId: string) {
  const { getUser } = useAuth();
  const queryClient = useQueryClient();
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  const validate = useValidateField();

  return useMutation({
    mutationFn: async ({ fields }: { fields: Array<{ key: string; type: string }> }) => {
      const targets = fields.filter(f => f.type !== 'boolean');
      const results = await Promise.allSettled(
        targets.map(field =>
          validate.mutateAsync({
            channel: channelId,
            field: field.key,
            value: undefined,
          }),
        ),
      );

      let allOk = true;
      const errors: string[] = [];
      for (const r of results) {
        if (r.status === 'fulfilled') {
          const value = r.value as { ok?: boolean; error?: string };
          if (!value?.ok) {
            allOk = false;
            if (value?.error) errors.push(value.error);
          }
        } else {
          allOk = false;
          if (r.reason instanceof Error) errors.push(r.reason.message);
        }
      }
      return { ok: allOk, errors };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: tenantKey(storeKey, 'config', 'integration-validation'),
      });
      queryClient.invalidateQueries({
        queryKey: tenantKey(storeKey, 'config', 'integration-status', channelId),
      });
    },
  });
}

export function useValidationStatus(channel: string) {
  const { getAuthHeader, getUser } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');

  return useQuery<ChannelStatus>({
    queryKey: tenantKey(storeKey, 'config', 'integration-status', channel),
    queryFn: () => IntegrationFieldService.getChannelValidationStatus(apiRequest, channel),
    staleTime: 30_000,
  });
}

export function useOAuthDisconnect(provider: 'bling' | 'nuvemshop') {
  const { getAuthHeader, getUser } = useAuth();
  const queryClient = useQueryClient();
  const apiRequest = createApiRequest(getAuthHeader);
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');

  return useMutation({
    mutationFn: () => IntegrationFieldService.disconnectOAuth(apiRequest, provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'config', 'integrations') });
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, provider) });
    },
  });
}
