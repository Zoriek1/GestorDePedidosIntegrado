import type { Customer } from '../../../api/endpoints/customers';

export interface CustomerKPIs {
  novosMes: number;
  ticketMedioGlobal: number;
  ltvMedio: number;
}

export interface CustomerBadge {
  label: string;
  color: 'default' | 'success' | 'warning' | 'info' | 'error';
}

export interface ICustomerInsightsService {
  computeKPIs(customers: Customer[]): CustomerKPIs;
  getBadges(customer: Customer, vipThreshold: number, now?: Date): CustomerBadge[];
  resolveVipThreshold(customers: Customer[]): number;
}

