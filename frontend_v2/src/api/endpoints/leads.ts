/**
 * Leads UTM API endpoints
 * React Query hooks para listar leads da landing page
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';

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
}

export interface LeadsResponse {
  leads: Lead[];
  total: number;
  page: number;
  pages: number;
}

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
  date_from?: string;
  date_to?: string;
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
