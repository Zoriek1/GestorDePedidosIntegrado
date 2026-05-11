/**
 * Entregas API — endpoints específicos do entregador.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../../../api/http';
import { useAuth } from '../../auth/authStore';
import type { Pedido } from '../../../api/endpoints/pedidos';

interface PedidosList {
  success: boolean;
  pedidos: Pedido[];
  total: number;
  entregador_id?: number;
}

export function useEntregasDisponiveis(options?: { enabled?: boolean }) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  return useQuery<PedidosList>({
    queryKey: ['entregas-disponiveis'],
    queryFn: async () => {
      const r = await apiRequest<PedidosList>('/pedidos/disponiveis-entrega');
      if (!r.ok) throw new Error(r.message);
      return r.data!;
    },
    staleTime: 30_000,
    enabled: options?.enabled ?? true,
  });
}

export function useMinhasEntregas(options?: { incluirConcluidos?: boolean; entregadorId?: number }) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const params = new URLSearchParams();
  if (options?.incluirConcluidos) params.append('incluir_concluidos', 'true');
  if (options?.entregadorId) params.append('entregador_id', String(options.entregadorId));
  const qs = params.toString();
  return useQuery<PedidosList>({
    queryKey: ['minhas-entregas', options?.incluirConcluidos, options?.entregadorId],
    queryFn: async () => {
      const r = await apiRequest<PedidosList>(`/pedidos/minhas-entregas${qs ? `?${qs}` : ''}`);
      if (!r.ok) throw new Error(r.message);
      return r.data!;
    },
    staleTime: 15_000,
  });
}

interface AtribuirLoteResponse {
  success: boolean;
  atribuidos: number[];
  ignorados: { pedido_id: number; motivo: string }[];
  entregador_id: number;
}

export function useAtribuirEntregasLote() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (pedidoIds: number[]) => {
      const r = await apiRequest<AtribuirLoteResponse>('/pedidos/atribuir-entregadores-lote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pedido_ids: pedidoIds }),
      });
      if (!r.ok) throw new Error(r.message);
      return r.data!;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entregas-disponiveis'] });
      qc.invalidateQueries({ queryKey: ['minhas-entregas'] });
      qc.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });
}

export function useFinalizarEntrega() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (pedidoId: number) => {
      const r = await apiRequest<{ success: boolean; data?: { pedido: Pedido } }>(
        `/pedidos/${pedidoId}/finalizar-entrega`,
        { method: 'POST' }
      );
      if (!r.ok) throw new Error(r.message);
      return r.data;
    },
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['minhas-entregas'] });
      qc.invalidateQueries({ queryKey: ['pedidos'] });
      qc.invalidateQueries({ queryKey: ['pedido', id] });
      qc.invalidateQueries({ queryKey: ['ledger'] });
    },
  });
}
