/**
 * Order mapping use cases
 * Domain logic for order status labels and colors
 */

export type StatusColor = 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';

const statusColors: Record<string, StatusColor> = {
  agendado: 'info',
  em_producao: 'warning',
  pronto_entrega: 'success',
  pronto_retirada: 'success',
  em_rota: 'secondary',
  concluido: 'secondary',
};

const statusLabels: Record<string, string> = {
  agendado: 'Agendado',
  em_producao: 'Em Produção',
  pronto_entrega: 'Pronto para Entrega',
  pronto_retirada: 'Pronto para Retirada',
  em_rota: 'Em Rota',
  concluido: 'Concluído',
};

/**
 * Get color for order status
 * @param status - Order status string
 * @returns MUI Chip color
 */
export function getStatusColor(status: string): StatusColor {
  return statusColors[status] || 'default';
}

/**
 * Get label for order status
 * @param status - Order status string
 * @returns Human-readable label
 */
export function getStatusLabel(status: string): string {
  return statusLabels[status] || status;
}

