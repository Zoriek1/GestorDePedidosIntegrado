import { useMutation, useQuery } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

export interface StepByStepUrl {
  step: number;
  label: string;
  url: string;
}

export interface RotaOtimizada {
  rota_id: number;
  nome: string;
  distancia_total_km: number;
  duracao_total_min: number;
  sequencia_pedidos: number[];
  num_pedidos: number;
  metodo_otimizacao?: string;
  origem?: { lat: number; lon: number };
  waypoints?: [number, number][];
  google_maps_url?: string | null;
  google_maps_step_by_step?: StepByStepUrl[];
}

export function useCalcularRotaOtimizada() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useMutation({
    mutationFn: async ({ pedidoIds }: { pedidoIds: number[] }) => {
      const response = await apiRequest<RotaOtimizada>('/pedidos/rota-otimizada', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pedido_ids: pedidoIds }),
      });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
  });
}

export function useRotaOtimizada(rotaId?: number) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<RotaOtimizada>({
    queryKey: ['rota-otimizada', rotaId],
    enabled: !!rotaId,
    queryFn: async () => {
      const response = await apiRequest<RotaOtimizada>(`/pedidos/rota-otimizada/${rotaId}`);
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
  });
}

