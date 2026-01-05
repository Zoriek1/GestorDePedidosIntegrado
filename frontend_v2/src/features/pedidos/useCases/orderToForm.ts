import type { Pedido } from '../../../api/endpoints/pedidos';
import type { PedidoFormData } from '../schemas';
import { formatCurrency, STATUS_PAGAMENTO } from '../schemas';

export function orderToForm(pedido: Pedido): PedidoFormData {
  // Converter valor de string para number se necessário
  let valorNum: number | undefined;
  if (pedido.valor !== undefined && pedido.valor !== null) {
    if (typeof pedido.valor === 'string') {
      // Remover formatação de moeda e converter para number
      const cleanValue = pedido.valor.replace(/[^\d,.-]/g, '').replace(',', '.');
      valorNum = parseFloat(cleanValue) || undefined;
    } else {
      valorNum = pedido.valor;
    }
  }

  // Validar status_pagamento
  let statusPagamento: 'Pendente' | 'Pago' | 'Parcial' | undefined = 'Pendente';
  if (pedido.status_pagamento && STATUS_PAGAMENTO.includes(pedido.status_pagamento as typeof STATUS_PAGAMENTO[number])) {
    statusPagamento = pedido.status_pagamento as 'Pendente' | 'Pago' | 'Parcial';
  }

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
    valor: formatCurrency(valorNum) || '',
    quantidade: pedido.quantidade ?? 1,
    taxa_entrega: pedido.taxa_entrega !== undefined && pedido.taxa_entrega !== null ? String(pedido.taxa_entrega) : '',
    pagamento: pedido.pagamento || '',
    status_pagamento: statusPagamento,
    observacoes: pedido.observacoes || '',
  };
}

