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
    pedido.bairro,
    pedido.cidade,
  ].filter(Boolean);
  
  return parts.join(', ') || 'Endereço não informado';
}

/** Rótulo amigável do tipo de local de entrega. */
export function getTipoLocalLabel(tipo?: string): string {
  switch (tipo) {
    case 'predio':
      return 'Prédio';
    case 'comercial':
      return 'Comercial';
    default:
      return 'Casa';
  }
}

/**
 * Monta a linha de detalhe do prédio: "AP 302 · Bloco A · Torre 2 · 3º andar".
 * Aceita um objeto parcial para servir tanto o pedido quanto o formulário.
 */
export function getDetalheLocal(p: {
  apartamento?: string;
  bloco?: string;
  torre?: string;
  andar?: string;
}): string {
  return [
    p.apartamento ? `AP ${p.apartamento}` : null,
    p.bloco ? `Bloco ${p.bloco}` : null,
    p.torre ? `Torre ${p.torre}` : null,
    p.andar ? `${p.andar}º andar` : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

/**
 * Format created_at to "DD/MM/YYYY às HH:mm"
 */
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

function buildWhatsAppLink(phone: string | undefined): string | undefined {
  if (!phone) return undefined;
  const digits = phone.replace(/\D/g, '');
  if (!digits) return undefined;

  // BR: se vier 10/11 dígitos, prefixa 55; se já vier com DDI, mantém
  const withCountry =
    digits.length === 10 || digits.length === 11 ? `55${digits}` : digits;

  return `https://wa.me/${withCountry}`;
}

/**
 * Monta mensagem operacional para encaminhar ao entregador.
 * - NÃO é a "mensagem do cartão" (pedido.mensagem)
 * - Inclui apenas campos relevantes e existentes
 */
export function buildEncaminharMensagem(pedido: Pedido): string {
  const lines: string[] = [];

  // Header (curto)
  addLine(lines, `Pedido #${pedido.id}`);
  addLine(lines, `${pedido.tipo_pedido} • ${formatDateBR(pedido.dia_entrega)} ${pedido.horario || ''}`.trim());

  // Contato (separado para ficar "clicável" em apps)
  addBlankLine(lines);
  addLine(lines, `Cliente: ${pedido.cliente}`);
  const telefoneFmt = pedido.telefone_cliente ? formatPhone(pedido.telefone_cliente) : '';
  if (telefoneFmt) addLine(lines, `Tel: ${telefoneFmt}`);
  const waLink = buildWhatsAppLink(pedido.telefone_cliente);
  if (waLink) addLine(lines, `WhatsApp: ${waLink}`);

  // Destinatário + item
  addBlankLine(lines);
  addLine(lines, `Para: ${pedido.destinatario}`);
  const qty = pedido.quantidade && pedido.quantidade > 1 ? ` x${pedido.quantidade}` : '';
  const cor = pedido.flores_cor?.trim() ? ` (${pedido.flores_cor.trim()})` : '';
  addLine(lines, `Item: ${pedido.produto}${qty}${cor}`);

  // Logística
  addBlankLine(lines);
  if (pedido.tipo_pedido === 'Entrega') {
    const endereco = getEnderecoCompleto(pedido);
    addLine(lines, 'Endereço:');
    addLine(lines, endereco);
    // Local: tipo + nome + detalhe do prédio (salta aos olhos do entregador)
    const tipoLabel = getTipoLocalLabel(pedido.tipo_local);
    const localLinha = [tipoLabel, pedido.nome_local?.trim()].filter(Boolean).join(': ');
    if (pedido.nome_local?.trim()) addLine(lines, `Local: ${localLinha}`);
    const detalhe = getDetalheLocal(pedido);
    if (detalhe) addLine(lines, detalhe);
    if (pedido.obs_entrega?.trim()) {
      addLine(lines, `Obs entrega: ${pedido.obs_entrega.trim()}`);
    }
    addLine(lines, `Mapa: ${buildMapsLinkFromAddress(endereco)}`);
  } else {
    addLine(lines, 'Retirada na loja');
  }

  // Cobrança (somente se tiver algo a cobrar)
  const precisaCobrar = pedido.status_pagamento === 'Pendente' || pedido.status_pagamento === 'Parcial';
  if (precisaCobrar && pedido.valor) {
    addBlankLine(lines);
    addLine(lines, `Pagamento: ${pedido.status_pagamento}`);
    addLine(lines, `Cobrar: ${formatBRL(pedido.valor)}`);
  }

  // Observações gerais (opcional)
  if (pedido.observacoes?.trim()) {
    addBlankLine(lines);
    addLine(lines, `Obs: ${pedido.observacoes.trim()}`);
  }

  return lines.join('\n');
}
