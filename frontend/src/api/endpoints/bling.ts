import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';
import { tenantKey } from '../../lib/tenantKey';

export interface BlingOption {
  id: number;
  bling_id: string;
  nome: string;
  tipo?: string | null;
  ativo: boolean;
}

export interface BlingPaymentMapping {
  id: number;
  gestor_payment_label: string;
  bling_payment_method_id?: number | null;
  bling_financial_account_id?: number | null;
  bling_category_id?: number | null;
  active: boolean;
  payment_method?: BlingOption | null;
  financial_account?: BlingOption | null;
  category?: BlingOption | null;
}

export interface BlingConfigResponse {
  payment_methods: BlingOption[];
  financial_accounts: BlingOption[];
  categories: BlingOption[];
  mappings: BlingPaymentMapping[];
}

export interface BlingOutbox {
  id: number;
  pedido_id: number;
  status: string;
  step: string;
  attempts: number;
  error_code?: string | null;
  error_message?: string | null;
  bling_order_id?: string | null;
  bling_order_number?: string | null;
  bling_receivable_ids?: Array<{ marker: string; id: string }>;
  payload?: unknown;
  response?: unknown;
  finished_at?: string | null;
}

export interface BlingPreview {
  pedido_id: number;
  valid: boolean;
  warnings: string[];
  errors: Array<{ message: string; details?: unknown }>;
  payload: unknown;
  financial_plan?: Array<{
    kind: string;
    marker: string;
    amount: number;
    due_date: string;
    payment_label: string;
    should_settle: boolean;
  }>;
  external_ref?: {
    id: number;
    provider: string;
    store_id: string;
    external_order_id: string;
    external_order_number?: string | null;
    pedido_id: number;
  } | null;
  outbox?: BlingOutbox | null;
}

export interface BlingLog {
  id: number;
  level: string;
  step?: string | null;
  message: string;
  request?: unknown;
  response?: unknown;
  status_code?: number | null;
  error_code?: string | null;
  created_at?: string;
}

function useApi() {
  const { getAuthHeader, getUser } = useAuth();
  const user = getUser(); const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  return { apiRequest: createApiRequest(getAuthHeader), storeKey };
}

export function useBlingStatus() {
  const { apiRequest, storeKey } = useApi();
  return useQuery({
    queryKey: tenantKey(storeKey, 'bling', 'status'),
    queryFn: async () => {
      const response = await apiRequest<{
        enabled: boolean;
        connected: boolean;
        counts: Record<string, number>;
      }>('/integrations/bling/status');
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
  });
}

export function useBlingInstall() {
  const { apiRequest } = useApi();
  return useMutation({
    mutationFn: async (): Promise<string> => {
      const response = await apiRequest<{ authorize_url: string }>('/integrations/bling/install');
      if (!response.ok) throw new Error(response.message);
      return response.data.authorize_url;
    },
  });
}

export function useBlingConfig() {
  const { apiRequest, storeKey } = useApi();
  return useQuery<BlingConfigResponse>({
    queryKey: tenantKey(storeKey, 'bling', 'config'),
    queryFn: async () => {
      const response = await apiRequest<BlingConfigResponse>('/integrations/bling/config');
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
  });
}

export function useSyncBlingConfig() {
  const { apiRequest, storeKey } = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await apiRequest('/integrations/bling/sync-config', { method: 'POST' });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'bling') });
    },
  });
}

export function useSaveBlingMapping() {
  const { apiRequest, storeKey } = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...data }: { id: number } & Partial<BlingPaymentMapping>) => {
      const response = await apiRequest<{ mapping: BlingPaymentMapping }>(
        `/integrations/bling/mappings/${id}`,
        { method: 'PUT', body: JSON.stringify(data) },
      );
      if (!response.ok) throw new Error(response.message);
      return response.data.mapping;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'bling', 'config') }),
  });
}

export function useBlingPreviewPedido(pedidoId: number) {
  const { apiRequest, storeKey } = useApi();
  return useQuery<BlingPreview>({
    queryKey: tenantKey(storeKey, 'bling', 'preview', pedidoId),
    queryFn: async () => {
      const response = await apiRequest<BlingPreview>(`/integrations/bling/pedidos/${pedidoId}/preview`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    enabled: !!pedidoId,
    staleTime: 5000,
  });
}

export function useSendBlingPedido() {
  const { apiRequest, storeKey } = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (pedidoId: number) => {
      const response = await apiRequest<{ outbox: BlingOutbox }>(
        `/integrations/bling/pedidos/${pedidoId}/send`,
        { method: 'POST' },
      );
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (_data, pedidoId) => {
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'bling', 'preview', pedidoId) });
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedido', pedidoId) });
    },
  });
}

export function useRetryBlingOutbox() {
  const { apiRequest, storeKey } = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (outboxId: number) => {
      const response = await apiRequest<{ outbox: BlingOutbox }>(
        `/integrations/bling/outbox/${outboxId}/retry`,
        { method: 'POST' },
      );
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'bling') });
      if (data.outbox?.pedido_id) {
        queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'bling', 'preview', data.outbox.pedido_id) });
      }
    },
  });
}

export function useBlingOutboxLogs(outboxId?: number | null) {
  const { apiRequest, storeKey } = useApi();
  return useQuery<{ logs: BlingLog[] }>({
    queryKey: tenantKey(storeKey, 'bling', 'logs', outboxId),
    queryFn: async () => {
      const response = await apiRequest<{ logs: BlingLog[] }>(
        `/integrations/bling/outbox/${outboxId}/logs`,
      );
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    enabled: !!outboxId,
  });
}
