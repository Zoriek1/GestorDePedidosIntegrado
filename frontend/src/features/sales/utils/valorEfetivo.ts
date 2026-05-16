/**
 * Helper para cálculo de valor efetivo baseado no status de pagamento
 *
 * Regras:
 * - PENDENTE: 0% do valor_total
 * - PARCIAL ou contém "50%": 50% do valor_total
 * - PAGO ou REALIZADO: 100% do valor_total
 * - Outros/Null: 0% (assumir não pago)
 *
 * Semântica dos campos:
 * - valor = total cobrado do cliente (inclui frete cobrado ao cliente)
 * - taxa_entrega = custo pago ao entregador (custo operacional da entrega)
 * - valor - taxa_entrega = receita líquida após pagar o entregador
 *
 * Fórmula:
 * valor_total = parseFloat(valor || '0')
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
  const valorTotal = parseValorToNumber(valor);
  
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
 * Parse valor de qualquer formato para número
 * Suporta:
 * - Números: 10.00, 65
 * - Formato BR: "R$ 65,00", "65,00", "1.234,56"
 * - Formato US: "10.00", "65.5"
 * - String simples: "10", "65"
 */
function parseValorToNumber(valor: string | number | undefined): number {
  if (!valor) return 0;
  
  // Se já é número, retornar diretamente
  if (typeof valor === 'number') {
    return isNaN(valor) ? 0 : valor;
  }
  
  const valorStr = String(valor).trim();
  if (!valorStr || valorStr === '') return 0;
  
  // Remover R$ e espaços
  let cleaned = valorStr.replace(/R\$\s?/gi, '').trim();
  
  // Detectar formato brasileiro (tem vírgula)
  if (cleaned.includes(',')) {
    // Formato BR: "65,00" ou "1.234,56"
    // Remover pontos (separadores de milhar) e substituir vírgula por ponto
    cleaned = cleaned.replace(/\./g, '').replace(',', '.');
    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? 0 : parsed;
  }
  
  // Detectar formato americano ou número simples (tem ponto decimal ou não)
  if (cleaned.includes('.')) {
    // Contar pontos - se tiver mais de 1, pode ser separador de milhar
    const dotCount = (cleaned.match(/\./g) || []).length;
    if (dotCount === 1) {
      // Um ponto = decimal americano: "10.00"
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? 0 : parsed;
    } else {
      // Múltiplos pontos = separadores de milhar: "1.234.567"
      // Remover todos os pontos
      cleaned = cleaned.replace(/\./g, '');
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? 0 : parsed;
    }
  }
  
  // String simples sem formatação: "10", "65"
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Calcula valor bruto do pedido (sem considerar status de pagamento)
 * @param pedido - Objeto Pedido completo
 * @returns Valor bruto
 */
export function calcularValorBrutoPedido(pedido: Pedido): number {
  return parseValorToNumber(pedido.valor);
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
 * Receita líquida do pedido: total cobrado do cliente menos o custo pago ao entregador.
 * valor = total do cliente (inclui frete cobrado); taxa_entrega = custo ao entregador.
 * @param pedido - Objeto Pedido completo
 * @returns Receita líquida (valor - taxa_entrega)
 */
export function calcularValorEfetivoComFrete(pedido: Pedido): number {
  const valorBruto = calcularValorBrutoPedido(pedido);
  const taxaEntrega = pedido.taxa_entrega || 0;
  return valorBruto - taxaEntrega;
}