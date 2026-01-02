import type { Customer } from '../../../api/endpoints/customers';
import type { CustomerBadge, CustomerKPIs, ICustomerInsightsService } from './ICustomerInsightsService';

export class CustomerInsightsService implements ICustomerInsightsService {
  computeKPIs(customers: Customer[]): CustomerKPIs {
    const now = new Date();
    const startMonth = new Date(now.getFullYear(), now.getMonth(), 1);

    let novosMes = 0;
    let ltvSum = 0;
    let ltvCount = 0;
    let ticketSum = 0;
    let ticketDivisor = 0;

    customers.forEach((c) => {
      if (c.created_at) {
        const created = new Date(c.created_at);
        if (created >= startMonth) {
          novosMes += 1;
        }
      }

      if (typeof c.ltv === 'number') {
        ltvSum += c.ltv;
        ltvCount += 1;
      }

      if (typeof c.ltv === 'number' && typeof c.total_pedidos === 'number' && c.total_pedidos > 0) {
        ticketSum += c.ltv;
        ticketDivisor += c.total_pedidos;
      }
    });

    return {
      novosMes,
      ticketMedioGlobal: ticketDivisor > 0 ? ticketSum / ticketDivisor : 0,
      ltvMedio: ltvCount > 0 ? ltvSum / ltvCount : 0,
    };
  }

  resolveVipThreshold(customers: Customer[]): number {
    const ltvs = customers
      .map((c) => c.ltv || 0)
      .filter((v) => v > 0)
      .sort((a, b) => b - a);
    if (ltvs.length === 0) return Number.MAX_SAFE_INTEGER;
    const idx = Math.max(0, Math.floor(ltvs.length * 0.1) - 1);
    return ltvs[idx] ?? Number.MAX_SAFE_INTEGER;
  }

  getBadges(customer: Customer, vipThreshold: number, now: Date = new Date()): CustomerBadge[] {
    const badges: CustomerBadge[] = [];

    if ((customer.ltv || 0) >= vipThreshold && vipThreshold !== Number.MAX_SAFE_INTEGER) {
      badges.push({ label: 'VIP', color: 'success' });
    }

    if (customer.created_at) {
      const created = new Date(customer.created_at);
      const startMonth = new Date(now.getFullYear(), now.getMonth(), 1);
      if (created >= startMonth) {
        badges.push({ label: 'Novo', color: 'info' });
      }
    }

    if (customer.ultimo_pedido) {
      const last = new Date(customer.ultimo_pedido);
      const diffDays = (now.getTime() - last.getTime()) / (1000 * 60 * 60 * 24);
      if (diffDays > 30) {
        badges.push({ label: 'Ausente', color: 'warning' });
      }
    }

    return badges;
  }
}

