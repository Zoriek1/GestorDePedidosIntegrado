/**
 * Customer mapping use cases
 * Domain logic for customer data transformation
 */

import type { Customer } from '../../../api/endpoints/customers';

/**
 * Format customer phone number (if needed)
 * Currently just returns as-is, but can be extended for formatting
 * @param customer - Customer object
 * @returns Formatted phone or original
 */
export function formatCustomerPhone(customer: Customer): string {
  return customer.telefone || '';
}

/**
 * Get customer display name
 * @param customer - Customer object
 * @returns Display name
 */
export function getCustomerDisplayName(customer: Customer): string {
  return customer.nome || `Cliente #${customer.id}`;
}

