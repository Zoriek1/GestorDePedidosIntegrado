/**
 * Orders API endpoints
 * All API calls via React Query hooks (no manual useEffect)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';
import { queryFnWithCache } from '../../lib/offline/queryWithCache';
import { enqueue } from '../../lib/offline/outbox';
import { useOffline } from '../../lib/offline/useOffline';
import { useToast } from '../../components/system/useToast';

// Types
export interface Pedido {
  id: number;
  cliente: string;
  telefone_cliente: string;
  cpf_cnpj?: string;
  destinatario: string;
  tipo_pedido: 'Entrega' | 'Retirada';
  produto: string;
  flores_cor?: string;
  valor?: string;
  dia_entrega: string; // YYYY-MM-DD
  horario: string;
  slot_inicio?: string | null; // "HH:MM"
  slot_deadline?: string | null; // "HH:MM"
  is_expressa?: boolean;
  cep?: string;
  rua?: string;
  numero?: string;
  tipo_local?: 'casa' | 'predio' | 'comercial';
  nome_local?: string;
  apto?: string;
  bloco?: string;
  torre?: string;
  andar?: string;
  quadra?: string;
  lote?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  uf?: string;
  endereco?: string;
  obs_entrega?: string;
  mensagem?: string;
  pagamento?: string;
  parcelas_cartao?: number | null;
  taxa_cartao_valor?: number | null;
  observacoes?: string;
  fonte_pedido?: string;
  fonte_pedido_id?: number;
  fonte_pedido_nome?: string;
  status_pagamento?: string;
  regra_pagamento?: string;
  percentual_entrada?: number | null;
  valor_entrada?: number | null;
  valor_restante?: number | null;
  forma_pagamento_entrada?: string;
  forma_pagamento_restante?: string;
  entrada_recebida_at?: string | null;
  saldo_recebido_at?: string | null;
  status: string;
  quantidade: number;
  oculto: boolean;
  impresso: boolean;
  cartao_impresso?: boolean;
  cliente_id?: number;
  vendedor_id?: number;
  entregador_id?: number | null;
  delivery_assigned_at?: string | null;
  delivery_completed_at?: string | null;
  distancia_km?: number;
  taxa_entrega?: number;
  coords_lat?: number;
  coords_lon?: number;
  fbc?: string;
  fbp?: string;
  codigo_whatsapp?: string;
  created_at?: string;
  updated_at?: string;
  deleted_at?: string | null;
}

export interface PedidosResponse {
  success: boolean;
  pedidos: Pedido[];
  total: number;
  page?: number;
  per_page?: number;
  total_pages?: number;
}

export interface OverduePedidosResponse {
  success: boolean;
  count: number;
}

export interface PedidosFilters {
  status?: string;
  data_inicio?: string; // YYYY-MM-DD
  data_fim?: string; // YYYY-MM-DD
  search?: string;
  filtrar_por_criacao?: boolean; // Novo parâmetro: filtrar por created_at ao invés de dia_entrega
  sort_by?: string; // Campo para ordenação: 'dia_entrega', 'valor', 'cliente', 'created_at'
  sort_order?: 'asc' | 'desc'; // Direção da ordenação
  page?: number; // Número da página (1-indexed)
  per_page?: number; // Itens por página
}

/**
 * Get orders with filters
 */
export function usePedidos(filters: PedidosFilters = {}, options?: { enabled?: boolean }) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryKey: readonly unknown[] = ['pedidos', filters];

  return useQuery<PedidosResponse>({
    queryKey,
    queryFn: () => queryFnWithCache(queryKey, async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.data_inicio) params.append('data_inicio', filters.data_inicio);
      if (filters.data_fim) params.append('data_fim', filters.data_fim);
      if (filters.search) params.append('search', filters.search);
      if (filters.filtrar_por_criacao) params.append('filtrar_por_criacao', 'true');
      if (filters.sort_by) params.append('sort_by', filters.sort_by);
      if (filters.sort_order) params.append('sort_order', filters.sort_order);
      if (filters.page) params.append('page', filters.page.toString());
      if (filters.per_page) params.append('per_page', filters.per_page.toString());

      const queryString = params.toString();
      const endpoint = `/pedidos${queryString ? `?${queryString}` : ''}`;

      const response = await apiRequest<PedidosResponse>(endpoint);
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    }, { tag: 'pedidos' }),
    placeholderData: (previousData) => previousData, // Maintains previous data when filters change
    enabled: options?.enabled ?? true,
    staleTime: 5000, // 5 seconds
    refetchInterval: 20000, // 20 seconds
    refetchOnWindowFocus: true
  });
}

export function useOverdueCount() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryKey: readonly unknown[] = ['pedidos', 'overdue'];

  return useQuery<OverduePedidosResponse>({
    queryKey,
    queryFn: async () => {
      const response = await apiRequest<OverduePedidosResponse>('/pedidos/overdue');
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data;
    },
    staleTime: 30000,
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

export interface CreatePedidoPayload {
  cliente: string;
  telefone_cliente: string;
  cpf_cnpj?: string;
  destinatario: string;
  tipo_pedido: 'Entrega' | 'Retirada';
  produto: string;
  flores_cor?: string;
  valor?: string;
  dia_entrega: string;
  horario: string;
  cep?: string;
  rua?: string;
  numero?: string;
  tipo_local?: 'casa' | 'predio' | 'comercial';
  nome_local?: string;
  apto?: string;
  bloco?: string;
  torre?: string;
  andar?: string;
  quadra?: string;
  lote?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  uf?: string;
  endereco?: string;
  obs_entrega?: string;
  mensagem?: string;
  pagamento?: string;
  parcelas_cartao?: number | null;
  observacoes?: string;
  status_pagamento?: string;
  regra_pagamento?: string;
  percentual_entrada?: number | null;
  valor_entrada?: number | null;
  valor_restante?: number | null;
  forma_pagamento_entrada?: string;
  forma_pagamento_restante?: string;
  fonte_pedido?: string;
  fonte_pedido_id?: number;
  codigo_whatsapp?: string;
  quantidade?: number;
  cliente_id?: number;
}

export function useCreatePedido() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const { isOnline } = useOffline();
  const { info } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreatePedidoPayload) => {
      if (isOnline) {
        const response = await apiRequest<{ pedido_id: number; pedido: Pedido; track_url?: string }>('/pedidos', {
          method: 'POST',
          body: JSON.stringify({ ...data, clientTimestamp: Date.now() }),
          headers: { 'Content-Type': 'application/json' }
        });
        if (!response.ok) throw new Error(response.message);
        return response.data;
      } else {
        await enqueue('create_order', data);
        info('Salvo offline; será sincronizado quando online');
        throw new Error('OFFLINE_ENQUEUED');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    }
  });
}

// Sugestões de correção de endereço feitas pelo cliente na página pública de rastreio.
export interface SugestaoEndereco {
  id: number;
  pedido_id: number;
  texto: string;
  status: 'pendente' | 'aplicada' | 'ignorada';
  endereco_anterior?: string | null;
  created_at?: string | null;
  resolved_at?: string | null;
  resolved_by?: string | null;
}

/** Lista as sugestões de endereço de um pedido (para revisão no painel). */
export function useSugestoesEndereco(pedidoId: number) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<{ success: boolean; sugestoes: SugestaoEndereco[] }>({
    queryKey: ['sugestoes-endereco', pedidoId],
    queryFn: async () => {
      const response = await apiRequest<{ success: boolean; sugestoes: SugestaoEndereco[] }>(
        `/pedidos/${pedidoId}/sugestoes-endereco`,
      );
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    enabled: !!pedidoId,
  });
}

/** Aplica ou ignora uma sugestão de endereço. */
export function useResolverSugestaoEndereco() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sugestaoId,
      acao,
    }: {
      sugestaoId: number;
      pedidoId: number;
      acao: 'aplicar' | 'ignorar';
    }) => {
      const response = await apiRequest<{ success: boolean; sugestao: SugestaoEndereco }>(
        `/pedidos/sugestoes-endereco/${sugestaoId}/resolver`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ acao }),
        },
      );
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (_data, { pedidoId }) => {
      queryClient.invalidateQueries({ queryKey: ['sugestoes-endereco', pedidoId] });
      queryClient.invalidateQueries({ queryKey: ['pedido', pedidoId] });
    },
  });
}

/** Busca o link público de acompanhamento de um pedido já existente (token assinado server-side). */
export function useTrackLink() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useMutation({
    mutationFn: async (id: number): Promise<string> => {
      const response = await apiRequest<{ track_url: string }>(`/pedidos/${id}/track-link`);
      if (!response.ok) throw new Error(response.message);
      return response.data.track_url;
    }
  });
}

export function useUpdatePedido() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const { isOnline } = useOffline();
  const { info } = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, ...data }: { id: number } & Partial<CreatePedidoPayload>) => {
      if (isOnline) {
        const response = await apiRequest<{ pedido: Pedido }>(`/pedidos/${id}`, {
          method: 'PUT',
          body: JSON.stringify({ ...data, clientTimestamp: Date.now() }),
          headers: { 'Content-Type': 'application/json' }
        });
        if (!response.ok) throw new Error(response.message);
        return response.data;
      } else {
        await enqueue('update_order', { id, ...data });
        info('Salvo offline; será sincronizado quando online');
        throw new Error('OFFLINE_ENQUEUED');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      queryClient.invalidateQueries({ queryKey: ['pedido'] });
    }
  });
}

/**
 * Update status do pedido
 */
export function useUpdatePedidoStatus() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, status }: { id: number; status: string }) => {
      const response = await apiRequest<{ success: boolean }>(`/pedidos/${id}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      queryClient.invalidateQueries({ queryKey: ['pedido', id] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}

/**
 * Delete pedido (DELETE /pedidos/:id)
 */
export function useDeletePedido() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      const response = await apiRequest<{ success: boolean }>(`/pedidos/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      queryClient.invalidateQueries({ queryKey: ['pedido', id] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}

/**
 * Marcar pedido como impresso (POST /pedidos/:id/marcar-impresso)
 */
export function useMarcarImpresso() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      const response = await apiRequest<{ success: boolean }>(`/pedidos/${id}/marcar-impresso`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['pedido', id] });
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });
}

/**
 * Alterna flag de "cartão impresso" do pedido.
 * POST /pedidos/:id/toggle-cartao-impresso
 */
export function useToggleCartaoImpresso() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: { id: number; value?: boolean }) => {
      const { id, value } = params;
      const response = await apiRequest<{ success: boolean; data?: { pedido: Pedido } }>(
        `/pedidos/${id}/toggle-cartao-impresso`,
        {
          method: 'POST',
          body: value !== undefined ? JSON.stringify({ cartao_impresso: value }) : undefined,
        }
      );
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ['pedido', vars.id] });
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });
}

/**
 * Ocultar todos os pedidos concluídos (POST /pedidos/ocultar-concluidos)
 */
export function useOcultarPedidosConcluidos() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiRequest<{ success: boolean; count: number; message?: string }>('/pedidos/ocultar-concluidos', {
        method: 'POST',
      });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}

/**
 * Calcula distância de um pedido (GET /pedidos/:id/distancia)
 */
export function useCalcularDistanciaPedido() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, forceRecalc = true }: { id: number; forceRecalc?: boolean }) => {
      const query = forceRecalc ? '?force_recalc=true' : '';
      const response = await apiRequest<{ success: boolean; distancia_km?: number; taxa_entrega?: number }>(`/pedidos/${id}/distancia${query}`);
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      queryClient.invalidateQueries({ queryKey: ['pedido', variables.id] });
    },
  });
}

/**
 * Calcula taxa de entrega de um pedido (POST /pedidos/:id/calcular-taxa)
 */
export function useCalcularTaxaEntrega() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id }: { id: number }) => {
      const response = await apiRequest<{ success: boolean; taxa_entrega?: number; distancia_km?: number }>(`/pedidos/${id}/calcular-taxa`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      queryClient.invalidateQueries({ queryKey: ['pedido', variables.id] });
    },
  });
}

/**
 * Calcula distâncias em lote (POST /pedidos/calcular-distancias)
 */
export function useCalcularDistanciasLote() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ pedidoIds = [], forceRecalc = false }: { pedidoIds?: number[]; forceRecalc?: boolean }) => {
      const response = await apiRequest<{ success: boolean; results?: Array<{ id: number; distancia_km: number }> }>('/pedidos/calcular-distancias', {
        method: 'POST',
        body: JSON.stringify({
          pedido_ids: pedidoIds,
          force_recalc: forceRecalc,
        }),
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });
}
