import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

export interface PendingScheduleItem {
  pedido_id: number;
  cliente: string;
  destinatario: string;
  dia_entrega: string | null;
  horario: string;
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
    },
  });
}
