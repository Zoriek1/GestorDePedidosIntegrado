/**
 * Order mapping use cases
 * Domain logic for order status labels and colors
 */

export type StatusColor = 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';

const statusColors: Record<string, StatusColor> = {
  agendado: 'info',
  producao: 'warning',
  pronto: 'success',
  entregue: 'secondary',
  cancelado: 'error',
  concluido: 'secondary',
};

const statusLabels: Record<string, string> = {
  agendado: 'Agendado',
  producao: 'Em Produção',
  pronto: 'Pronto',
  entregue: 'Entregue',
  cancelado: 'Cancelado',
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

