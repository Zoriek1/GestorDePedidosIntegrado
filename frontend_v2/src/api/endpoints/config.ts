import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

export interface MetaFaturamentoResponse {
  success: boolean;
  mes: string;
  valor: number | null;
}

export function useMetaFaturamento(mes: string) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryKey: readonly unknown[] = ['config', 'meta-faturamento', mes];

  return useQuery<MetaFaturamentoResponse>({
    queryKey,
    queryFn: async () => {
      const response = await apiRequest<MetaFaturamentoResponse>(`/config/meta-faturamento?mes=${mes}`);
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
  });
}

export function useUpdateMetaFaturamento() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ mes, valor }: { mes: string; valor: number }) => {
      const response = await apiRequest<MetaFaturamentoResponse>('/config/meta-faturamento', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mes, valor }),
      });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['config', 'meta-faturamento', data.mes] });
    },
  });
}
