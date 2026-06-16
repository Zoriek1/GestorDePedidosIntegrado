/**
 * Helper functions for OrderCard component
 */

import dayjs from 'dayjs';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { formatDateBR } from '../../../lib/format/date';
import { formatBRL } from '../../../lib/format/currency';

/**
 * Check if a pedido is late (atrasado)
 * A pedido is considered late if:
 * - It has dia_entrega and horario
 * - The delivery date/time has passed
 * - The status is not 'concluido'
 */
export function isPedidoAtrasado(pedido: Pedido): boolean {
  if (!pedido.dia_entrega || !pedido.horario) return false;
  
  try {
    // Parse horario (format: "HH:mm" or "HH:mm:ss")
    const [hours, minutes] = pedido.horario.split(':').map(Number);
    const entregaDateTime = dayjs(pedido.dia_entrega)
      .hour(hours)
      .minute(minutes)
      .second(0)
      .millisecond(0);
    
    const now = dayjs();
    return entregaDateTime.isBefore(now) && pedido.status !== 'concluido';
  } catch {
    return false;
  }
}

/**
 * Format phone number to Brazilian format
 * Input: "11987654321" or "(11) 98765-4321"
 * Output: "(11) 98765-4321"
 */
export function formatPhone(phone: string | undefined): string {
  if (!phone) return '';
  
  // Remove all non-digits
  const digits = phone.replace(/\D/g, '');
  
  // Format based on length
  if (digits.length === 10) {
    // Landline: (11) 1234-5678
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  } else if (digits.length === 11) {
    // Mobile: (11) 98765-4321
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
  }
  
  // Return original if format is unknown
  return phone;
}

/**
 * Build complete address string from pedido fields
 */
export function getEnderecoCompleto(pedido: Pedido): string {
  if (pedido.endereco) {
    return pedido.endereco;
  }
  
  const parts = [
    pedido.rua,
    pedido.numero,
    pedido.tipo_local === 'casa' && pedido.quadra ? `Qd ${pedido.quadra}` : null,
    pedido.tipo_local === 'casa' && pedido.lote ? `Lt ${pedido.lote}` : null,
    pedido.complemento,
    pedido.bairro,
    pedido.cidade,
  ].filter(Boolean);
  
  return parts.join(', ') || 'Endereço não informado';
}

/**
 * Format created_at to "DD/MM/YYYY às HH:mm"
 */
export function getDetalhesEntrega(pedido: Pedido): string[] {
  if (pedido.tipo_pedido !== 'Entrega') return [];
  const tipoLocal = pedido.tipo_local || 'casa';
  const lines: string[] = [];

  if (tipoLocal === 'predio') {
    if (pedido.nome_local) lines.push(`Prédio: ${pedido.nome_local}`);
    const predioParts = [
      pedido.apto ? `AP ${pedido.apto}` : null,
      pedido.bloco ? `Bloco ${pedido.bloco}` : null,
      pedido.torre ? `Torre ${pedido.torre}` : null,
      pedido.andar ? `${pedido.andar}º andar` : null,
    ].filter(Boolean);
    if (predioParts.length) lines.push(predioParts.join(' · '));
  } else if (tipoLocal === 'comercial') {
    if (pedido.nome_local) lines.push(`Comercial: ${pedido.nome_local}`);
  } else {
    const casaParts = [
      pedido.quadra ? `Qd ${pedido.quadra}` : null,
      pedido.lote ? `Lt ${pedido.lote}` : null,
    ].filter(Boolean);
    if (casaParts.length) lines.push(casaParts.join(' · '));
  }

  if (pedido.complemento) lines.push(`Complemento: ${pedido.complemento}`);
  if (pedido.obs_entrega) lines.push(`Referência: ${pedido.obs_entrega}`);
  return lines;
}

export function formatCreatedAt(createdAt: string | undefined): string {
  if (!createdAt) return '';
  
  try {
    const date = dayjs(createdAt);
    return date.format('DD/MM/YYYY [às] HH:mm');
  } catch {
    return createdAt;
  }
}

function addLine(lines: string[], line: string | undefined) {
  if (!line) return;
  const trimmed = line.trim();
  if (!trimmed) return;
  lines.push(trimmed);
}

function addBlankLine(lines: string[]) {
  if (lines.length === 0) return;
  if (lines[lines.length - 1] === '') return;
  lines.push('');
}

function buildMapsLinkFromAddress(address: string): string {
  const query = encodeURIComponent(address);
  return `https://www.google.com/maps/search/?api=1&query=${query}`;
}

/** Formata CEP "74215140" -> "74215-140" (mantém original se não tiver 8 dígitos). */
function formatCep(cep: string | undefined): string {
  if (!cep) return '';
  const digits = cep.replace(/\D/g, '');
  if (digits.length !== 8) return cep.trim();
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

/**
 * Linha 1 do endereço: complemento/local (prédio, comercial ou casa).
 * Ex.: "Edifício Salinas, AP 208"
 */
function buildLocalLine(pedido: Pedido): string {
  const tipoLocal = pedido.tipo_local || 'casa';
  let parts: (string | null)[] = [];

  if (tipoLocal === 'predio') {
    parts = [
      pedido.nome_local ? `Edifício ${pedido.nome_local}` : 'Edifício',
      pedido.apto ? `AP ${pedido.apto}` : null,
      pedido.bloco ? `Bloco ${pedido.bloco}` : null,
      pedido.torre ? `Torre ${pedido.torre}` : null,
      pedido.andar ? `${pedido.andar}º andar` : null,
    ];
  } else if (tipoLocal === 'comercial') {
    parts = [pedido.nome_local || null];
  } else {
    parts = [
      pedido.quadra ? `Qd ${pedido.quadra}` : null,
      pedido.lote ? `Lt ${pedido.lote}` : null,
    ];
  }

  if (pedido.complemento) parts.push(pedido.complemento);
  return parts.filter(Boolean).join(', ');
}

/**
 * Linha 2 do endereço: rua, número – bairro, cidade – CEP.
 * Ex.: "Rua T 33, 350 – Setor Bueno, Goiânia – CEP 74215-140"
 */
function buildRuaLine(pedido: Pedido): string {
  const ruaNumero = [pedido.rua, pedido.numero].filter(Boolean).join(', ');
  const bairroCidade = [pedido.bairro, pedido.cidade].filter(Boolean).join(', ');
  const cep = formatCep(pedido.cep);
  const cepLabel = cep ? `CEP ${cep}` : '';
  return [ruaNumero, bairroCidade, cepLabel].filter(Boolean).join(' – ');
}

/** Endereço numa linha só, usado apenas para a query do Google Maps. */
function buildMapsQuery(pedido: Pedido): string {
  if (pedido.endereco) return pedido.endereco;
  return [pedido.rua, pedido.numero, pedido.bairro, pedido.cidade, formatCep(pedido.cep)]
    .filter(Boolean)
    .join(', ');
}

/**
 * Indica presença do cartão sem revelar o conteúdo.
 * Mais de 3 caracteres -> tem cartão escrito.
 */
function buildCartaoLine(pedido: Pedido): string {
  const texto = pedido.mensagem?.trim() ?? '';
  return texto.length > 3 ? '📦 Cartão: escrito incluso' : '📦 Sem cartão';
}

// Formas de pagamento cobradas no ato da entrega (dinheiro em mãos).
// Pix/cartão/boleto são pagos remotamente: pendente => aguardar confirmação.
const FORMAS_COBRANCA_NA_ENTREGA = ['Dinheiro'];

/**
 * Bloco de pagamento para o entregador (1 ou 2 linhas):
 *  - Linha de status: "💰 Pagamento: ❌ PENDENTE (Pix)"
 *  - Linha de instrução (quando aplicável):
 *      Pendente/Parcial cobrável na entrega -> "💰 Cobrar R$ X na entrega (dinheiro)"
 *      Pendente/Parcial remoto             -> "⚠️ Entregar somente após confirmação de pagamento."
 *  - Pago -> só a linha de status, sem instrução.
 */
function buildPagamentoBlock(pedido: Pedido): string[] {
  const status = pedido.status_pagamento || 'Pendente';
  const forma = pedido.pagamento?.trim();
  const formaSuffix = forma ? ` (${forma})` : '';
  const lines: string[] = [];

  if (status === 'Pago') {
    lines.push(`💰 Pagamento: ✅ PAGO${formaSuffix}`);
    return lines;
  }

  const statusLabel = status === 'Parcial' ? '⚠️ PARCIAL' : '❌ PENDENTE';
  lines.push(`💰 Pagamento: ${statusLabel}${formaSuffix}`);

  const cobrarNaEntrega = !!forma && FORMAS_COBRANCA_NA_ENTREGA.includes(forma);
  if (cobrarNaEntrega && pedido.valor) {
    lines.push(`💰 Cobrar ${formatBRL(pedido.valor)} na entrega (dinheiro)`);
  } else {
    lines.push('⚠️ Entregar somente após confirmação de pagamento.');
  }

  return lines;
}

/**
 * Monta mensagem operacional para encaminhar ao entregador.
 * - NÃO é a "mensagem do cartão" (pedido.mensagem) — apenas sinaliza se há cartão.
 * - Inclui apenas campos relevantes e existentes.
 */
export function buildEncaminharMensagem(pedido: Pedido): string {
  const lines: string[] = [];
  const isEntrega = pedido.tipo_pedido === 'Entrega';

  // Header
  addLine(lines, `📦 Pedido #${pedido.id} • ${pedido.tipo_pedido.toUpperCase()}`);
  const dataHora = `${formatDateBR(pedido.dia_entrega)} ${pedido.horario || ''}`.trim();
  addLine(lines, `🗓️ ${dataHora}`);

  // Contato (telefone + WhatsApp na mesma linha; clicáveis em apps)
  addBlankLine(lines);
  addLine(lines, `👤 Cliente: ${pedido.cliente}`);
  const telefoneFmt = pedido.telefone_cliente ? formatPhone(pedido.telefone_cliente) : '';
  const waLink = buildWhatsAppLink(pedido.telefone_cliente);
  const contatoParts = [
    telefoneFmt ? `📞 ${telefoneFmt}` : '',
    waLink ? `WhatsApp: ${waLink}` : '',
  ].filter(Boolean);
  if (contatoParts.length) addLine(lines, contatoParts.join(' | '));
  addLine(lines, `🎁 Para: ${pedido.destinatario}`);

  // Item + presença de cartão (sem revelar o texto)
  addBlankLine(lines);
  const qty = pedido.quantidade && pedido.quantidade > 1 ? ` x${pedido.quantidade}` : '';
  const cor = pedido.flores_cor?.trim() ? ` (${pedido.flores_cor.trim()})` : '';
  addLine(lines, `🌹 Item: ${pedido.produto}${qty}${cor}`);
  addLine(lines, buildCartaoLine(pedido));

  // Endereço (2 linhas) + instrução + mapa separado
  addBlankLine(lines);
  if (isEntrega) {
    addLine(lines, '📍 Endereço:');
    addLine(lines, buildLocalLine(pedido));
    addLine(lines, buildRuaLine(pedido));
    if (pedido.obs_entrega?.trim()) {
      addLine(lines, `🔹 Instrução: ${pedido.obs_entrega.trim()}`);
    }
    addLine(lines, `🗺️ Mapa: ${buildMapsLinkFromAddress(buildMapsQuery(pedido))}`);
  } else {
    addLine(lines, '🏪 Retirada na loja');
  }

  // Pagamento (status + instrução)
  addBlankLine(lines);
  buildPagamentoBlock(pedido).forEach((line) => addLine(lines, line));

  // Confirmação do entregador
  addBlankLine(lines);
  addLine(lines, '✅ Responda com "OK" ao pegar o pedido.');

  return lines.join('\n');
}

function buildWhatsAppLink(phone: string | undefined): string | undefined {
  if (!phone) return undefined;
  const digits = phone.replace(/\D/g, '');
  if (!digits) return undefined;

  // BR: se vier 10/11 dígitos, prefixa 55; se já vier com DDI, mantém
  const withCountry =
    digits.length === 10 || digits.length === 11 ? `55${digits}` : digits;

  return `https://wa.me/${withCountry}`;
}
