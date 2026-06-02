/**
 * Stats API endpoint
 */

import { useQuery } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';
import { queryFnWithCache } from '../../lib/offline/queryWithCache';

export interface Stats {
  total: number;
  agendados: number;
  producao: number;
  prontos: number;
  emRota: number;
  cancelados: number;
  atrasados: number;
}

type BackendStats = {
  total: number;
  agendado: number;
  em_producao: number;
  pronto_entrega: number;
  pronto_retirada: number;
  em_rota: number;
  concluido: number;
};

export interface StatsResponse {
  success: boolean;
  stats: Stats;
}

/**
 * Get statistics
 */
export function useStats() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryKey: readonly unknown[] = ['stats'];

  return useQuery<StatsResponse>({
    queryKey,
    queryFn: () => queryFnWithCache(queryKey, async () => {
      const response = await apiRequest<{ success: boolean; stats: BackendStats }>('/stats');
      if (!response.ok) {
        throw new Error(response.message);
      }
      const s = response.data.stats;
      const mapped: Stats = {
        total: s.total,
        agendados: s.agendado,
        producao: s.em_producao,
        prontos: (s.pronto_entrega || 0) + (s.pronto_retirada || 0),
        emRota: s.em_rota,
        cancelados: 0, // backend não expõe
        atrasados: 0, // opcional, preenchido via outro endpoint se necessário
      };
      const mappedResponse: StatsResponse = { success: true, stats: mapped };
      return mappedResponse;
    }, { tag: 'stats' }),
    placeholderData: (previousData) => previousData,
    staleTime: 30000, // 30 seconds
    refetchInterval: 20000, // 20 seconds
    refetchOnWindowFocus: true,
  });
}

