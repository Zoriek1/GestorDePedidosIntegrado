/**
 * Catálogo curado de arranjos (CAT-01).
 * - useArranjoSugestoes: autocomplete por similaridade/frequência (debounce no componente).
 * - usePromoverArranjo: promove um nome ao catálogo (confirmação da florista).
 */
import { useQuery, useMutation } from '@tanstack/react-query';
import { createApiRequest } from '../../../api/http';
import { useAuth } from '../../auth/authStore';

interface SugestoesResponse {
  arranjos: string[];
  total: number;
}

export function useArranjoSugestoes(q: string, enabled: boolean) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  return useQuery<string[]>({
    queryKey: ['catalogo-arranjos', q],
    queryFn: async () => {
      const r = await apiRequest<SugestoesResponse>(
        `/catalogo/arranjos?q=${encodeURIComponent(q)}`
      );
      if (!r.ok) throw new Error(r.message);
      return r.data.arranjos ?? [];
    },
    enabled,
    staleTime: 30_000,
  });
}

export function usePromoverArranjo() {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);
  return useMutation({
    mutationFn: async (nome: string) => {
      const r = await apiRequest('/catalogo/arranjos/promover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome }),
      });
      if (!r.ok) throw new Error(r.message);
      return r.data;
    },
  });
}
