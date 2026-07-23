import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import http from '@/api/http';
import { tenantKey } from '@/lib/tenantKey';

const BASE = '/api/integrations/mercadopago';

export function useMercadoPagoStatus() {
  return useQuery({
    queryKey: [...tenantKey(), 'mp-status'],
    queryFn: () => http.get(`${BASE}/status`).then((r) => r.data),
  });
}

export function useMercadoPagoConfig() {
  return useQuery({
    queryKey: [...tenantKey(), 'mp-config'],
    queryFn: () => http.get(`${BASE}/config`).then((r) => r.data),
  });
}

export function useMercadoPagoSetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => http.post(`${BASE}/setup`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...tenantKey(), 'mp-status'] });
      qc.invalidateQueries({ queryKey: [...tenantKey(), 'mp-config'] });
    },
  });
}

export function useMercadoPagoProcessPending() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => http.post(`${BASE}/process-pending`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...tenantKey(), 'mp-outbox'] });
    },
  });
}

export function useMercadoPagoOutboxList(status?: string) {
  return useQuery({
    queryKey: [...tenantKey(), 'mp-outbox', status],
    queryFn: () =>
      http.get(`${BASE}/outbox`, { params: status ? { status } : undefined }).then((r) => r.data),
  });
}

export function useMercadoPagoOutboxLogs(outboxId: number | null) {
  return useQuery({
    queryKey: [...tenantKey(), 'mp-outbox-logs', outboxId],
    queryFn: () => http.get(`${BASE}/outbox/${outboxId}/logs`).then((r) => r.data),
    enabled: outboxId !== null,
  });
}

export function useMercadoPagoRetryOutbox() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (outboxId: number) =>
      http.post(`${BASE}/outbox/${outboxId}/retry`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...tenantKey(), 'mp-outbox'] });
    },
  });
}
