/**
 * Entregas API — endpoints específicos do entregador.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../../../api/http';
import { useAuth } from '../../auth/authStore';
import { tenantKey } from '../../../lib/tenantKey';
import type { Pedido } from '../../../api/endpoints/pedidos';

interface PedidosList {
  success: boolean;
  pedidos: Pedido[];
  total: number;
  entregador_id?: number;
}

export function useEntregasDisponiveis(options?: { enabled?: boolean }) {
  const { getAuthHeader, getUser } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  return useQuery<PedidosList>({
    queryKey: tenantKey(storeKey, 'entregas-disponiveis'),
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
  const { getAuthHeader, getUser } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  const params = new URLSearchParams();
  if (options?.incluirConcluidos) params.append('incluir_concluidos', 'true');
  if (options?.entregadorId) params.append('entregador_id', String(options.entregadorId));
  const qs = params.toString();
  return useQuery<PedidosList>({
    queryKey: tenantKey(storeKey, 'minhas-entregas', options?.incluirConcluidos, options?.entregadorId),
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
  const { getAuthHeader, getUser } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const qc = useQueryClient();
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
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
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'entregas-disponiveis') });
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'minhas-entregas') });
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedidos') });
    },
  });
}

interface EntregadorOption {
  id: number;
  name: string;
  email: string;
}

/** Lista leve de entregadores ativos (admin/vendedor/atendente). */
export function useEntregadores() {
  const { getAuthHeader, getUser } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  return useQuery<EntregadorOption[]>({
    queryKey: tenantKey(storeKey, 'entregadores'),
    queryFn: async () => {
      const r = await apiRequest<{ users: EntregadorOption[] }>('/users/entregadores');
      if (!r.ok) throw new Error(r.message);
      return (r.data as { users: EntregadorOption[] }).users ?? [];
    },
    staleTime: 60_000,
  });
}

/** Atribui (ou desatribui se entregadorId=null) um entregador a um pedido. */
export function useAtribuirEntregadorPedido() {
  const { getAuthHeader, getUser } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const qc = useQueryClient();
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  return useMutation({
    mutationFn: async (params: { pedidoId: number; entregadorId: number | null }) => {
      const r = await apiRequest<{ success: boolean; data?: { pedido: Pedido } }>(
        `/pedidos/${params.pedidoId}/atribuir-entregador`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entregador_id: params.entregadorId }),
        }
      );
      if (!r.ok) throw new Error(r.message);
      return r.data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedido', vars.pedidoId) });
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedidos') });
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'minhas-entregas') });
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'entregas-disponiveis') });
    },
  });
}

export function useFinalizarEntrega() {
  const { getAuthHeader, getUser } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const qc = useQueryClient();
  const user = getUser();
  const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
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
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'minhas-entregas') });
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedidos') });
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedido', id) });
      qc.invalidateQueries({ queryKey: tenantKey(storeKey, 'ledger') });
    },
  });
}
