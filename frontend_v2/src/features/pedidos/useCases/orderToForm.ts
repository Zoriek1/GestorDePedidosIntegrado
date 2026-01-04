import type { Pedido } from '../../../api/endpoints/pedidos';
import type { PedidoFormData } from '../schemas';
import { formatCurrency } from '../schemas';

export function orderToForm(pedido: Pedido): PedidoFormData {
  return {
    cliente: pedido.cliente || '',
    cliente_modo: pedido.cliente_id ? 'busca' : 'novo',
    telefone_cliente: pedido.telefone_cliente || '',
    cliente_id: pedido.cliente_id,
    fonte_pedido_id: pedido.fonte_pedido_id,
    tipo_pedido: pedido.tipo_pedido,
    destinatario: pedido.destinatario || '',
    dia_entrega: pedido.dia_entrega,
    horario: pedido.horario || '',
    cep: pedido.cep || '',
    rua: pedido.rua || '',
    numero: pedido.numero || '',
    complemento: '',
    bairro: pedido.bairro || '',
    cidade: pedido.cidade || '',
    endereco: pedido.endereco || '',
    obs_entrega: pedido.obs_entrega || '',
    produto: pedido.produto || '',
    flores_cor: pedido.flores_cor || '',
    mensagem: pedido.mensagem || '',
    valor: formatCurrency(pedido.valor as any) || '',
    quantidade: pedido.quantidade ?? 1,
    taxa_entrega: pedido.taxa_entrega !== undefined && pedido.taxa_entrega !== null ? String(pedido.taxa_entrega) : '',
    pagamento: pedido.pagamento || '',
    status_pagamento: (pedido.status_pagamento as any) || 'Pendente',
    observacoes: pedido.observacoes || '',
  };
}

