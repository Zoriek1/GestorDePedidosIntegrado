/**
 * Ledger API — hooks React Query para o módulo de Recebíveis
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../../../api/http';
import { useAuth } from '../../auth/authStore';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface LedgerEntry {
  id: number;
  user_id: number;
  type: 'CREDIT' | 'DEBIT';
  category: string;
  amount: number;
  description: string;
  pedido_id: number | null;
  week_ref: string; // YYYY-MM-DD (segunda-feira)
  due_date: string | null; // YYYY-MM-DD
  status: 'pendente' | 'confirmado';
  confirmed_at: string | null;
  created_at: string;
  created_by: number;
}

export interface LedgerBalance {
  user_id: number;
  total_credits: number;
  confirmed_credits: number;
  pending_credits: number;
  total_debits: number;
  balance: number;
}

export interface LedgerSummaryItem {
  user: { id: number; name: string; email: string; role: string };
  total_credits: number;
  confirmed_credits: number;
  pending_credits: number;
  total_debits: number;
  balance: number;
}

export interface EntriesFilters {
  user_id?: number;
  week_ref?: string;
  category?: string;
  from?: string;
  to?: string;
}

export interface ManualEntryPayload {
  user_id: number;
  type: 'CREDIT' | 'DEBIT';
  category: string;
  amount: number;
  description?: string;
  week_ref?: string;
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------
function useApi() {
  const { getAuthHeader } = useAuth();
  return createApiRequest(getAuthHeader);
}

function toParams(obj: Record<string, string | number | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== '') p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : '';
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/** Saldo devedor do usuário atual (vendedor) ou de qualquer um (admin via user_id) */
export function useLedgerBalance(userId?: number) {
  const api = useApi();
  return useQuery<LedgerBalance>({
    queryKey: ['ledger-balance', userId],
    queryFn: async () => {
      const qs = userId ? `?user_id=${userId}` : '';
      const res = await api<LedgerBalance>(`/ledger/balance${qs}`);
      if (!res.ok) throw new Error(res.message);
      return res.data as LedgerBalance;
    },
    staleTime: 30_000,
  });
}

/** Extrato com filtros */
export function useLedgerEntries(filters: EntriesFilters = {}) {
  const api = useApi();
  return useQuery<LedgerEntry[]>({
    queryKey: ['ledger-entries', filters],
    queryFn: async () => {
      const qs = toParams(filters as Record<string, string | number | undefined>);
      const res = await api<{ entries: LedgerEntry[] }>(`/ledger/entries${qs}`);
      if (!res.ok) throw new Error(res.message);
      return (res.data as { entries: LedgerEntry[] }).entries ?? [];
    },
    staleTime: 30_000,
  });
}

/** Pagamentos pendentes de confirmação */
export function usePendingPayments(userId?: number) {
  const api = useApi();
  return useQuery<LedgerEntry[]>({
    queryKey: ['ledger-pending', userId],
    queryFn: async () => {
      const qs = userId ? `?user_id=${userId}` : '';
      const res = await api<{ entries: LedgerEntry[] }>(`/ledger/pending${qs}`);
      if (!res.ok) throw new Error(res.message);
      return (res.data as { entries: LedgerEntry[] }).entries ?? [];
    },
    staleTime: 20_000,
  });
}

/** Confirmar recebimento (funcionário ou admin) */
export function useConfirmEntry() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (entryId: number) => {
      const res = await api(`/ledger/entries/${entryId}/confirm`, { method: 'PUT' });
      if (!res.ok) throw new Error((res as { message: string }).message);
      return res;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ledger-balance'] });
      qc.invalidateQueries({ queryKey: ['ledger-pending'] });
      qc.invalidateQueries({ queryKey: ['ledger-entries'] });
      qc.invalidateQueries({ queryKey: ['ledger-summary'] });
    },
  });
}

/** Resumo de todos os vendedores (admin) */
export function useLedgerSummary() {
  const api = useApi();
  return useQuery<LedgerSummaryItem[]>({
    queryKey: ['ledger-summary'],
    queryFn: async () => {
      const res = await api<{ summary: LedgerSummaryItem[] }>('/ledger/summary');
      if (!res.ok) throw new Error(res.message);
      return (res.data as { summary: LedgerSummaryItem[] }).summary ?? [];
    },
    staleTime: 60_000,
  });
}

/** Lançamento manual (admin) */
export function useCreateLedgerEntry() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ManualEntryPayload) => {
      const res = await api('/ledger/entries', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error((res as { message: string }).message);
      return res;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ledger-balance'] });
      qc.invalidateQueries({ queryKey: ['ledger-entries'] });
      qc.invalidateQueries({ queryKey: ['ledger-summary'] });
    },
  });
}

/** Gerar créditos fixos da semana (admin) */
export function useGenerateWeekly() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (weekRef?: string) => {
      const res = await api('/ledger/generate-weekly', {
        method: 'POST',
        body: JSON.stringify({ week_ref: weekRef }),
      });
      if (!res.ok) throw new Error((res as { message: string }).message);
      return res.data as { created: number; skipped: number };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ledger-balance'] });
      qc.invalidateQueries({ queryKey: ['ledger-entries'] });
      qc.invalidateQueries({ queryKey: ['ledger-pending'] });
      qc.invalidateQueries({ queryKey: ['ledger-summary'] });
    },
  });
}

/** Gerar calendário de créditos para N semanas (admin) */
export function useGenerateCalendar() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ nWeeks, fromWeek }: { nWeeks: number; fromWeek?: string }) => {
      const res = await api('/ledger/generate-calendar', {
        method: 'POST',
        body: JSON.stringify({ n_weeks: nWeeks, from_week: fromWeek }),
      });
      if (!res.ok) throw new Error((res as { message: string }).message);
      return res.data as { weeks: string[]; total_created: number; total_skipped: number };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ledger-balance'] });
      qc.invalidateQueries({ queryKey: ['ledger-entries'] });
      qc.invalidateQueries({ queryKey: ['ledger-pending'] });
      qc.invalidateQueries({ queryKey: ['ledger-summary'] });
    },
  });
}
