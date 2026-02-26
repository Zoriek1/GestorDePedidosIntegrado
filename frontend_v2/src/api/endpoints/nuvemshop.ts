import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

export interface PendingScheduleItem {
  pedido_id: number;
  cliente: string;
  destinatario: string;
  dia_entrega: string | null;
  horario: string;
  valor?: string | null;
  produto?: string | null;
  endereco?: string | null;
  status_pagamento?: string | null;
  observacoes?: string;
}

export interface PendingSchedulesResponse {
  total: number;
  pedidos: PendingScheduleItem[];
}

export function usePendingSchedules() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<PendingSchedulesResponse>({
    queryKey: ['nuvemshop', 'pendencias-agendamento'],
    queryFn: async () => {
      const response = await apiRequest<PendingSchedulesResponse>(
        '/integrations/nuvemshop/pedidos-pendentes-agendamento'
      );
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
  });
}

export function useDefineSchedule() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { pedido_id: number; dia_entrega: string; horario?: string }) => {
      const response = await apiRequest(`/integrations/nuvemshop/pedidos/${payload.pedido_id}/definir-agendamento`, {
        method: 'POST',
        body: JSON.stringify({
          dia_entrega: payload.dia_entrega,
          horario: payload.horario || undefined,
        }),
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nuvemshop', 'pendencias-agendamento'] });
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });
}

export function useProcessPendingNuvemshop() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiRequest('/integrations/nuvemshop/process-pending', {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nuvemshop', 'pendencias-agendamento'] });
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });
}

/** Retorna a URL de autorização OAuth para conectar/reconectar a loja na Nuvemshop. */
export function useNuvemshopInstall() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useMutation({
    mutationFn: async () => {
      const response = await apiRequest<{ authorize_url: string }>('/integrations/nuvemshop/install');
      if (!response.ok) {
        throw new Error(response.message);
      }
      const url = (response.data as { authorize_url?: string })?.authorize_url;
      if (!url) throw new Error('URL de autorização não retornada');
      return url;
    },
  });
}

/** Recria os webhooks de pedidos na loja conectada (útil após mudar de domínio/VPS). */
export function useSetupNuvemshopWebhooks() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useMutation({
    mutationFn: async () => {
      const response = await apiRequest('/integrations/nuvemshop/setup-webhooks', {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
  });
}
