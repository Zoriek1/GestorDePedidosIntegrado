/**
 * Users API — hooks React Query para gerenciamento de usuários (admin)
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../../../api/http';
import { useAuth } from '../../auth/authStore';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface AppUser {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'vendedor' | 'viewer';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PayrollConfig {
  id: number;
  user_id: number;
  category: string;
  label: string;
  amount: number;
  frequency: 'semanal' | 'mensal';
  payment_day: number | null; // 0=Seg...6=Dom; só para semanal
  is_active: boolean;
  created_at: string;
}

export interface CommissionConfig {
  id: number;
  user_id: number;
  source: string;
  rate: number;
  is_active: boolean;
  created_at: string;
}

export interface UserConfig {
  user: AppUser;
  payroll: PayrollConfig[];
  commission: CommissionConfig[];
}

export interface CreateUserPayload {
  name: string;
  email: string;
  password: string;
  role: 'admin' | 'vendedor' | 'viewer';
}

export interface UpdateUserPayload {
  name?: string;
  role?: 'admin' | 'vendedor' | 'viewer';
  is_active?: boolean;
  password?: string;
}

// ---------------------------------------------------------------------------
function useApi() {
  const { getAuthHeader } = useAuth();
  return createApiRequest(getAuthHeader);
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useUsers() {
  const api = useApi();
  return useQuery<AppUser[]>({
    queryKey: ['users'],
    queryFn: async () => {
      const res = await api<{ users: AppUser[] }>('/users');
      if (!res.ok) throw new Error(res.message);
      return (res.data as { users: AppUser[] }).users ?? [];
    },
    staleTime: 60_000,
  });
}

export function useUserConfig(userId: number) {
  const api = useApi();
  return useQuery<UserConfig>({
    queryKey: ['user-config', userId],
    queryFn: async () => {
      const res = await api<UserConfig>(`/users/${userId}/config`);
      if (!res.ok) throw new Error(res.message);
      return res.data as UserConfig;
    },
    enabled: userId > 0,
    staleTime: 30_000,
  });
}

export function useCreateUser() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateUserPayload) => {
      const res = await api('/users', { method: 'POST', body: JSON.stringify(payload) });
      if (!res.ok) throw new Error((res as { message: string }).message);
      return res.data as { user: AppUser };
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });
}

export function useUpdateUser(userId: number) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateUserPayload) => {
      const res = await api(`/users/${userId}`, { method: 'PUT', body: JSON.stringify(payload) });
      if (!res.ok) throw new Error((res as { message: string }).message);
      return res.data as { user: AppUser };
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });
}

export function useDeleteCommission(userId: number) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (configId: number) => {
      const res = await api(`/users/${userId}/commission/${configId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error((res as { message: string }).message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-config', userId] }),
  });
}

export function useDeleteUser(userId: number) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await api(`/users/${userId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error((res as { message: string }).message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });
}

export function useUpdatePayroll(userId: number) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (configs: Partial<PayrollConfig>[]) => {
      const res = await api(`/users/${userId}/payroll`, {
        method: 'PUT',
        body: JSON.stringify(configs),
      });
      if (!res.ok) throw new Error((res as { message: string }).message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-config', userId] }),
  });
}

export function useDeletePayroll(userId: number) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (configId: number) => {
      const res = await api(`/users/${userId}/payroll/${configId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error((res as { message: string }).message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-config', userId] }),
  });
}

export function useUpdateCommission(userId: number) {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (configs: { source: string; rate: number }[]) => {
      const res = await api(`/users/${userId}/commission`, {
        method: 'PUT',
        body: JSON.stringify(configs),
      });
      if (!res.ok) throw new Error((res as { message: string }).message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-config', userId] }),
  });
}
