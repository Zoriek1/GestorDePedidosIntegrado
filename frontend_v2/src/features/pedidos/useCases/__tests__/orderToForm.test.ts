import { describe, it, expect } from 'vitest';
import { orderToForm } from '../orderToForm';
import type { Pedido } from '../../../../api/endpoints/pedidos';

function makePedido(overrides: Partial<Pedido> = {}): Pedido {
  return {
    id: 1,
    cliente: 'Maria Silva',
    telefone_cliente: '11999999999',
    destinatario: 'João',
    tipo_pedido: 'Entrega',
    produto: 'Buquê de rosas',
    dia_entrega: '2026-03-01',
    horario: '14:00',
    status: 'pendente',
    quantidade: 1,
    oculto: false,
    impresso: false,
    fonte_pedido_id: 2,
    ...overrides,
  };
}

describe('orderToForm', () => {
  it('mapeia campos básicos corretamente', () => {
    const pedido = makePedido();
    const form = orderToForm(pedido);

    expect(form.cliente).toBe('Maria Silva');
    expect(form.tipo_pedido).toBe('Entrega');
    expect(form.produto).toBe('Buquê de rosas');
    expect(form.dia_entrega).toBe('2026-03-01');
    expect(form.fonte_pedido_id).toBe(2);
  });

  it('usa fonte_pedido_id=1 como fallback quando ausente', () => {
    const pedido = makePedido({ fonte_pedido_id: undefined });
    const form = orderToForm(pedido);
    expect(form.fonte_pedido_id).toBe(1);
  });

  it('usa "Entrega" como fallback para tipo_pedido inválido', () => {
    const pedido = makePedido({ tipo_pedido: 'Invalido' as 'Entrega' });
    const form = orderToForm(pedido);
    expect(form.tipo_pedido).toBe('Entrega');
  });

  it('define status_pagamento como "Pendente" por padrão', () => {
    const pedido = makePedido({ status_pagamento: undefined });
    const form = orderToForm(pedido);
    expect(form.status_pagamento).toBe('Pendente');
  });

  it('aceita status_pagamento válido', () => {
    const pedido = makePedido({ status_pagamento: 'Pago' });
    const form = orderToForm(pedido);
    expect(form.status_pagamento).toBe('Pago');
  });

  it('converte valor string para moeda formatada', () => {
    const pedido = makePedido({ valor: '150.00' });
    const form = orderToForm(pedido);
    expect(form.valor).toBeTruthy();
  });

  it('define cliente_modo como "busca" quando cliente_id presente', () => {
    const pedido = makePedido({ cliente_id: 42 });
    const form = orderToForm(pedido);
    expect(form.cliente_modo).toBe('busca');
    expect(form.cliente_id).toBe(42);
  });

  it('define cliente_modo como "novo" quando cliente_id ausente', () => {
    const pedido = makePedido({ cliente_id: undefined });
    const form = orderToForm(pedido);
    expect(form.cliente_modo).toBe('novo');
  });

  it('converte dia_entrega de formato ISO para YYYY-MM-DD', () => {
    const pedido = makePedido({ dia_entrega: '2026-03-15T00:00:00.000Z' });
    const form = orderToForm(pedido);
    expect(form.dia_entrega).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
