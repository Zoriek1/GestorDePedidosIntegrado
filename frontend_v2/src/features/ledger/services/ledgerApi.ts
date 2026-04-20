/**
 * Ledger API — hooks React Query para o módulo de Recebíveis (double-entry)
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
  status: 'active' | 'settled';
  settled_at: string | null;
  settled_by_id: number | null;
  voided: boolean;
  created_at: string;
  created_by: number;
}

export interface LedgerBalance {
  user_id: number;
  total_credits: number;
  overdue_credits: number;
  due_today_credits: number;
  upcoming_credits: number;
  total_debits: number;
  balance: number;
}

export interface LedgerSummaryItem {
  user: { id: number; name: string; email: string; role: string };
  total_credits: number;
  overdue_credits: number;
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

export interface SettleResult {
  settled: number;
  amount: number;
  debit_id: number | null;
}

export interface PedidoAtribuido {
  entry_id: number;
  pedido_id: number;
  cliente: string | null;
  dia_entrega: string | null;
  week_ref: string | null;
  due_date: string | null;
  commission_amount: number;
  category: string;
  fonte_pedido_id?: number | null;
  fonte?: string | null;
  rate?: number | null; // percentual em %
  valor_pedido?: number | null;
  status: 'active' | 'settled';
  settled_at: string | null;
  settled_by_id: number | null;
}

export interface LedgerPeriodSource {
  source: string | null;
  source_id: number | null;
  source_slug: string | null;
  total: number;
}

export interface LedgerPeriod {
  period_date: string | null; // YYYY-MM-DD
  total_commission: number;
  active_commission: number;
  settled_commission: number;
  orders_count: number;
  is_overdue: boolean;
  status: 'atrasado' | 'pendente' | 'quitado' | 'sem_movimento';
  by_source: LedgerPeriodSource[];
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

/** Extrato com filtros (exclui voided automaticamente no backend) */
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

/** Pedidos atribuídos com detalhes de comissão */
export function usePedidosAtribuidos(filters: { from?: string; to?: string; user_id?: number } = {}) {
  const api = useApi();
  return useQuery<PedidoAtribuido[]>({
    queryKey: ['ledger-pedidos', filters],
    queryFn: async () => {
      const qs = toParams(filters as Record<string, string | number | undefined>);
      const res = await api<{ pedidos: PedidoAtribuido[] }>(`/ledger/pedidos${qs}`);
      if (!res.ok) throw new Error(res.message);
      return (res.data as { pedidos: PedidoAtribuido[] }).pedidos ?? [];
    },
    staleTime: 30_000,
  });
}

/** Comissões agrupadas por período de pagamento (due_date) */
export function useLedgerPeriods(userId?: number) {
  const api = useApi();
  return useQuery<LedgerPeriod[]>({
    queryKey: ['ledger-periods', userId],
    queryFn: async () => {
      const qs = userId ? `?user_id=${userId}` : '';
      const res = await api<{ periods: LedgerPeriod[] }>(`/ledger/periods${qs}`);
      if (!res.ok) throw new Error(res.message);
      return (res.data as { periods: LedgerPeriod[] }).periods ?? [];
    },
    staleTime: 30_000,
  });
}

/** CREDITs active do vendedor (pendentes de quitação em lote) */
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

/** Quitação em lote — substitui confirmação individual */
export function useSettleUser() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (userId?: number) => {
      const body = userId ? JSON.stringify({ user_id: userId }) : '{}';
      const res = await api<SettleResult>('/ledger/settle', { method: 'POST', body });
      if (!res.ok) throw new Error((res as { message: string }).message);
      return res.data as SettleResult;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ledger-balance'] });
      qc.invalidateQueries({ queryKey: ['ledger-pending'] });
      qc.invalidateQueries({ queryKey: ['ledger-entries'] });
      qc.invalidateQueries({ queryKey: ['ledger-summary'] });
      qc.invalidateQueries({ queryKey: ['ledger-periods'] });
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
      qc.invalidateQueries({ queryKey: ['ledger-periods'] });
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
      qc.invalidateQueries({ queryKey: ['ledger-periods'] });
    },
  });
}
