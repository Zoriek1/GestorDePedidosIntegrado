import { useAuth } from '../features/auth/authStore';

export function useStoreKey(): string {
  const { getUser } = useAuth();
  const user = getUser();
  return user?.store_slug ?? String(user?.store_ref_id ?? 'default');
}

export function tenantKey(storeKey: string, ...parts: unknown[]): unknown[] {
  return [storeKey, ...parts];
}