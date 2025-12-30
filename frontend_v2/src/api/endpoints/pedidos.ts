/**
 * Orders API endpoints
 * All API calls via React Query hooks (no manual useEffect)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

// Types
export interface Pedido {
  id: number;
  cliente: string;
  telefone_cliente: string;
  destinatario: string;
  tipo_pedido: 'Entrega' | 'Retirada';
  produto: string;
  flores_cor?: string;
  valor?: string;
  dia_entrega: string; // YYYY-MM-DD
  horario: string;
  cep?: string;
  rua?: string;
  numero?: string;
  bairro?: string;
  cidade?: string;
  endereco?: string;
  obs_entrega?: string;
  mensagem?: string;
  pagamento?: string;
  observacoes?: string;
  fonte_pedido?: string;
  fonte_pedido_id?: number;
  fonte_pedido_nome?: string;
  status_pagamento?: string;
  status: string;
  quantidade: number;
  oculto: boolean;
  impresso: boolean;
  cliente_id?: number;
  distancia_km?: number;
  taxa_entrega?: number;
  coords_lat?: number;
  coords_lon?: number;
  created_at?: string;
  updated_at?: string;
}

export interface PedidosResponse {
  success: boolean;
  pedidos: Pedido[];
  total: number;
}

export interface PedidosFilters {
  status?: string;
  data_inicio?: string; // YYYY-MM-DD
  data_fim?: string; // YYYY-MM-DD
  search?: string;
}

/**
 * Get orders with filters
 */
export function usePedidos(filters: PedidosFilters = {}) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<PedidosResponse>({
    queryKey: ['pedidos', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.data_inicio) params.append('data_inicio', filters.data_inicio);
      if (filters.data_fim) params.append('data_fim', filters.data_fim);
      if (filters.search) params.append('search', filters.search);

      const queryString = params.toString();
      const endpoint = `/pedidos${queryString ? `?${queryString}` : ''}`;

      const response = await apiRequest<PedidosResponse>(endpoint);
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    staleTime: 5000, // 5 seconds
    refetchInterval: 15000, // 15 seconds
    refetchOnWindowFocus: true,
    keepPreviousData: true, // Maintains previous data when filters change
  });
}

/**
 * Get single order by ID
 */
export function usePedido(id: number) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<{ success: boolean; pedido: Pedido }>({
    queryKey: ['pedido', id],
    queryFn: async () => {
      const response = await apiRequest<{ success: boolean; pedido: Pedido }>(`/pedidos/${id}`);
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    enabled: !!id,
  });
}

