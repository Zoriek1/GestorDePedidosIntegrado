import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';
import { tenantKey } from '../../lib/tenantKey';

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

export interface NuvemshopConfig {
  connected: boolean;
  store_id: string | null;
  active: boolean;
  default_vendedor_id: number | null;
  default_vendedor_name: string | null;
}

export function usePendingSchedules() {
  const { getAuthHeader, getUser } = useAuth();
  const user = getUser(); const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<PendingSchedulesResponse>({
    queryKey: tenantKey(storeKey, 'nuvemshop', 'pendencias-agendamento'),
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

export function useNuvemshopConfig() {
  const { getAuthHeader, getUser } = useAuth();
  const user = getUser(); const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<NuvemshopConfig>({
    queryKey: tenantKey(storeKey, 'nuvemshop', 'config'),
    queryFn: async () => {
      const response = await apiRequest<NuvemshopConfig>('/integrations/nuvemshop/config');
      if (!response.ok) {
        throw new Error(response.message);
      }
      return response.data as NuvemshopConfig;
    },
  });
}

export function useDefineSchedule() {
  const { getAuthHeader, getUser } = useAuth();
  const user = getUser(); const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
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
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'nuvemshop', 'pendencias-agendamento') });
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedidos') });
    },
  });
}

export function useProcessPendingNuvemshop() {
  const { getAuthHeader, getUser } = useAuth();
  const user = getUser(); const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
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
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'nuvemshop', 'pendencias-agendamento') });
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedidos') });
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

export interface Vendedor {
  id: number;
  name: string;
  email: string;
  role: string;
}

export function useListVendedores() {
  const { getAuthHeader, getUser } = useAuth();
  const user = getUser(); const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<Vendedor[]>({
    queryKey: tenantKey(storeKey, 'users', 'vendedores'),
    queryFn: async () => {
      const response = await apiRequest<{ users: Vendedor[] }>('/users');
      if (!response.ok) throw new Error(response.message);
      return ((response.data as { users: Vendedor[] }).users ?? []).filter(
        (u) => u.role === 'vendedor',
      );
    },
  });
}

export function useAssignVendorNuvemshop() {
  const { getAuthHeader, getUser } = useAuth();
  const user = getUser(); const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (vendedor_id: number) => {
      const response = await apiRequest('/integrations/nuvemshop/atribuir-vendedor', {
        method: 'POST',
        body: JSON.stringify({ vendedor_id }),
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error(response.message);
      return response.data as { atribuidos: number };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedidos') });
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

export function useSaveDefaultVendorNuvemshop() {
  const { getAuthHeader, getUser } = useAuth();
  const user = getUser(); const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (vendedor_id: number | null) => {
      const response = await apiRequest('/integrations/nuvemshop/config', {
        method: 'PUT',
        body: JSON.stringify({ vendedor_id }),
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error(response.message);
      return response.data as NuvemshopConfig;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'nuvemshop', 'config') });
      queryClient.invalidateQueries({ queryKey: tenantKey(storeKey, 'pedidos') });
    },
  });
}
