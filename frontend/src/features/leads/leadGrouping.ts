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

/**
 * Ações operacionais que a linha do lead expõe, por estado canônico (`status`).
 *
 * Fonte única que espelha `ALLOWED_STATUS_TRANSITIONS` do backend
 * (routes/leads.py): cada estado só oferece os controles/transições válidos.
 * `LeadActions` lê este mapa em vez de ternários espalhados pelos dois renderers.
 *
 * Travas (espelho do backend, sem regra nova):
 *  - `whatsapp_iniciado` é terminal manual → sem `disqualify`/compra (compra chega
 *    pelo fluxo de pedido). Expõe só o segmented de `situacao`.
 *  - `situacao` é valor único → segmented control (o followup mora dentro dele).
 *  - `descarte`/`nao_entrou_em_contato` não têm ação rápida na linha; a reabertura
 *    acontece pela captura de telefone (chip de status / bulk), inalterada.
 *
 * A chamada de WhatsApp (depende de ter telefone, não de status) e o botão de
 * ver/criar pedido ficam FORA do mapa — `LeadActions` os renderiza sempre.
 */
export type LeadAction =
  | 'capture_phone' // pendente sem telefone: botão de captura inline
  | 'mark_no_contact' // marcar "não entrou em contato"
  | 'confirm' // confirmar lead (dispara CAPI Lead)
  | 'disqualify' // descartar lead
  | 'situacao' // segmented de situação (lead confirmado)
  | 'view_order'; // ver o pedido vinculado (compra realizada)

export const ACTIONS_BY_STATUS: Record<string, LeadAction[]> = {
  pendente_whatsapp: ['capture_phone', 'mark_no_contact'],
  lead_pendente: ['confirm', 'disqualify'],
  whatsapp_iniciado: ['situacao'],
  compra_realizada: ['view_order'],
  descarte: [],
  nao_entrou_em_contato: [],
};

/** Ações válidas para um status (lista vazia para status nulo/desconhecido). */
export function getLeadActions(status: string | null | undefined): LeadAction[] {
  return ACTIONS_BY_STATUS[status ?? ''] ?? [];
}

/**
 * Estados pré-confirmação onde capturar o telefone (manualmente) faz sentido e
 * destrava o lead. Espelha `canEditLeadPhone` / `_apply_lead_phone_update` do backend.
 */
const PHONE_CAPTURABLE_STATUSES = new Set<string>([
  'pendente_whatsapp',
  'lead_pendente',
  'nao_entrou_em_contato',
]);

/**
 * Ações REAIS da linha considerando o telefone — não só o status.
 *
 * O backend exige telefone para `confirm`/`disqualify` (STATUSES_REQUIRING_PHONE
 * em routes/leads.py → 422 `telefone_obrigatorio`). Um lead sem telefone que só
 * expõe esses botões vira um beco sem saída: clicar dá erro e não há como avançar.
 * É exatamente o "limbo" do `lead_pendente` sem número (promovido pelo webhook do
 * WhatsApp, que não captura o telefone por causa do @lid).
 *
 * Regra: sem telefone, escondemos `confirm`/`disqualify` e oferecemos
 * `capture_phone` para os estados pré-confirmação — capturar o número promove o
 * lead e reabilita as ações normais.
 */
export function getEffectiveLeadActions(
  lead: Pick<Lead, 'status' | 'phone'>,
): LeadAction[] {
  const base = getLeadActions(lead.status);
  const hasPhone = !!lead.phone && lead.phone.trim() !== '';
  if (hasPhone) return base;

  const withoutPhoneGated = base.filter(
    (a) => a !== 'confirm' && a !== 'disqualify',
  );
  if (
    PHONE_CAPTURABLE_STATUSES.has(lead.status ?? '') &&
    !withoutPhoneGated.includes('capture_phone')
  ) {
    return ['capture_phone', ...withoutPhoneGated];
  }
  return withoutPhoneGated;
}

/** Telefone BR (com DDD) → URL `wa.me`, ou `null` se inválido (<10 dígitos). */
export function buildWhatsAppUrl(phone: string): string | null {
  const digits = phone.replace(/\D/g, '');
  if (digits.length < 10) return null;
  const full = digits.length <= 11 ? `55${digits}` : digits;
  return `https://wa.me/${full}`;
}
