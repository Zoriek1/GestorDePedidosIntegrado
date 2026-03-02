import type { Pedido } from '../../../api/endpoints/pedidos';
import type { PedidoFormData } from '../schemas';
import { formatCurrency, STATUS_PAGAMENTO, TIPOS_PEDIDO } from '../schemas';
<<<<<<< HEAD

export function orderToForm(pedido: Pedido): PedidoFormData {
  // DEBUG: Log do pedido recebido para diagnóstico
  console.log('=== DEBUG orderToForm ===');
  console.log('Pedido recebido:', pedido);
=======
import { createLogger } from '../../../lib/logger';

const log = createLogger('orderToForm');

export function orderToForm(pedido: Pedido): PedidoFormData {
  log.debug('Pedido recebido:', pedido);
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  
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

  // Garantir que fonte_pedido_id existe e é válido
  let fontePedidoId = pedido.fonte_pedido_id;
  if (!fontePedidoId || fontePedidoId === 0) {
<<<<<<< HEAD
    console.warn('Pedido sem fonte_pedido_id válida, usando 1 como fallback');
=======
    log.warn('Pedido sem fonte_pedido_id válida, usando 1 como fallback');
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
    fontePedidoId = 1; // Fallback para fonte padrão (Site)
  }

  // Validar tipo_pedido - deve ser 'Entrega' ou 'Retirada'
  let tipoPedido: 'Entrega' | 'Retirada' = 'Entrega';
  if (pedido.tipo_pedido && TIPOS_PEDIDO.includes(pedido.tipo_pedido as typeof TIPOS_PEDIDO[number])) {
    tipoPedido = pedido.tipo_pedido as 'Entrega' | 'Retirada';
  } else if (pedido.tipo_pedido) {
<<<<<<< HEAD
    console.warn('tipo_pedido inválido:', pedido.tipo_pedido, '- usando "Entrega" como fallback');
=======
    log.warn('tipo_pedido inválido:', pedido.tipo_pedido, '- usando "Entrega" como fallback');
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  }

  // Garantir que dia_entrega está no formato correto (YYYY-MM-DD)
  let diaEntrega = pedido.dia_entrega || '';
  if (diaEntrega && !/^\d{4}-\d{2}-\d{2}$/.test(diaEntrega)) {
<<<<<<< HEAD
    console.warn('dia_entrega em formato inválido:', diaEntrega);
=======
    log.warn('dia_entrega em formato inválido:', diaEntrega);
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
    // Tentar converter se estiver em outro formato
    try {
      const date = new Date(diaEntrega);
      if (!isNaN(date.getTime())) {
        diaEntrega = date.toISOString().split('T')[0];
<<<<<<< HEAD
        console.log('dia_entrega convertido para:', diaEntrega);
      }
    } catch {
      console.error('Falha ao converter dia_entrega');
=======
        log.debug('dia_entrega convertido para:', diaEntrega);
      }
    } catch {
      log.error('Falha ao converter dia_entrega');
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
    }
  }

  const formData: PedidoFormData = {
    cliente: pedido.cliente || '',
    cliente_modo: pedido.cliente_id ? 'busca' : 'novo',
    telefone_cliente: pedido.telefone_cliente || '',
    cliente_id: pedido.cliente_id,
    fonte_pedido_id: fontePedidoId,
    tipo_pedido: tipoPedido,
    destinatario: pedido.destinatario || '',
    dia_entrega: diaEntrega,
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

<<<<<<< HEAD
  console.log('FormData gerado:', formData);
=======
  log.debug('FormData gerado:', formData);
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  return formData;
}

