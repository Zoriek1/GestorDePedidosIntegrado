/**
 * Fontes de Pedido API endpoints
 * React Query hooks para gerenciar fontes de pedido
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';
import { useToast } from '../../components/system/useToast';

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

export interface CreateFontePayload {
  nome: string;
  ativo?: boolean;
}

export interface UpdateFontePayload {
  nome?: string;
  ativo?: boolean;
}

/**
 * Create fonte de pedido
 */
export function useCreateFonte() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();
  const { success, error: showError } = useToast();

  return useMutation({
    mutationFn: async (payload: CreateFontePayload) => {
      const response = await apiRequest<{ success: boolean; fonte: FontePedido }>('/fontes-pedido', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fontes-pedido'] });
      success('Fonte criada com sucesso');
    },
    onError: (err: Error) => {
      showError(err.message || 'Erro ao criar fonte');
    },
  });
}

/**
 * Update fonte de pedido
 */
export function useUpdateFonte() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();
  const { success, error: showError } = useToast();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateFontePayload }) => {
      const response = await apiRequest<{ success: boolean; fonte: FontePedido }>(`/fontes-pedido/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fontes-pedido'] });
      success('Fonte atualizada com sucesso');
    },
    onError: (err: Error) => {
      showError(err.message || 'Erro ao atualizar fonte');
    },
  });
}

/**
 * Delete fonte de pedido
 */
export function useDeleteFonte() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();
  const { success, error: showError } = useToast();

  return useMutation({
    mutationFn: async (id: number) => {
      const response = await apiRequest<{ success: boolean }>(`/fontes-pedido/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fontes-pedido'] });
      success('Fonte deletada com sucesso');
    },
    onError: (err: Error) => {
      showError(err.message || 'Erro ao deletar fonte');
    },
  });
}
