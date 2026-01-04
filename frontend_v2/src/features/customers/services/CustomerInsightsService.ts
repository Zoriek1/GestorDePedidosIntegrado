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
    const ltv = customer.ltv || 0;
    const totalPedidos = customer.total_pedidos || 0;
    const ticketMedio = totalPedidos > 0 ? ltv / totalPedidos : 0;

    // VIP - Top 10% por LTV
    if (ltv >= vipThreshold && vipThreshold !== Number.MAX_SAFE_INTEGER) {
      badges.push({ label: 'VIP', color: 'success' });
    }

    // Novo - Criado este mês
    if (customer.created_at) {
      const created = new Date(customer.created_at);
      const startMonth = new Date(now.getFullYear(), now.getMonth(), 1);
      if (created >= startMonth) {
        badges.push({ label: 'Novo', color: 'info' });
      }
    }

    // Ausente - Sem pedidos há mais de 30 dias
    if (customer.ultimo_pedido) {
      const last = new Date(customer.ultimo_pedido);
      const diffDays = (now.getTime() - last.getTime()) / (1000 * 60 * 60 * 24);
      if (diffDays > 30) {
        badges.push({ label: 'Ausente', color: 'warning' });
      }
    } else if (totalPedidos === 0) {
      // Nunca fez pedido
      badges.push({ label: 'Sem Pedidos', color: 'default' });
    }

    // Frequente - 5+ pedidos
    if (totalPedidos >= 5) {
      badges.push({ label: 'Frequente', color: 'info' });
    }

    // Alto Valor - LTV acima de R$ 500
    if (ltv >= 500) {
      badges.push({ label: 'Alto Valor', color: 'success' });
    }

    // Ticket Médio Alto - Acima de R$ 200 por pedido
    if (ticketMedio >= 200 && totalPedidos >= 2) {
      badges.push({ label: 'Ticket Alto', color: 'success' });
    }

    // Inativo - Sem pedidos há mais de 90 dias
    if (customer.ultimo_pedido) {
      const last = new Date(customer.ultimo_pedido);
      const diffDays = (now.getTime() - last.getTime()) / (1000 * 60 * 60 * 24);
      if (diffDays > 90) {
        badges.push({ label: 'Inativo', color: 'error' });
      }
    }

    // Cliente Fiel - 10+ pedidos
    if (totalPedidos >= 10) {
      badges.push({ label: 'Cliente Fiel', color: 'success' });
    }

    return badges;
  }
}

