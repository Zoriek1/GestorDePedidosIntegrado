/**
 * Funil de leads por situação — taxonomia de grupos e mapeamento.
 *
 * Isolado da página (LeadsPage.tsx) para ser testável sem montar a UI inteira.
 * `status` é o estado canônico (vem do backend, governa CAPI/stats); `situacao`
 * é o subestado operacional do lead confirmado (`status='whatsapp_iniciado'`).
 */
import type { Lead } from '../../api/endpoints/leads';

// Subestados do lead confirmado, marcados pelo operador. Etiqueta de funil —
// não muda status nem dispara evento Meta.
export const SITUACAO_VALUES = ['aguardando_resposta', 'orcamento_enviado', 'sem_resposta'] as const;
export type Situacao = (typeof SITUACAO_VALUES)[number];

export const SITUACAO_LABELS: Record<Situacao, string> = {
  aguardando_resposta: 'Em conversa',
  orcamento_enviado: 'Orçamento enviado',
  sem_resposta: 'Sem resposta',
};

export const SITUACAO_CHIP_COLOR: Record<Situacao, 'info' | 'success' | 'warning'> = {
  aguardando_resposta: 'info',
  orcamento_enviado: 'success',
  sem_resposta: 'warning',
};

export type LeadGroup =
  | 'orcamento'
  | 'em_conversa'
  | 'a_confirmar'
  | 'sem_telefone'
  | 'sem_resposta'
  | 'fechados'
  | 'descartados';

/**
 * Funil priorizado (topo = onde prestar atenção). O lead confirmado
 * (`status='whatsapp_iniciado'`) ramifica pela `situacao`.
 */
export function getLeadGroup(lead: Pick<Lead, 'status' | 'situacao'>): LeadGroup {
  const { status, situacao } = lead;
  if (status === 'compra_realizada') return 'fechados';
  if (status === 'nao_entrou_em_contato' || status === 'descarte') return 'descartados';
  if (status === 'whatsapp_iniciado') {
    if (situacao === 'orcamento_enviado') return 'orcamento';
    if (situacao === 'sem_resposta') return 'sem_resposta';
    return 'em_conversa'; // aguardando_resposta ou null
  }
  if (status === 'lead_pendente') return 'a_confirmar'; // tem telefone, falta confirmar
  return 'sem_telefone'; // pendente_whatsapp / null — precisa capturar telefone
}

export const GROUP_ORDER: readonly LeadGroup[] = [
  'orcamento',
  'em_conversa',
  'a_confirmar',
  'sem_telefone',
  'sem_resposta',
  'fechados',
  'descartados',
] as const;

export const GROUP_LABELS: Record<LeadGroup, string> = {
  orcamento: 'Orçamento enviado',
  em_conversa: 'Em conversa',
  a_confirmar: 'A confirmar',
  sem_telefone: 'Sem telefone',
  sem_resposta: 'Sem resposta · reativar',
  fechados: 'Fechados',
  descartados: 'Descartados',
};
