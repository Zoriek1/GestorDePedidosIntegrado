/**
 * Helpers de role — centraliza checks usados pela UI.
 * Os checks inline (`role === 'x'`) que já existem no código foram mantidos;
 * novos lugares devem importar daqui.
 */
import type { AuthUser } from './authStore';

export const isAdmin = (role?: string | null) => role === 'admin';
export const isVendedor = (role?: string | null) => role === 'vendedor';
export const isEntregador = (role?: string | null) => role === 'entregador';
export const isAtendente = (role?: string | null) => role === 'atendente';

export function canDeletePedido(
  user: AuthUser | null,
  pedido: { vendedor_id?: number | null } | undefined | null
): boolean {
  if (!user) return false;
  if (isAdmin(user.role)) return true;
  if (isVendedor(user.role) && pedido?.vendedor_id && user.id === pedido.vendedor_id) {
    return true;
  }
  return false;
}

export function canFinalizarEntrega(
  user: AuthUser | null,
  pedido: { entregador_id?: number | null; status?: string } | undefined | null
): boolean {
  if (!user || !pedido) return false;
  if ((pedido.status || '').toLowerCase() === 'concluido') return false;
  if (isAdmin(user.role)) return !!pedido.entregador_id;
  if (isEntregador(user.role) && pedido.entregador_id && user.id === pedido.entregador_id) {
    return true;
  }
  return false;
}
