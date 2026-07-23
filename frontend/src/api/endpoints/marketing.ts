import { useMutation, useQuery } from '@tanstack/react-query';
import { createApiRequest } from '../http';
import { useAuth } from '../../features/auth/authStore';
import { tenantKey } from '../../lib/tenantKey';

export type MarketingDestination = 'meta' | 'ga4';

export interface MarketingDiagnosticResult {
  destination: MarketingDestination;
  ok: boolean;
  status: 'validated' | 'failed' | 'not_tested';
  duration_ms: number;
  http_status?: number;
  error?: string;
  request_id?: string;
  events_received?: number;
  trace_id?: string;
}

export interface MarketingConfigStatus {
  dispatch_enabled: boolean;
  meta: { configured: boolean; test_mode: boolean };
  ga4: { configured: boolean; validate_only: boolean; measurement_id?: string | null };
}

export interface MarketingOutboxItem {
  id: number;
  pedido_id: number;
  destino: MarketingDestination;
  evento: string;
  status: string;
  last_http_status?: number | null;
  last_error?: string | null;
  request_id?: string | null;
  next_status_check_at?: string | null;
  created_at?: string | null;
}

export interface MarketingOutboxStatus {
  counts: Array<{ destino: MarketingDestination; status: string; total: number }>;
  items: MarketingOutboxItem[];
}

function useApi() {
  const { getAuthHeader, getUser } = useAuth();
  const user = getUser(); const storeKey = user?.store_slug ?? String(user?.store_ref_id ?? 'default');
  return { apiRequest: createApiRequest(getAuthHeader), storeKey };
}

export function useMarketingConfig() {
  const { apiRequest, storeKey } = useApi();
  return useQuery({
    queryKey: tenantKey(storeKey, 'marketing', 'config'),
    queryFn: async () => {
      const response = await apiRequest<MarketingConfigStatus>(
        '/admin/marketing-conversions/config',
      );
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
  });
}

export function useMarketingOutbox() {
  const { apiRequest, storeKey } = useApi();
  return useQuery({
    queryKey: tenantKey(storeKey, 'marketing', 'outbox'),
    queryFn: async () => {
      const response = await apiRequest<MarketingOutboxStatus>(
        '/admin/marketing-conversions?limit=30',
      );
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    refetchInterval: 30000,
  });
}

export function useMarketingDiagnostic() {
  const { apiRequest } = useApi();
  return useMutation({
    mutationFn: async ({
      destination,
      metaTestEventCode,
    }: {
      destination: MarketingDestination;
      metaTestEventCode?: string;
    }) => {
      const options = {
        method: 'POST',
        body: JSON.stringify({ meta_test_event_code: metaTestEventCode || undefined }),
        timeoutMs: 45000,
      } as RequestInit & { timeoutMs: number };
      const response = await apiRequest<{ result: MarketingDiagnosticResult }>(
        `/admin/marketing-conversions/diagnostics/${destination}`,
        options,
      );
      if (!response.ok) throw new Error(response.message);
      return response.data.result;
    },
  });
}
