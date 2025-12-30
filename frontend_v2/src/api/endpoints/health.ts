/**
 * Health check API endpoint
 */

import { useQuery } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

export interface HealthResponse {
  success: boolean;
  status: 'healthy' | 'unhealthy';
  message?: string;
  error?: string;
}

/**
 * Health check
 */
export function useHealth() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await apiRequest<HealthResponse>('/health');
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    staleTime: 60000, // 1 minute
    retry: 1,
  });
}

