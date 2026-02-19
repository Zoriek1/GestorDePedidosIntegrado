/**
 * Helpers de agregação para a tela de Vendas
 */
import dayjs from 'dayjs';
import type { Pedido } from '../../../api/endpoints/pedidos';
import {
  calcularValorBrutoPedido,
  calcularValorEfetivoComFrete,
  calcularValorRecebidoPedido,
} from './valorEfetivo';

export interface SalesTotals {
  quantidade: number;
  totalVendasBruto: number;
  totalRecebido: number;
  totalEfetivo: number;
  ticketMedioEfetivo: number;
}

export interface ProductRankingItem {
  produto: string;
  total: number;
  quantidade: number;
}

export interface ChannelShareItem {
  canal: string;
  total: number;
  percentual: number;
}

export interface HourBucket {
  hora: number;
  label: string;
  quantidade: number;
  valor: number;
}

export interface DailyBucket {
  dateKey: string;
  label: string;
  valor: number;
  quantidade: number;
}

export function calcularTotais(vendas: Pedido[]): SalesTotals {
  const quantidade = vendas.length;
  const totalVendasBruto = vendas.reduce((sum, venda) => sum + calcularValorBrutoPedido(venda), 0);
  const totalRecebido = vendas.reduce((sum, venda) => sum + calcularValorRecebidoPedido(venda), 0);
  const totalEfetivo = vendas.reduce((sum, venda) => sum + calcularValorEfetivoComFrete(venda), 0);
  const ticketMedioEfetivo = quantidade > 0 ? totalEfetivo / quantidade : 0;

  return { quantidade, totalVendasBruto, totalRecebido, totalEfetivo, ticketMedioEfetivo };
}

export function agruparPorProduto(vendas: Pedido[]): ProductRankingItem[] {
  const mapa = new Map<string, ProductRankingItem>();

  vendas.forEach((venda) => {
    const produto = (venda.produto || 'Sem produto').trim();
    const item = mapa.get(produto) || { produto, total: 0, quantidade: 0 };
    item.total += calcularValorEfetivoComFrete(venda);
    item.quantidade += 1;
    mapa.set(produto, item);
  });

  return Array.from(mapa.values()).sort((a, b) => b.total - a.total);
}

export function agruparPorCanal(vendas: Pedido[]): ChannelShareItem[] {
  const mapa = new Map<string, number>();
  const total = vendas.reduce((sum, venda) => sum + calcularValorEfetivoComFrete(venda), 0);

  vendas.forEach((venda) => {
    const canalRaw = venda.fonte_pedido_nome || venda.fonte_pedido || 'Sem canal';
    const canal = canalRaw.trim();
    mapa.set(canal, (mapa.get(canal) || 0) + calcularValorEfetivoComFrete(venda));
  });

  return Array.from(mapa.entries())
    .map(([canal, valor]) => ({
      canal,
      total: valor,
      percentual: total > 0 ? (valor / total) * 100 : 0,
    }))
    .sort((a, b) => b.total - a.total);
}

export function agruparPorHora(vendas: Pedido[], horaInicio = 8, horaFim = 22): HourBucket[] {
  const buckets: HourBucket[] = [];
  for (let h = horaInicio; h <= horaFim; h += 1) {
    buckets.push({ hora: h, label: `${String(h).padStart(2, '0')}h`, quantidade: 0, valor: 0 });
  }

  vendas.forEach((venda) => {
    if (!venda.created_at) return;
    const hora = dayjs(venda.created_at).hour();
    if (hora < horaInicio || hora > horaFim) return;
    const bucket = buckets[hora - horaInicio];
    if (!bucket) return;
    bucket.quantidade += 1;
    bucket.valor += calcularValorEfetivoComFrete(venda);
  });

  return buckets;
}

export function agruparPorDia(vendas: Pedido[], startDate: string, endDate: string): DailyBucket[] {
  const start = dayjs(startDate);
  const end = dayjs(endDate);
  const days: Record<string, DailyBucket> = {};

  let current = start;
  while (current.isBefore(end) || current.isSame(end, 'day')) {
    const dateKey = current.format('YYYY-MM-DD');
    days[dateKey] = {
      dateKey,
      label: current.format('DD/MM'),
      valor: 0,
      quantidade: 0,
    };
    current = current.add(1, 'day');
  }

  vendas.forEach((venda) => {
    const vendaDate = dayjs(venda.created_at || venda.dia_entrega);
    const dateKey = vendaDate.format('YYYY-MM-DD');
    if (!days[dateKey]) return;
    days[dateKey].valor += calcularValorBrutoPedido(venda);
    days[dateKey].quantidade += 1;
  });

  return Object.values(days);
}
