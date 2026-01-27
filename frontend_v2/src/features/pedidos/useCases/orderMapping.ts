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

/**
 * Get color for payment status
 * @param status - Payment status string (Pago, Pendente, Parcial)
 * @returns MUI Chip color
 */
export function getPaymentStatusColor(status: string | undefined): StatusColor {
  if (!status) return 'warning'; // Default to 'Pendente' color
  
  switch (status) {
    case 'Pago':
      return 'success';
    case 'Pendente':
      return 'warning';
    case 'Parcial':
      return 'info';
    default:
      return 'default';
  }
}

/**
 * Get label for payment status
 * @param status - Payment status string
 * @returns Human-readable label (defaults to 'Pendente' if undefined/null)
 */
export function getPaymentStatusLabel(status: string | undefined): string {
  return status || 'Pendente';
}

