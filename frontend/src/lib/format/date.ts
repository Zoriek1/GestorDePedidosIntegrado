/**
 * Date formatting utilities
 * Unified date formatting using date-fns
 */

import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale/pt-BR';

/**
 * Format date to Brazilian format (dd/MM/yyyy)
 * @param date - Date object or ISO string
 * @returns Formatted string like "25/12/2024"
 */
export function formatDateBR(date: Date | string): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return format(dateObj, 'dd/MM/yyyy', { locale: ptBR });
  } catch {
    // Fallback to original string if parsing fails
    return typeof date === 'string' ? date : date.toISOString().split('T')[0];
  }
}

/**
 * Format date and time to Brazilian format (dd/MM/yyyy HH:mm)
 * @param date - Date object or ISO string
 * @returns Formatted string like "25/12/2024 14:30"
 */
export function formatDateTimeBR(date: Date | string): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return format(dateObj, 'dd/MM/yyyy HH:mm', { locale: ptBR });
  } catch {
    // Fallback to date only if parsing fails
    return formatDateBR(date);
  }
}

