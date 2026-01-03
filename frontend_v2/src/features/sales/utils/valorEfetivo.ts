/**
 * Helper para cálculo de valor efetivo baseado no status de pagamento
 * 
 * Regras:
 * - PENDENTE: 0% do valor_total
 * - PARCIAL ou contém "50%": 50% do valor_total
 * - PAGO ou REALIZADO: 100% do valor_total
 * - Outros/Null: 0% (assumir não pago)
 * 
 * IMPORTANTE: valor já é o total cobrado (inclui entrega).
 * taxa_entrega é apenas informativo e não deve ser subtraído.
 * 
 * Fórmula:
 * valor_total = parseFloat(valor || '0')  // valor já inclui entrega
 * valor_efetivo = valor_total * percentual_pagamento
 */

import type { Pedido } from '../../../api/endpoints/pedidos';

/**
 * Calcula valor efetivo baseado no status de pagamento
 * @param valor - Valor total como string (ex: "150.00") - já inclui entrega
 * @param _taxaEntrega - Taxa de entrega (não utilizado, apenas para compatibilidade)
 * @param statusPagamento - Status do pagamento (PENDENTE, PAGO, REALIZADO, 50% FEITO, PARCIAL, etc.)
 * @returns Valor efetivo (já ponderado pelo status de pagamento)
 */
export function calcularValorEfetivo(
  valor: string | undefined,
  _taxaEntrega: number | undefined,
  statusPagamento: string | undefined
): number {
  // valor já é o total cobrado (inclui entrega), não subtrair taxa_entrega
  // taxa_entrega é apenas informativo
  const valorTotal = parseFloat(valor || '0');
  
  // Se não há status de pagamento, assumir não pago (0%)
  if (!statusPagamento) return 0;
  
  const statusUpper = statusPagamento.toUpperCase().trim();
  
  // PENDENTE = 0%
  if (statusUpper === 'PENDENTE') return 0;
  
  // PAGO ou REALIZADO = 100%
  if (statusUpper === 'PAGO' || statusUpper === 'REALIZADO') {
    return valorTotal;
  }
  
  // PARCIAL ou contém "50%" = 50%
  // Removido regra genérica 'FEITO' para evitar falsos positivos
  if (statusUpper.includes('50%') || statusUpper === 'PARCIAL') {
    return valorTotal * 0.5;
  }
  
  // Outros casos = não pago (0%)
  return 0;
}

/**
 * Calcula valor efetivo a partir de um objeto Pedido
 * @param pedido - Objeto Pedido completo
 * @returns Valor efetivo
 */
export function calcularValorEfetivoPedido(pedido: Pedido): number {
  return calcularValorEfetivo(
    pedido.valor,
    pedido.taxa_entrega,
    pedido.status_pagamento
  );
}

/**
 * Calcula valor bruto do pedido (sem considerar status de pagamento)
 * @param pedido - Objeto Pedido completo
 * @returns Valor bruto
 */
export function calcularValorBrutoPedido(pedido: Pedido): number {
  return parseFloat(pedido.valor || '0');
}

/**
 * Calcula valor recebido baseado no status de pagamento
 * @param pedido - Objeto Pedido completo
 * @returns Valor recebido (considerando status de pagamento: parcial=50%, pendente=0%, realizado=100%)
 */
export function calcularValorRecebidoPedido(pedido: Pedido): number {
  const valorBruto = calcularValorBrutoPedido(pedido);
  const statusPagamento = pedido.status_pagamento;
  
  if (!statusPagamento) return 0;
  
  const statusUpper = statusPagamento.toUpperCase().trim();
  
  // PENDENTE = 0%
  if (statusUpper === 'PENDENTE') return 0;
  
  // PAGO ou REALIZADO = 100%
  if (statusUpper === 'PAGO' || statusUpper === 'REALIZADO') {
    return valorBruto;
  }
  
  // PARCIAL ou contém "50%" = 50%
  if (statusUpper.includes('50%') || statusUpper === 'PARCIAL') {
    return valorBruto * 0.5;
  }
  
  // Outros casos = não pago (0%)
  return 0;
}

/**
 * Calcula valor efetivo (valor bruto - frete)
 * @param pedido - Objeto Pedido completo
 * @returns Valor efetivo (bruto - frete)
 */
export function calcularValorEfetivoComFrete(pedido: Pedido): number {
  const valorBruto = calcularValorBrutoPedido(pedido);
  const taxaEntrega = pedido.taxa_entrega || 0;
  return valorBruto - taxaEntrega;
}