/**
 * Leads UTM API endpoints
 * React Query hooks para listar leads da landing page
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

export interface LeadTouchpoint {
  id: number;
  lead_id: number;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  utm_content: string | null;
  utm_term: string | null;
  utm_id: string | null;
  src: string | null;
  placement: string | null;
  sck: string | null;
  fbclid: string | null;
  fbp: string | null;
  referrer: string | null;
  url: string | null;
  ip_address: string | null;
  is_paid: boolean;
  created_at: string | null;
}

export interface Lead {
  id: number;
  event: string | null;
  url: string | null;
  referrer: string | null;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  utm_content: string | null;
  utm_term: string | null;
  src: string | null;
  sck: string | null;
  phone: string | null;
  token_rastreio: string | null;
  token_valido: boolean | null;
  status: string | null;
  fbclid: string | null;
  fbp: string | null;
  ip_address: string | null;
  created_at: string | null;
  pedido_id: number | null;
  valor_pedido: string | null;
  first_touch_id: number | null;
  last_touch_id: number | null;
  first_touch: LeadTouchpoint | null;
  last_touch: LeadTouchpoint | null;
}

export interface LeadTouchpointsResponse {
  ok: boolean;
  lead_id: number;
  first_touch_id: number | null;
  last_touch_id: number | null;
  touchpoints: LeadTouchpoint[];
}

export interface LeadsResponse {
  leads: Lead[];
  total: number;
  page: number;
  pages: number;
}

export type LeadsPeriod = 'today' | '14d' | 'all' | 'custom';

export interface LeadsFilters {
  page?: number;
  per_page?: number;
  /** Um único evento, ou `all` para não filtrar por evento */
  event?: string;
  /** Vários eventos separados por vírgula (ex.: modal_open,whatsapp_click,site_click) */
  events?: string;
  utm_source?: string;
  utm_campaign?: string;
  /** Filtra pelo código único de rastreio (token WhatsApp) */
  token_rastreio?: string;
  /** Filtra pelo status do lead */
  status?: string;
  /** Janela temporal resolvida no backend (today, 14d, all). Use `custom` com date_from/date_to. */
  period?: LeadsPeriod;
  date_from?: string;
  date_to?: string;
}

export interface LeadsStatsBucket {
  pendentes: number;
  com_telefone: number;
  compras: number;
  total: number;
}

export interface LeadsStatsResponse {
  ok: boolean;
  today: LeadsStatsBucket;
  last_14d: LeadsStatsBucket;
}

export interface BulkStatusResponse {
  ok: boolean;
  updated: number;
  skipped: number;
  skipped_ids: number[];
}

export interface BulkDisqualifyUpdate {
  id: number;
  phone?: string;
}

export interface BulkDisqualifyResponse {
  ok: boolean;
  updated: number;
  skipped: number;
  skipped_ids: number[];
}

export function useLeads(filters: LeadsFilters = {}) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<LeadsResponse>({
    queryKey: ['leads', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.page) params.set('page', String(filters.page));
      if (filters.per_page) params.set('per_page', String(filters.per_page));
      if (filters.events) {
        params.set('events', filters.events);
      } else if (filters.event) {
        params.set('event', filters.event);
      }
      if (filters.utm_source) params.set('utm_source', filters.utm_source);
      if (filters.utm_campaign) params.set('utm_campaign', filters.utm_campaign);
      if (filters.token_rastreio?.trim()) {
        params.set('token_rastreio', filters.token_rastreio.trim());
      }
      if (filters.status) params.set('status', filters.status);
      if (filters.period) params.set('period', filters.period);
      if (filters.date_from) params.set('date_from', filters.date_from);
      if (filters.date_to) params.set('date_to', filters.date_to);

      const qs = params.toString();
      const endpoint = `/leads${qs ? `?${qs}` : ''}`;
      const response = await apiRequest<LeadsResponse>(endpoint);
      if (!response.ok) {
        throw new Error(response.message ?? 'Erro ao carregar leads');
      }
      return response.data as LeadsResponse;
    },
  });
}

interface UpdateLeadPhoneResponse {
  ok: boolean;
  lead: Lead;
}

interface UpdateLeadStatusResponse {
  ok: boolean;
  lead: Lead;
}

export function useUpdateLeadStatus() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: { id?: number; token_rastreio?: string; status: string }) => {
      const { id, token_rastreio, status } = input;
      const path =
        token_rastreio != null && token_rastreio.trim() !== ''
          ? '/leads/by-token/status'
          : `/leads/${id}/status`;
      const body =
        token_rastreio != null && token_rastreio.trim() !== ''
          ? JSON.stringify({ token_rastreio: token_rastreio.trim(), status })
          : JSON.stringify({ status });
      if (!token_rastreio?.trim() && id == null) {
        throw new Error('Informe o id do lead ou o token de rastreio');
      }
      const response = await apiRequest<UpdateLeadStatusResponse>(path, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body,
      });

      if (!response.ok) {
        throw new Error(response.message ?? 'Erro ao atualizar status do lead');
      }

      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
}

export function useLeadsStats() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<LeadsStatsResponse>({
    queryKey: ['leads', 'stats'],
    queryFn: async () => {
      const response = await apiRequest<LeadsStatsResponse>('/leads/stats');
      if (!response.ok) {
        throw new Error(response.message ?? 'Erro ao carregar stats de leads');
      }
      return response.data as LeadsStatsResponse;
    },
    staleTime: 60_000,
  });
}

export function useBulkUpdateLeadStatus() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: { ids: number[]; status: string }) => {
      if (!input.ids.length) {
        throw new Error('Selecione ao menos um lead');
      }
      const response = await apiRequest<BulkStatusResponse>('/leads/bulk/status', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: input.ids, status: input.status }),
      });
      if (!response.ok) {
        throw new Error(response.message ?? 'Erro ao atualizar leads em lote');
      }
      return response.data as BulkStatusResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
}

export function useBulkDisqualifyLeads() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: { updates: BulkDisqualifyUpdate[] }) => {
      if (!input.updates.length) {
        throw new Error('Selecione ao menos um lead');
      }
      const response = await apiRequest<BulkDisqualifyResponse>('/leads/bulk/disqualify', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates: input.updates }),
      });
      if (!response.ok) {
        throw new Error(response.message ?? 'Erro ao desqualificar leads');
      }
      return response.data as BulkDisqualifyResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
}

export function useUpdateLeadPhone() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: { id?: number; token_rastreio?: string; phone: string }) => {
      const { id, token_rastreio, phone } = input;
      const path =
        token_rastreio != null && token_rastreio.trim() !== ''
          ? '/leads/by-token/phone'
          : `/leads/${id}/phone`;
      const body =
        token_rastreio != null && token_rastreio.trim() !== ''
          ? JSON.stringify({ token_rastreio: token_rastreio.trim(), phone })
          : JSON.stringify({ phone });
      if (!token_rastreio?.trim() && id == null) {
        throw new Error('Informe o id do lead ou o token de rastreio');
      }
      const response = await apiRequest<UpdateLeadPhoneResponse>(path, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body,
      });

      if (!response.ok) {
        throw new Error(response.message ?? 'Erro ao atualizar telefone do lead');
      }

      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
}
