import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { BalanceCard } from '../BalanceCard';
import { PaymentPeriodsCard } from '../PaymentPeriodsCard';
import { PendingPaymentsCard } from '../PendingPaymentsCard';

vi.mock('../../services/ledgerApi', () => ({
  usePendingPayments: vi.fn(),
  useSettleUser: vi.fn(),
}));

import { usePendingPayments, useSettleUser } from '../../services/ledgerApi';

describe('Recebiveis UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('BalanceCard usa saldo principal como A Receber', () => {
    render(
      <BalanceCard
        userName="Vendedor Teste"
        balance={{
          user_id: 1,
          total_credits: 300,
          overdue_credits: 50,
          due_today_credits: 100,
          upcoming_credits: 150,
          total_debits: 200,
          balance: 300,
        }}
      />
    );

    expect(screen.getByText(/A Receber —/i)).toBeInTheDocument();
    expect(screen.getByText(/300,00/)).toBeInTheDocument();
    expect(screen.getByText(/Quitado:/i)).toBeInTheDocument();
  });

  it('PaymentPeriodsCard mostra subtotal por fonte real', () => {
    render(
      <PaymentPeriodsCard
        periods={[
          {
            period_date: '2025-02-14',
            total_commission: 80,
            active_commission: 30,
            settled_commission: 50,
            orders_count: 2,
            is_overdue: false,
            status: 'pendente',
            by_source: [
              { source: 'WhatsApp', source_id: 1, source_slug: 'whatsapp', total: 30 },
              { source: 'Site', source_id: 2, source_slug: 'site', total: 50 },
            ],
          },
        ]}
      />
    );

    expect(screen.getByText(/WhatsApp:/i)).toBeInTheDocument();
    expect(screen.getByText(/Site:/i)).toBeInTheDocument();
  });

  it('PendingPaymentsCard chama settle em lote ao clicar Recebi', () => {
    const mutate = vi.fn();
    vi.mocked(usePendingPayments).mockReturnValue({
      data: [
        {
          id: 11,
          user_id: 1,
          type: 'CREDIT',
          category: 'comissao_whatsapp',
          amount: 120,
          description: 'Comissão',
          pedido_id: 99,
          week_ref: '2025-02-10',
          due_date: '2025-02-14',
          status: 'active',
          settled_at: null,
          settled_by_id: null,
          voided: false,
          created_at: '2025-02-10 10:00:00',
          created_by: 1,
        },
      ],
      isLoading: false,
    } as never);
    vi.mocked(useSettleUser).mockReturnValue({
      mutate,
      isPending: false,
    } as never);

    render(<PendingPaymentsCard userId={1} isAdmin />);

    fireEvent.click(screen.getByRole('button', { name: /Recebi pagamento/i }));
    expect(mutate).toHaveBeenCalledWith(1);
  });
});
