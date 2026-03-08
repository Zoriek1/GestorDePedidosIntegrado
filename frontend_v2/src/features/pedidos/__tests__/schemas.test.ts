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
  });

  it('inclui lote no endereco quando preenchido', () => {
    const payload = transformFormToApiPayload(makeFormData({ lote: '12' }));
    expect(payload.endereco).toContain('Lt 12');
  });

  it('inclui quadra e lote juntos no endereco', () => {
    const payload = transformFormToApiPayload(makeFormData({ quadra: '5', lote: '12' }));
    expect(payload.endereco).toContain('Qd 5');
    expect(payload.endereco).toContain('Lt 12');
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
    rua: 'Rua das Flores',
    numero: '10',
    cidade: 'Goiânia',
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
