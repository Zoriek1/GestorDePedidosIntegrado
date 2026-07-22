import { Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from './authStore';

/**
 * Libera a rota apenas quando a loja tem o módulo de Leads habilitado.
 *
 * O módulo é opt-in por loja (`stores.leads_enabled`) porque a captação pública
 * ainda resolve sempre a loja default — liberar Leads para um segundo tenant
 * misturaria os dados. Lojas sem a flag são devolvidas para a home, sem avisar
 * que o módulo existe.
 *
 * Isto é navegação, não autorização: quem barra de fato é o guard do backend em
 * `/api/leads`, que lê a flag do banco a cada request.
 */
export function RequireLeadsEnabled({ children }: { children: ReactNode }) {
  const { getUser, isJwtUser } = useAuth();
  const user = getUser();

  // Sessão legada (Basic Auth) não traz payload de loja; nesses ambientes só
  // existe a loja default, então mantemos o acesso.
  const enabled = user?.leads_enabled ?? !isJwtUser();

  if (!enabled) return <Navigate to="/" replace />;
  return <>{children}</>;
}
