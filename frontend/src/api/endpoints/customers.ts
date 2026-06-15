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
  ticket_medio?: number;
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

export interface CustomersListResponse {
  success: boolean;
  total: number;
  page: number;
  per_page: number;
  clientes: Customer[];
}

export interface CustomersFilters {
  search?: string;
  page?: number;
  perPage?: number;
  includeStats?: boolean;
  minPedidos?: number;
  maxPedidos?: number;
  minLTV?: number;
  maxLTV?: number;
  ultimoPedidoApos?: string;
  ultimoPedidoAntes?: string;
}

export function useCustomers(params: CustomersFilters = {}) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const { search = '', page = 1, perPage = 50, includeStats = true, minPedidos, maxPedidos, minLTV, maxLTV, ultimoPedidoApos, ultimoPedidoAntes } = params;

  return useQuery<CustomersListResponse>({
    queryKey: ['customers.list', { search, page, perPage, includeStats, minPedidos, maxPedidos, minLTV, maxLTV, ultimoPedidoApos, ultimoPedidoAntes }],
    queryFn: async () => {
      const query = new URLSearchParams();
      if (search) query.append('search', search);
      query.append('page', page.toString());
      query.append('per_page', perPage.toString());
      query.append('stats', includeStats ? 'true' : 'false');
      if (minPedidos !== undefined) query.append('min_pedidos', minPedidos.toString());
      if (maxPedidos !== undefined) query.append('max_pedidos', maxPedidos.toString());
      if (minLTV !== undefined) query.append('min_ltv', minLTV.toString());
      if (maxLTV !== undefined) query.append('max_ltv', maxLTV.toString());
      if (ultimoPedidoApos) query.append('ultimo_pedido_apos', ultimoPedidoApos);
      if (ultimoPedidoAntes) query.append('ultimo_pedido_antes', ultimoPedidoAntes);

      const response = await apiRequest<CustomersListResponse>(`/clientes?${query.toString()}`);
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    staleTime: 10000,
    placeholderData: (prev) => prev,
  });
}

export interface CustomerOrdersResponse {
  success: boolean;
  total_pedidos: number;
  pedidos: Array<{
    id: number;
    created_at?: string;
    dia_entrega?: string;
    horario?: string;
    status?: string;
    valor?: string;
  }>;
}

export interface ClienteEndereco {
  id: number;
  cliente_id: number;
  apelido: string;
  principal: boolean;
  cep: string;
  rua: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  estado: string;
  endereco_completo: string;
}

export interface ClienteEnderecosResponse {
  success: boolean;
  total: number;
  enderecos: ClienteEndereco[];
}

/**
 * Endereços salvos de um cliente.
 * GET /api/clientes/:id/enderecos — usado no wizard para reusar endereços (#17).
 */
export function useClienteEnderecos(id?: number | null) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<ClienteEnderecosResponse>({
    queryKey: ['cliente.enderecos', id],
    enabled: !!id,
    queryFn: async () => {
      const response = await apiRequest<ClienteEnderecosResponse>(`/clientes/${id}/enderecos`);
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    staleTime: 30000,
  });
}

export function useCustomerOrders(id?: number, limit = 50) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<CustomerOrdersResponse>({
    queryKey: ['customer.orders', id, limit],
    enabled: !!id,
    queryFn: async () => {
      const response = await apiRequest<CustomerOrdersResponse>(`/clientes/${id}/pedidos?limit=${limit}`);
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    staleTime: 10000,
  });
}

