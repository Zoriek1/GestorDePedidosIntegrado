import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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

    expect(screen.getByText(/A Receber .*Vendedor Teste/i)).toBeInTheDocument();
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

  it('PendingPaymentsCard chama settle por pedido_ids ao clicar Recebi', async () => {
    const mutate = vi.fn();
    vi.mocked(usePendingPayments).mockReturnValue({
      data: {
        user_id: 1,
        competencia_tipo: 'semanal',
        competencia: '2025-W07',
        competencias_disponiveis: ['2025-W07'],
        atrasado: {
          total: 120,
          total_pedidos: 1,
          pedidos: [
            {
              ledger_entry_id: 11,
              pedido_id: 99,
              cliente: 'Cliente Teste',
              fonte: 'WhatsApp',
              dia_entrega: '2025-02-10',
              week_ref: '2025-02-10',
              due_date: '2025-02-11',
              amount: 120,
              category: 'comissao_whatsapp',
              status: 'atrasado',
              competencia: '2025-W07',
            },
          ],
        },
        a_receber: { total: 0, total_pedidos: 0, pedidos: [] },
        quitado: { total: 0, total_pedidos: 0, pedidos: [] },
      },
      isLoading: false,
    } as never);
    vi.mocked(useSettleUser).mockReturnValue({
      mutate,
      isPending: false,
    } as never);

    render(<PendingPaymentsCard userId={1} isAdmin />);

    fireEvent.click(screen.getByRole('button', { name: /Recebi pagamento .*120,00/i }));
    await waitFor(() => {
      expect(mutate).toHaveBeenCalledWith({
        user_id: 1,
        pedido_ids: [99],
        contexto: {
          section: 'atrasado',
          competencia_tipo: 'semanal',
          competencia: '2025-W07',
        },
      });
    });
  });
});
