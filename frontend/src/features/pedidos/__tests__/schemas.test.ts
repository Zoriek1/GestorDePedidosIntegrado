/**
 * Testes para schemas.ts — foco em quadra e lote
 *
 * Cobre:
 *  - transformFormToApiPayload: quadra/lote incluídos no endereco
 *  - pedidoFormSchema: campos opcionais, limites de tamanho
 *  - pedidoFormDefaultValues: valores iniciais corretos
 *  - step2Schema: aceita quadra e lote
 */

import { describe, it, expect } from 'vitest';
import dayjs from 'dayjs';
import {
  transformFormToApiPayload,
  pedidoFormDefaultValues,
  pedidoFormSchema,
  step2Schema,
  isValidCpfCnpj,
  type PedidoFormData,
} from '../schemas';

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

/** Monta um PedidoFormData completo válido com overrides pontuais */
function makeFormData(overrides: Partial<PedidoFormData> = {}): PedidoFormData {
  return {
    ...pedidoFormDefaultValues,
    cliente: 'Maria Silva',
    telefone_cliente: '(62) 99999-9999',
    tipo_pedido: 'Entrega',
    destinatario: 'João',
    dia_entrega: dayjs().format('YYYY-MM-DD'),
    horario: '14:00',
    rua: 'Rua das Flores',
    numero: '10',
    cep: '74810-170',
    bairro: 'Jardim Goiás',
    cidade: 'Goiânia',
    produto: 'Buquê de rosas',
    valor: 'R$ 150,00',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// transformFormToApiPayload — quadra e lote no endereco
// ---------------------------------------------------------------------------

describe('transformFormToApiPayload — quadra e lote', () => {
  it('inclui quadra no endereco quando preenchida', () => {
    const payload = transformFormToApiPayload(makeFormData({ quadra: '5' }));
    expect(payload.endereco).toContain('Qd 5');
    expect(payload.quadra).toBe('5');
  });

  it('inclui lote no endereco quando preenchido', () => {
    const payload = transformFormToApiPayload(makeFormData({ lote: '12' }));
    expect(payload.endereco).toContain('Lt 12');
    expect(payload.lote).toBe('12');
  });

  it('inclui quadra e lote juntos no endereco', () => {
    const payload = transformFormToApiPayload(makeFormData({ quadra: '5', lote: '12' }));
    expect(payload.endereco).toContain('Qd 5');
    expect(payload.endereco).toContain('Lt 12');
    expect(payload.tipo_local).toBe('casa');
    expect(payload.quadra).toBe('5');
    expect(payload.lote).toBe('12');
  });

  it('omite quadra do endereco quando vazia', () => {
    const payload = transformFormToApiPayload(makeFormData({ quadra: '', lote: '12' }));
    expect(payload.endereco).not.toContain('Qd');
    expect(payload.endereco).toContain('Lt 12');
  });

  it('omite lote do endereco quando vazio', () => {
    const payload = transformFormToApiPayload(makeFormData({ quadra: '5', lote: '' }));
    expect(payload.endereco).toContain('Qd 5');
    expect(payload.endereco).not.toContain('Lt');
  });

  it('omite quadra e lote quando ambos vazios', () => {
    const payload = transformFormToApiPayload(makeFormData({ quadra: '', lote: '' }));
    expect(payload.endereco).not.toContain('Qd');
    expect(payload.endereco).not.toContain('Lt');
  });

  it('omite quadra e lote quando ambos undefined', () => {
    const payload = transformFormToApiPayload(makeFormData({ quadra: undefined, lote: undefined }));
    expect(payload.endereco).not.toContain('Qd');
    expect(payload.endereco).not.toContain('Lt');
  });

  it('posiciona quadra após número e antes do bairro', () => {
    const payload = transformFormToApiPayload(
      makeFormData({ numero: '10', quadra: '5', lote: '12', bairro: 'Jardim', cidade: 'Goiânia' }),
    );
    const endereco = payload.endereco as string;
    expect(endereco.indexOf('nº 10')).toBeLessThan(endereco.indexOf('Qd 5'));
    expect(endereco.indexOf('Qd 5')).toBeLessThan(endereco.indexOf('Jardim'));
  });

  it('posiciona lote após quadra e antes do bairro', () => {
    const payload = transformFormToApiPayload(
      makeFormData({ quadra: '5', lote: '12', bairro: 'Jardim', cidade: 'Goiânia' }),
    );
    const endereco = payload.endereco as string;
    expect(endereco.indexOf('Qd 5')).toBeLessThan(endereco.indexOf('Lt 12'));
    expect(endereco.indexOf('Lt 12')).toBeLessThan(endereco.indexOf('Jardim'));
  });

  it('produz endereco completo e correto com todos os componentes', () => {
    const payload = transformFormToApiPayload(
      makeFormData({
        rua: 'Rua das Flores',
        numero: '10',
        quadra: '5',
        lote: '12',
        bairro: 'Jardim Primavera',
        cidade: 'Goiânia',
        complemento: '',
        endereco: '',
      }),
    );
    expect(payload.endereco).toBe(
      'Rua das Flores, nº 10, Qd 5, Lt 12, Jardim Primavera, Goiânia',
    );
  });

  it('não usa endereco composto quando endereco manual já está preenchido', () => {
    const payload = transformFormToApiPayload(
      makeFormData({ endereco: 'Endereço manual', quadra: '5', lote: '12' }),
    );
    // Quando endereco já vem preenchido, não recompõe
    expect(payload.endereco).toBe('Endereço manual');
  });

  it('normaliza codigo_whatsapp para maiúsculo no payload', () => {
    const payload = transformFormToApiPayload(makeFormData({ codigo_whatsapp: ' a3f9b7k20k ' }));
    expect(payload.codigo_whatsapp).toBe('A3F9B7K20K');
  });

  it('omite quadra e lote para predio e envia detalhes do predio separados', () => {
    const payload = transformFormToApiPayload(
      makeFormData({
        tipo_local: 'predio',
        nome_local: 'Edificio Jardim',
        apto: '302',
        bloco: 'B',
        torre: '2',
        andar: '3',
        quadra: '5',
        lote: '12',
      }),
    );
    expect(payload.quadra).toBeUndefined();
    expect(payload.lote).toBeUndefined();
    expect(payload.nome_local).toBe('Edificio Jardim');
    expect(payload.apto).toBe('302');
    expect(payload.bloco).toBe('B');
    expect(payload.torre).toBe('2');
    expect(payload.andar).toBe('3');
    expect(payload.endereco).not.toContain('Qd 5');
    expect(payload.endereco).not.toContain('Lt 12');
    expect(payload.endereco).toContain('Edificio Jardim AP 302 -');
  });

  it('prefixa comercio ao gerar endereco composto automaticamente', () => {
    const payload = transformFormToApiPayload(
      makeFormData({
        tipo_local: 'comercial',
        nome_local: 'Loja Centro',
        endereco: '',
      }),
    );

    expect(payload.endereco).toContain('Loja Centro -');
  });
});

// ---------------------------------------------------------------------------
// pedidoFormSchema — validação de quadra e lote
// ---------------------------------------------------------------------------

describe('pedidoFormSchema — quadra e lote são opcionais', () => {
  it('aceita pedido sem quadra e lote', () => {
    const result = pedidoFormSchema.safeParse(makeFormData({ quadra: undefined, lote: undefined }));
    expect(result.success).toBe(true);
  });

  it('aceita pedido com quadra e lote preenchidos', () => {
    const result = pedidoFormSchema.safeParse(makeFormData({ quadra: '5', lote: '12' }));
    expect(result.success).toBe(true);
  });

  it('aceita quadra e lote como strings vazias', () => {
    const result = pedidoFormSchema.safeParse(makeFormData({ quadra: '', lote: '' }));
    expect(result.success).toBe(true);
  });

  it('rejeita quadra com mais de 50 caracteres', () => {
    const result = pedidoFormSchema.safeParse(makeFormData({ quadra: 'A'.repeat(51) }));
    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((i) => i.path[0]);
      expect(paths).toContain('quadra');
    }
  });

  it('rejeita lote com mais de 50 caracteres', () => {
    const result = pedidoFormSchema.safeParse(makeFormData({ lote: 'B'.repeat(51) }));
    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((i) => i.path[0]);
      expect(paths).toContain('lote');
    }
  });

  it('aceita quadra com exatamente 50 caracteres', () => {
    const result = pedidoFormSchema.safeParse(makeFormData({ quadra: 'X'.repeat(50) }));
    expect(result.success).toBe(true);
  });

  it('aceita lote com exatamente 50 caracteres', () => {
    const result = pedidoFormSchema.safeParse(makeFormData({ lote: 'Y'.repeat(50) }));
    expect(result.success).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// pedidoFormDefaultValues — quadra e lote inicializados
// ---------------------------------------------------------------------------

describe('pedidoFormDefaultValues', () => {
  it('define quadra como string vazia por padrão', () => {
    expect(pedidoFormDefaultValues.quadra).toBe('');
  });

  it('define lote como string vazia por padrão', () => {
    expect(pedidoFormDefaultValues.lote).toBe('');
  });
});

// ---------------------------------------------------------------------------
// step2Schema — quadra e lote incluídos no schema parcial
// ---------------------------------------------------------------------------

describe('step2Schema — aceita quadra e lote', () => {
  const baseStep2 = {
    tipo_pedido: 'Entrega' as const,
    destinatario: 'João',
    dia_entrega: dayjs().format('YYYY-MM-DD'),
    horario: '14:00',
    cep: '74810-170',
    rua: 'Rua das Flores',
    numero: '10',
    bairro: 'Jardim Goiás',
    cidade: 'Goiânia',
    uf: 'GO',
  };

  it('valida step 2 com quadra e lote preenchidos', () => {
    const result = step2Schema.safeParse({ ...baseStep2, quadra: '5', lote: '12' });
    expect(result.success).toBe(true);
  });

  it('valida step 2 sem quadra e lote (ambos opcionais)', () => {
    const result = step2Schema.safeParse(baseStep2);
    expect(result.success).toBe(true);
  });

  it('rejeita quadra acima de 50 caracteres no step 2', () => {
    const result = step2Schema.safeParse({ ...baseStep2, quadra: 'Q'.repeat(51) });
    expect(result.success).toBe(false);
  });

  it('rejeita lote acima de 50 caracteres no step 2', () => {
    const result = step2Schema.safeParse({ ...baseStep2, lote: 'L'.repeat(51) });
    expect(result.success).toBe(false);
  });

  it('valida step 2 com Retirada sem endereço (quadra/lote irrelevantes)', () => {
    const result = step2Schema.safeParse({
      tipo_pedido: 'Retirada' as const,
      destinatario: 'João',
      dia_entrega: dayjs().format('YYYY-MM-DD'),
      horario: '10:00',
      quadra: '99',
      lote: '88',
    });
    expect(result.success).toBe(true);
  });
});

describe('dados fiscais e UF', () => {
  it('aceita CPF, CNPJ e documento vazio', () => {
    expect(pedidoFormSchema.safeParse(makeFormData({ cpf_cnpj: '529.982.247-25' })).success).toBe(true);
    expect(pedidoFormSchema.safeParse(makeFormData({ cpf_cnpj: '04.252.011/0001-10' })).success).toBe(true);
    expect(pedidoFormSchema.safeParse(makeFormData({ cpf_cnpj: '' })).success).toBe(true);
    expect(isValidCpfCnpj('52998224725')).toBe(true);
  });

  it('rejeita CPF/CNPJ inválido quando preenchido', () => {
    const result = pedidoFormSchema.safeParse(makeFormData({ cpf_cnpj: '111.111.111-11' }));
    expect(result.success).toBe(false);
  });

  it('normaliza documento e UF no payload', () => {
    const payload = transformFormToApiPayload(
      makeFormData({ cpf_cnpj: '04.252.011/0001-10', uf: 'go' }),
    );
    expect(payload.cpf_cnpj).toBe('04252011000110');
    expect(payload.uf).toBe('GO');
  });

  it.each(['cep', 'rua', 'numero', 'bairro', 'cidade', 'uf'] as const)(
    'rejeita entrega sem %s',
    (field) => {
      const result = pedidoFormSchema.safeParse(makeFormData({ [field]: '' }));
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues.map((issue) => issue.path[0])).toContain(field);
      }
    },
  );

  it('aceita retirada sem endereço estruturado', () => {
    const result = pedidoFormSchema.safeParse(makeFormData({
      tipo_pedido: 'Retirada',
      cep: '', rua: '', numero: '', bairro: '', cidade: '', uf: '',
    }));
    expect(result.success).toBe(true);
  });
});
