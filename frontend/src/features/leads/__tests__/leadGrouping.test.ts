import { describe, it, expect } from 'vitest';
import {
  getLeadGroup,
  GROUP_ORDER,
  ACTIONS_BY_STATUS,
  getLeadActions,
  type LeadGroup,
} from '../leadGrouping';

type Input = { status: string | null; situacao: string | null };

function group(status: string | null, situacao: string | null = null): LeadGroup {
  return getLeadGroup({ status, situacao } as Input);
}

describe('getLeadGroup', () => {
  it('confirmado com orcamento_enviado vai pro topo (orcamento)', () => {
    expect(group('whatsapp_iniciado', 'orcamento_enviado')).toBe('orcamento');
  });

  it('confirmado com sem_resposta vai pro pool de reativação', () => {
    expect(group('whatsapp_iniciado', 'sem_resposta')).toBe('sem_resposta');
  });

  it('confirmado em aguardando_resposta ou sem situação fica em conversa', () => {
    expect(group('whatsapp_iniciado', 'aguardando_resposta')).toBe('em_conversa');
    expect(group('whatsapp_iniciado', null)).toBe('em_conversa');
  });

  it('lead_pendente (tem telefone) vai pra A confirmar', () => {
    expect(group('lead_pendente')).toBe('a_confirmar');
  });

  it('pendente_whatsapp / null vão pra Sem telefone', () => {
    expect(group('pendente_whatsapp')).toBe('sem_telefone');
    expect(group(null)).toBe('sem_telefone');
  });

  it('compra_realizada vai pra Fechados, ignorando situacao', () => {
    expect(group('compra_realizada', 'orcamento_enviado')).toBe('fechados');
  });

  it('descarte e nao_entrou_em_contato vão pra Descartados', () => {
    expect(group('descarte')).toBe('descartados');
    expect(group('nao_entrou_em_contato')).toBe('descartados');
  });

  it('todo grupo retornado está em GROUP_ORDER', () => {
    const samples: Input[] = [
      { status: 'whatsapp_iniciado', situacao: 'orcamento_enviado' },
      { status: 'whatsapp_iniciado', situacao: 'sem_resposta' },
      { status: 'whatsapp_iniciado', situacao: null },
      { status: 'lead_pendente', situacao: null },
      { status: 'pendente_whatsapp', situacao: null },
      { status: 'compra_realizada', situacao: null },
      { status: 'descarte', situacao: null },
    ];
    for (const s of samples) {
      expect(GROUP_ORDER).toContain(getLeadGroup(s));
    }
  });
});

describe('ACTIONS_BY_STATUS / getLeadActions', () => {
  it('pendente_whatsapp oferece captura de telefone e "não contatou"', () => {
    expect(getLeadActions('pendente_whatsapp')).toEqual(['capture_phone', 'mark_no_contact']);
  });

  it('lead_pendente oferece confirmar e descartar', () => {
    expect(getLeadActions('lead_pendente')).toEqual(['confirm', 'disqualify']);
  });

  it('whatsapp_iniciado é terminal manual: só situação, sem descarte/compra', () => {
    const actions = getLeadActions('whatsapp_iniciado');
    expect(actions).toEqual(['situacao']);
    expect(actions).not.toContain('disqualify');
    expect(actions).not.toContain('confirm');
    // Não há ação de "compra" na linha — a compra chega pelo fluxo de pedido.
    expect(actions).not.toContain('view_order');
  });

  it('compra_realizada só expõe ver o pedido', () => {
    expect(getLeadActions('compra_realizada')).toEqual(['view_order']);
  });

  it('descarte / nao_entrou_em_contato não têm ação rápida na linha', () => {
    expect(getLeadActions('descarte')).toEqual([]);
    expect(getLeadActions('nao_entrou_em_contato')).toEqual([]);
  });

  it('status nulo ou desconhecido devolve lista vazia (sem crash)', () => {
    expect(getLeadActions(null)).toEqual([]);
    expect(getLeadActions(undefined)).toEqual([]);
    expect(getLeadActions('status_inexistente')).toEqual([]);
  });

  it('nenhum status oferece descartar um lead já confirmado/comprado', () => {
    for (const [status, actions] of Object.entries(ACTIONS_BY_STATUS)) {
      if (status === 'whatsapp_iniciado' || status === 'compra_realizada') {
        expect(actions).not.toContain('disqualify');
      }
    }
  });
});
