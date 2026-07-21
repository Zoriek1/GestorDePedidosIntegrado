import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../auth/authStore';
import { createApiRequest } from '../../../api/http';
import {
  ConfigService,
  IntegrationFieldService,
  IntegrationSettingsPayload,
  IntegrationSettingsService,
  TaxaEntregaConfig,
  TaxaCartaoConfig,
  type ValidationResult,
  type ChannelStatus,
} from '../services/configService';

export function useTaxaEntregaConfig() {
  const { getAuthHeader } = useAuth();
  const queryClient = useQueryClient();
  const apiRequest = createApiRequest(getAuthHeader);

  const query = useQuery({
    queryKey: ['config', 'taxa-entrega'],
    queryFn: () => ConfigService.getTaxaEntrega(apiRequest),
  });

  const mutation = useMutation({
    mutationFn: (config: TaxaEntregaConfig) => ConfigService.updateTaxaEntrega(apiRequest, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'taxa-entrega'] });
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
  const { getAuthHeader } = useAuth();
  const queryClient = useQueryClient();
  const apiRequest = createApiRequest(getAuthHeader);

  const query = useQuery({
    queryKey: ['config', 'taxa-cartao'],
    queryFn: () => ConfigService.getTaxaCartao(apiRequest),
    staleTime: 5 * 60 * 1000,
  });

  const mutation = useMutation({
    mutationFn: (config: TaxaCartaoConfig) => ConfigService.updateTaxaCartao(apiRequest, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'taxa-cartao'] });
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

  // Escopo por loja: a query key inclui a identidade da loja autenticada para não
  // reaproveitar o cache de integrações entre lojas/sessões.
  const user = getUser();
  const storeKey = user?.store_slug ?? user?.store_ref_id ?? null;
  const integrationsKey = ['config', 'integrations', storeKey] as const;

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
  const storeKey = user?.store_slug ?? user?.store_ref_id ?? null;
  const integrationsKey = ['config', 'integrations', storeKey] as const;

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

export function useValidationStatus(channel: string) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<ChannelStatus>({
    queryKey: ['config', 'integration-status', channel],
    queryFn: () => IntegrationFieldService.getChannelValidationStatus(apiRequest, channel),
    staleTime: 30_000,
  });
}

export function useOAuthDisconnect(provider: 'bling' | 'nuvemshop') {
  const { getAuthHeader } = useAuth();
  const queryClient = useQueryClient();
  const apiRequest = createApiRequest(getAuthHeader);

  return useMutation({
    mutationFn: () => IntegrationFieldService.disconnectOAuth(apiRequest, provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'integrations'] });
      queryClient.invalidateQueries({ queryKey: [provider] });
    },
  });
}
