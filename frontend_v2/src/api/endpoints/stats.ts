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
  entregues: number;
  cancelados: number;
  atrasados: number;
}

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
      const response = await apiRequest<StatsResponse>('/stats');
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    }, { tag: 'stats' }),
    placeholderData: (previousData) => previousData,
    staleTime: 30000, // 30 seconds
    refetchInterval: 8000, // 8 seconds
    refetchOnWindowFocus: true,
  });
}

