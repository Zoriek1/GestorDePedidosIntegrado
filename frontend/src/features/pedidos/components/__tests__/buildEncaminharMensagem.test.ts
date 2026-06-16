/**
 * Testes para buildEncaminharMensagem (mensagem operacional ao entregador).
 *
 * Cobre:
 *  - encoding correto (acentos UTF-8, sem mojibake)
 *  - endereço em 2 linhas + mapa separado
 *  - presença de cartão: vazio / curto (<=3) / longo (>3) sem revelar conteúdo
 *  - pagamento pago x pendente (incl. cobrança em dinheiro na entrega)
 *  - linha de confirmação do entregador
 */

import { describe, it, expect } from 'vitest';
import { buildEncaminharMensagem } from '../OrderCardHelpers';
import type { Pedido } from '../../../../api/endpoints/pedidos';

function makePedido(overrides: Partial<Pedido> = {}): Pedido {
  return {
    id: 833,
    cliente: 'TESTE',
    telefone_cliente: '62099999999',
    destinatario: 'TESTE DESTINATARIO',
    tipo_pedido: 'Entrega',
    produto: 'Buquê 12 rosas',
    flores_cor: 'Cor de rosa',
    valor: 'R$ 150,00',
    dia_entrega: '2026-06-15',
    horario: '14:00',
    cep: '74215140',
    rua: 'Rua T 33',
    numero: '350',
    tipo_local: 'predio',
    nome_local: 'Salinas',
    apto: '208',
    bairro: 'Setor Bueno',
    cidade: 'Goiânia',
    mensagem: 'Feliz aniversário, com amor!',
    pagamento: 'Pix',
    status_pagamento: 'Pendente',
    status: 'liberado',
    quantidade: 1,
    oculto: false,
    impresso: false,
    ...overrides,
  } as Pedido;
}

describe('buildEncaminharMensagem', () => {
  it('produz mensagem completa no formato esperado (entrega, prédio, cartão, pendente Pix)', () => {
    const msg = buildEncaminharMensagem(makePedido());

    expect(msg).toContain('📦 Pedido #833 • ENTREGA');
    expect(msg).toContain('🗓️ 15/06/2026 14:00');
    expect(msg).toContain('👤 Cliente: TESTE');
    expect(msg).toContain('📞 (62) 09999-9999 | WhatsApp: https://wa.me/5562099999999');
    expect(msg).toContain('🎁 Para: TESTE DESTINATARIO');
    expect(msg).toContain('🌹 Item: Buquê 12 rosas (Cor de rosa)');
    expect(msg).toContain('📦 Cartão: escrito incluso');
    expect(msg).toContain('📍 Endereço:');
    expect(msg).toContain('Edifício Salinas, AP 208');
    expect(msg).toContain('Rua T 33, 350 – Setor Bueno, Goiânia – CEP 74215-140');
    expect(msg).toContain('🗺️ Mapa: https://www.google.com/maps/search/?api=1&query=');
    expect(msg).toContain('💰 Pagamento: ❌ PENDENTE (Pix)');
    expect(msg).toContain('⚠️ Entregar somente após confirmação de pagamento.');
    expect(msg).toContain('✅ Responda com "OK" ao pegar o pedido.');
  });

  it('encoding: sem mojibake e com acentuação correta', () => {
    const msg = buildEncaminharMensagem(makePedido());
    expect(msg).not.toMatch(/Ã|Â|Ã©|Ã­/);
    expect(msg).toContain('Edifício');
    expect(msg).toContain('Goiânia');
  });

  it('nunca revela o texto real do cartão', () => {
    const msg = buildEncaminharMensagem(
      makePedido({ mensagem: 'Feliz aniversário, com amor!' })
    );
    expect(msg).not.toContain('Feliz aniversário, com amor!');
    expect(msg).toContain('📦 Cartão: escrito incluso');
  });

  it('cartão vazio -> "Sem cartão"', () => {
    expect(buildEncaminharMensagem(makePedido({ mensagem: '' }))).toContain('📦 Sem cartão');
    expect(buildEncaminharMensagem(makePedido({ mensagem: undefined }))).toContain('📦 Sem cartão');
  });

  it('cartão curto (3 caracteres) -> "Sem cartão"', () => {
    expect(buildEncaminharMensagem(makePedido({ mensagem: 'Oi!' }))).toContain('📦 Sem cartão');
    expect(buildEncaminharMensagem(makePedido({ mensagem: '   x   ' }))).toContain('📦 Sem cartão');
  });

  it('cartão longo (>3 caracteres) -> "escrito incluso"', () => {
    expect(buildEncaminharMensagem(makePedido({ mensagem: 'Parabéns!' }))).toContain(
      '📦 Cartão: escrito incluso'
    );
  });

  it('pagamento Pago -> sem aviso de confirmação', () => {
    const msg = buildEncaminharMensagem(
      makePedido({ status_pagamento: 'Pago', pagamento: 'Pix' })
    );
    expect(msg).toContain('💰 Pagamento: ✅ PAGO (Pix)');
    expect(msg).not.toContain('Entregar somente após confirmação');
    expect(msg).not.toContain('Cobrar');
  });

  it('pendente em Dinheiro -> cobrar na entrega com valor', () => {
    const msg = buildEncaminharMensagem(
      makePedido({ status_pagamento: 'Pendente', pagamento: 'Dinheiro' })
    );
    expect(msg).toContain('💰 Pagamento: ❌ PENDENTE (Dinheiro)');
    // formatBRL usa NBSP entre "R$" e o valor; checamos as partes estáveis.
    expect(msg).toMatch(/💰 Cobrar R\$\s?150,00 na entrega \(dinheiro\)/);
    expect(msg).not.toContain('Entregar somente após confirmação');
  });

  it('retirada na loja -> sem bloco de endereço/mapa', () => {
    const msg = buildEncaminharMensagem(
      makePedido({ tipo_pedido: 'Retirada' })
    );
    expect(msg).toContain('📦 Pedido #833 • RETIRADA');
    expect(msg).toContain('🏪 Retirada na loja');
    expect(msg).not.toContain('🗺️ Mapa');
  });

  it('instrução de entrega aparece após o endereço quando existe', () => {
    const msg = buildEncaminharMensagem(
      makePedido({ obs_entrega: 'Deixar com porteiro' })
    );
    expect(msg).toContain('🔹 Instrução: Deixar com porteiro');
  });
});
