/**
 * Customers API endpoints
 * React Query hooks for customer search
 */

import { useQuery } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

// Types
export interface Customer {
  id: number;
  nome: string;
  telefone: string;
  email?: string;
  observacoes?: string;
  created_at?: string;
  updated_at?: string;
  // Optional stats (if include_stats=true)
  total_pedidos?: number;
  ltv?: number;
  ultimo_pedido?: string;
}

export interface CustomerSearchResponse {
  success: boolean;
  clientes: Customer[];
  total?: number;
}

/**
 * Search customers (autocomplete/search endpoint)
 * Uses GET /api/clientes/search?q=query&limit=10
 * 
 * Note: Debounce will be implemented in the component using this hook
 */
export function useCustomerSearch(query: string, limit = 10) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<CustomerSearchResponse>({
    queryKey: ['customers.search', { q: query, limit }],
    queryFn: async () => {
      if (!query || query.trim().length === 0) {
        // Return empty result if no query
        return { success: true, clientes: [], total: 0 };
      }

      const params = new URLSearchParams();
      params.append('q', query.trim());
      if (limit) params.append('limit', limit.toString());

      const endpoint = `/clientes/search?${params.toString()}`;
      const response = await apiRequest<CustomerSearchResponse>(endpoint);

      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    enabled: !!query && query.trim().length >= 2, // Only fetch if query has at least 2 characters
    staleTime: 5000, // 5 seconds
    placeholderData: (previousData) => previousData // Keep previous results while typing
  });
}

/**
 * Get customer by ID
 * Uses GET /api/clientes/:id
 */
export function useCustomer(id: number | null) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<{ success: boolean; cliente: Customer }>({
    queryKey: ['customer', id],
    queryFn: async () => {
      if (!id) {
        throw new Error('Customer ID is required');
      }

      const response = await apiRequest<{ success: boolean; cliente: Customer }>(`/clientes/${id}`);
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    enabled: !!id,
  });
}

