import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../auth/authStore';
import { createApiRequest } from '../../../api/http';
import { ConfigService, TaxaEntregaConfig, TaxaCartaoConfig } from '../services/configService';

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
