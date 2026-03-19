/**
 * Leads UTM API endpoints
 * React Query hooks para listar leads da landing page
 */

import { useQuery } from '@tanstack/react-query';
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
  utm_source?: string;
  utm_campaign?: string;
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
      if (filters.utm_source) params.set('utm_source', filters.utm_source);
      if (filters.utm_campaign) params.set('utm_campaign', filters.utm_campaign);
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
