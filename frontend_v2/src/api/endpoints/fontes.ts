/**
 * Fontes de Pedido API endpoints
 * React Query hooks para gerenciar fontes de pedido
 */

import { useQuery } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

// Types
export interface FontePedido {
  id: number;
  nome: string;
  ativo: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface FontesResponse {
  success: boolean;
  count: number;
  fontes: FontePedido[];
}

/**
 * Get active fontes de pedido
 * Uses GET /api/fontes-pedido?ativas=true
 */
export function useFontesPedido(apenasAtivas: boolean = true) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<FontesResponse>({
    queryKey: ['fontes-pedido', { apenasAtivas }],
    queryFn: async () => {
      const endpoint = `/fontes-pedido?ativas=${apenasAtivas}`;
      const response = await apiRequest<FontesResponse>(endpoint);
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

