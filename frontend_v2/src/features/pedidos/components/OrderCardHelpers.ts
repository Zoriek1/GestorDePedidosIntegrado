/**
 * Helper functions for OrderCard component
 */

import dayjs from 'dayjs';
import type { Pedido } from '../../../api/endpoints/pedidos';

/**
 * Check if a pedido is late (atrasado)
 * A pedido is considered late if:
 * - It has dia_entrega and horario
 * - The delivery date/time has passed
 * - The status is not 'concluido'
 */
export function isPedidoAtrasado(pedido: Pedido): boolean {
  if (!pedido.dia_entrega || !pedido.horario) return false;
  
  try {
    // Parse horario (format: "HH:mm" or "HH:mm:ss")
    const [hours, minutes] = pedido.horario.split(':').map(Number);
    const entregaDateTime = dayjs(pedido.dia_entrega)
      .hour(hours)
      .minute(minutes)
      .second(0)
      .millisecond(0);
    
    const now = dayjs();
    return entregaDateTime.isBefore(now) && pedido.status !== 'concluido';
  } catch {
    return false;
  }
}

/**
 * Format phone number to Brazilian format
 * Input: "11987654321" or "(11) 98765-4321"
 * Output: "(11) 98765-4321"
 */
export function formatPhone(phone: string | undefined): string {
  if (!phone) return '';
  
  // Remove all non-digits
  const digits = phone.replace(/\D/g, '');
  
  // Format based on length
  if (digits.length === 10) {
    // Landline: (11) 1234-5678
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  } else if (digits.length === 11) {
    // Mobile: (11) 98765-4321
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
  }
  
  // Return original if format is unknown
  return phone;
}

/**
 * Build complete address string from pedido fields
 */
export function getEnderecoCompleto(pedido: Pedido): string {
  if (pedido.endereco) {
    return pedido.endereco;
  }
  
  const parts = [
    pedido.rua,
    pedido.numero,
    pedido.bairro,
    pedido.cidade,
  ].filter(Boolean);
  
  return parts.join(', ') || 'Endereço não informado';
}

/**
 * Format created_at to "DD/MM/YYYY às HH:mm"
 */
export function formatCreatedAt(createdAt: string | undefined): string {
  if (!createdAt) return '';
  
  try {
    const date = dayjs(createdAt);
    return date.format('DD/MM/YYYY [às] HH:mm');
  } catch {
    return createdAt;
  }
}
