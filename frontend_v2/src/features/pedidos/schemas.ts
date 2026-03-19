/**
 * Schemas de validação Zod para Pedidos
 * Validação rigorosa com condicionais (ex: endereço obrigatório apenas para entrega)
 */

import { z } from 'zod';
import dayjs from 'dayjs';

// ============================================================================
// Constantes de Validação
// ============================================================================

export const FORMAS_PAGAMENTO = [
  'Pix',
  'Cartão de Crédito',
  'Cartão de Débito',
  'Dinheiro',
  'Transferência',
  'Boleto',
  'Outro',
] as const;

export const STATUS_PAGAMENTO = [
  'Pendente',
  'Pago',
  'Parcial',
] as const;

export const TIPOS_PEDIDO = [
  'Entrega',
  'Retirada',
] as const;

/** Regex para CEP no formato 99999-999 */
export const CEP_REGEX = /^\d{5}-\d{3}$/;

/** Regex para CEP com ou sem hífen */
export const CEP_DIGITS_REGEX = /^\d{8}$/;

// ============================================================================
// Schema Base do Pedido (Formulário)
// ============================================================================

/**
 * Schema do formulário de criação de pedido
 * Os campos de valor são strings formatadas (R$ 0,00) que serão transformados para float
 */
export const pedidoFormSchema = z.object({
  // Step 1 - Dados do Cliente
  cliente: z.string()
    .min(2, 'Nome do cliente deve ter pelo menos 2 caracteres')
    .max(100, 'Nome do cliente deve ter no máximo 100 caracteres'),

  /** Define se o fluxo é busca de cliente existente ou novo cadastro */
  cliente_modo: z.enum(['busca', 'novo']).default('novo'),
  
  telefone_cliente: z.string()
    .min(10, 'Telefone deve ter pelo menos 10 dígitos')
    .max(20, 'Telefone inválido')
    .refine(
      (val) => /^\(\d{2}\)\s?\d{4,5}-?\d{4}$/.test(val) || /^\d{10,11}$/.test(val.replace(/\D/g, '')),
      'Formato de telefone inválido'
    ),

  /** ID do cliente selecionado no autocomplete (opcional) */
  cliente_id: z.number().optional(),

  /** ID da fonte do pedido (opcional) */
  fonte_pedido_id: z.number().optional(),

  // Step 2 - Dados da Entrega
  tipo_pedido: z.enum(TIPOS_PEDIDO, {
    message: 'Selecione o tipo de pedido',
  }),

  destinatario: z.string()
    .min(2, 'Nome do destinatário deve ter pelo menos 2 caracteres')
    .max(100, 'Nome do destinatário deve ter no máximo 100 caracteres'),

  dia_entrega: z.string()
    .min(1, 'Data de entrega é obrigatória')
    .refine(
      (val) => {
        const date = dayjs(val);
        return date.isValid();
      },
      'Data inválida'
    )
    .refine(
      (val) => {
        const date = dayjs(val);
        const today = dayjs().startOf('day');
        return date.isSame(today) || date.isAfter(today);
      },
      'Data de entrega não pode ser no passado'
    ),

  horario: z.string()
    .min(1, 'Horário de entrega é obrigatório. Clique em "Selecionar Horário".')
    .refine(
      (val) => /^\d{2}:\d{2}(?: - \d{2}:\d{2})?$/.test(val),
      'Formato de horário inválido (use HH:MM ou HH:MM - HH:MM)'
    ),

  // Endereço (obrigatório se tipo_pedido === 'Entrega')
  cep: z.string()
    .optional()
    .refine(
      (val) => {
        if (!val || val.trim() === '') return true; // Opcional quando vazio
        return CEP_REGEX.test(val) || CEP_DIGITS_REGEX.test(val.replace(/\D/g, ''));
      },
      'CEP inválido. Use o formato 00000-000'
    ),

  rua: z.string().max(200).optional(),
  numero: z.string().max(20).optional(),
  quadra: z.string().max(50).optional(),
  lote: z.string().max(50).optional(),
  complemento: z.string().max(100).optional(), // Novo: será mapeado para observacoes
  bairro: z.string().max(100).optional(),
  cidade: z.string().max(100).optional(),
  endereco: z.string().max(500).optional(),
  obs_entrega: z.string().max(500).optional(),

  // Step 3 - Dados do Produto
  produto: z.string()
    .min(3, 'Descrição do produto deve ter pelo menos 3 caracteres')
    .max(500, 'Descrição do produto deve ter no máximo 500 caracteres'),

  flores_cor: z.string().max(200).optional(),

  mensagem: z.string().max(1000, 'Mensagem do cartão deve ter no máximo 1000 caracteres').optional(),

  valor: z.string()
    .min(1, 'Valor do produto é obrigatório')
    .refine(
      (val) => {
        const parsed = parseCurrencyToFloat(val);
        return parsed !== undefined && parsed >= 0;
      },
      'Valor inválido'
    ),

  /** Quantidade de produtos (padrão: 1) */
  quantidade: z.coerce
    .number()
    .int('Quantidade deve ser um número inteiro')
    .min(1, 'Quantidade deve ser pelo menos 1')
    .max(100, 'Quantidade máxima é 100')
    .default(1),

  // Step 4 - Pagamento
  taxa_entrega: z.string().optional(),

  pagamento: z.string().max(50).optional(),

  status_pagamento: z.enum(STATUS_PAGAMENTO).default('Pendente'),

  observacoes: z.string().max(1000).optional(),

  // Atribuição de anúncio (Meta Ads)
  origem_anuncio: z.boolean().default(false),
  fbclid: z.string().max(255).optional(),
  fbp: z.string().max(255).optional(),

}).superRefine((data, ctx) => {
  // fbclid obrigatório quando pedido vem de anúncio
  if (data.origem_anuncio && (!data.fbclid || data.fbclid.trim() === '')) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'fbclid é obrigatório para pedidos vindos de anúncio',
      path: ['fbclid'],
    });
  }
  // Validação condicional: cliente existente requer cliente_id
  if (data.cliente_modo === 'busca' && !data.cliente_id) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Selecione um cliente existente ou altere para novo cadastro',
      path: ['cliente'],
    });
  }

  // Para novo cliente, garantir que não ficou um cliente_id residual
  if (data.cliente_modo === 'novo' && data.cliente_id) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Limpe o cliente selecionado para cadastrar um novo',
      path: ['cliente_id'],
    });
  }

  // Validação condicional: endereço obrigatório se for entrega
  if (data.tipo_pedido === 'Entrega') {
    // CEP é recomendado para entregas
    if (!data.cep || data.cep.trim() === '') {
      // Não bloqueia, mas recomenda
    }

    // Pelo menos rua + número OU endereço completo deve estar preenchido
    const hasAddress = (data.rua && data.numero) || data.endereco;
    
    if (!hasAddress) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Endereço é obrigatório para entregas',
        path: ['endereco'],
      });
    }

    // Cidade é obrigatória para entrega
    if (!data.cidade && !data.endereco?.includes(',')) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Cidade é obrigatória para entregas',
        path: ['cidade'],
      });
    }
  }
});

// ============================================================================
// Tipos inferidos
// ============================================================================

/** Tipo do formulário de pedido (dados do form com strings formatadas) */
export type PedidoFormData = z.infer<typeof pedidoFormSchema>;

/** Valores padrão para o formulário */
export const pedidoFormDefaultValues: PedidoFormData = {
  cliente: '',
  cliente_modo: 'novo',
  telefone_cliente: '',
  cliente_id: undefined,
  fonte_pedido_id: undefined,
  tipo_pedido: 'Entrega',
  destinatario: '',
  dia_entrega: dayjs().format('YYYY-MM-DD'),
  horario: '',
  cep: '',
  rua: '',
  numero: '',
  quadra: '',
  lote: '',
  complemento: '',
  bairro: '',
  cidade: '',
  endereco: '',
  obs_entrega: '',
  produto: '',
  flores_cor: '',
  mensagem: '',
  valor: '',
  quantidade: 1,
  taxa_entrega: '',
  pagamento: '',
  status_pagamento: 'Pendente',
  observacoes: '',
  origem_anuncio: false,
  fbclid: '',
  fbp: '',
};

// ============================================================================
// Funções de Transformação
// ============================================================================

/**
 * Converte valor monetário formatado (R$ 1.234,56) para float (1234.56)
 */
export function parseCurrencyToFloat(value: string | undefined): number | undefined {
  if (!value) return undefined;

  // Remove prefixo R$ e espaços, mantém apenas dígitos, vírgula, ponto e hífen
  const cleaned = value.replace(/R\$\s*/g, '').trim().replace(/[^\d,.-]/g, '');

  // Se tem vírgula, tratar como formato BR (1.000,00)
  if (cleaned.includes(',')) {
    // Remove pontos (separadores de milhar) e substitui vírgula por ponto
    const normalized = cleaned.replace(/\./g, '').replace(',', '.');
    const parsed = parseFloat(normalized);
    return Number.isNaN(parsed) ? undefined : parsed;
  }

  // Se não tem vírgula, pode ser número puro ou formato incorreto
  // Remove pontos e trata como número inteiro
  const normalized = cleaned.replace(/\./g, '');
  const parsed = parseFloat(normalized);
  return Number.isNaN(parsed) ? undefined : parsed;
}

/**
 * Formata float para string monetária (R$ 1.234,56)
 */
export function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return '';
  
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
}

/**
 * Remove máscara do telefone, deixando apenas dígitos
 */
export function parsePhoneToDigits(phone: string): string {
  return phone.replace(/\D/g, '');
}

/**
 * Aplica máscara de CEP (99999-999)
 */
export function applyCepMask(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 8);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

/**
 * Remove máscara do CEP, deixando apenas dígitos
 */
export function parseCepToDigits(cep: string): string {
  return cep.replace(/\D/g, '');
}

/**
 * Transforma dados do formulário para o payload da API
 * Inclui merge de complemento em observacoes
 */
export function transformFormToApiPayload(formData: PedidoFormData): Record<string, unknown> {
  // Monta o endereço completo se não estiver preenchido
  let enderecoCompleto = formData.endereco;
  if (!enderecoCompleto && formData.rua) {
    const parts = [
      formData.rua,
      formData.numero ? `nº ${formData.numero}` : null,
      formData.quadra ? `Qd ${formData.quadra}` : null,
      formData.lote ? `Lt ${formData.lote}` : null,
      formData.complemento ? formData.complemento : null,
      formData.bairro,
      formData.cidade,
    ].filter(Boolean);
    enderecoCompleto = parts.join(', ');
  }

  // Merge complemento em observacoes
  const observacoesParts: string[] = [];
  if (formData.observacoes?.trim()) {
    observacoesParts.push(formData.observacoes.trim());
  }
  if (formData.complemento?.trim()) {
    observacoesParts.push(`Complemento: ${formData.complemento.trim()}`);
  }
  const observacoesFinal = observacoesParts.length > 0 
    ? observacoesParts.join('\n') 
    : undefined;

  return {
    cliente: formData.cliente.trim(),
    telefone_cliente: parsePhoneToDigits(formData.telefone_cliente.trim()),
    cliente_id: formData.cliente_id || undefined,
    tipo_pedido: formData.tipo_pedido,
    destinatario: formData.destinatario.trim(),
    dia_entrega: formData.dia_entrega, // Already in YYYY-MM-DD format
    horario: formData.horario.trim(),
    cep: formData.cep?.trim() || undefined,
    rua: formData.rua?.trim() || undefined,
    numero: formData.numero?.trim() || undefined,
    bairro: formData.bairro?.trim() || undefined,
    cidade: formData.cidade?.trim() || undefined,
    endereco: enderecoCompleto?.trim() || undefined,
    obs_entrega: formData.obs_entrega?.trim() || undefined,
    produto: formData.produto.trim(),
    flores_cor: formData.flores_cor?.trim() || undefined,
    mensagem: formData.mensagem?.trim() || undefined,
    // enviar valor como string numérica (ex: "90.00") ou undefined
    valor: (() => {
      const parsed = parseCurrencyToFloat(formData.valor);
      return parsed !== undefined ? parsed.toFixed(2) : undefined;
    })(),
    taxa_entrega: parseCurrencyToFloat(formData.taxa_entrega),
    pagamento: formData.pagamento?.trim() || undefined,
    status_pagamento: formData.status_pagamento || 'Pendente',
    observacoes: observacoesFinal,
    quantidade: formData.quantidade ?? 1,
    fonte_pedido_id: formData.fonte_pedido_id || undefined,
    fbc: formData.fbclid?.trim()
      ? `fb.1.${Date.now()}.${formData.fbclid.trim()}`
      : undefined,
    fbp: formData.fbp?.trim() || undefined,
  };
}

// ============================================================================
// Validação por Step (para validação parcial)
// ============================================================================

/** Schema parcial para Step 1 - Cliente */
export const step1Schema = z.object({
  cliente: pedidoFormSchema.shape.cliente,
  cliente_modo: pedidoFormSchema.shape.cliente_modo,
  telefone_cliente: pedidoFormSchema.shape.telefone_cliente,
  cliente_id: pedidoFormSchema.shape.cliente_id,
  fonte_pedido_id: pedidoFormSchema.shape.fonte_pedido_id,
  origem_anuncio: pedidoFormSchema.shape.origem_anuncio,
  fbclid: pedidoFormSchema.shape.fbclid,
}).superRefine((data, ctx) => {
  if (data.origem_anuncio && (!data.fbclid || data.fbclid.trim() === '')) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'fbclid é obrigatório para pedidos vindos de anúncio',
      path: ['fbclid'],
    });
  }
});

/** Schema parcial para Step 2 - Entrega */
export const step2Schema = z.object({
  tipo_pedido: pedidoFormSchema.shape.tipo_pedido,
  destinatario: pedidoFormSchema.shape.destinatario,
  dia_entrega: pedidoFormSchema.shape.dia_entrega,
  horario: pedidoFormSchema.shape.horario,
  cep: pedidoFormSchema.shape.cep,
  rua: pedidoFormSchema.shape.rua,
  numero: pedidoFormSchema.shape.numero,
  quadra: pedidoFormSchema.shape.quadra,
  lote: pedidoFormSchema.shape.lote,
  complemento: pedidoFormSchema.shape.complemento,
  bairro: pedidoFormSchema.shape.bairro,
  cidade: pedidoFormSchema.shape.cidade,
  endereco: pedidoFormSchema.shape.endereco,
  obs_entrega: pedidoFormSchema.shape.obs_entrega,
}).superRefine((data, ctx) => {
  if (data.tipo_pedido === 'Entrega') {
    const hasAddress = (data.rua && data.numero) || data.endereco;
    if (!hasAddress) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Endereço é obrigatório para entregas',
        path: ['endereco'],
      });
    }
    if (!data.cidade && !data.endereco?.includes(',')) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Cidade é obrigatória para entregas',
        path: ['cidade'],
      });
    }
  }
});

/** Schema parcial para Step 3 - Produto */
export const step3Schema = pedidoFormSchema.pick({
  produto: true,
  flores_cor: true,
  mensagem: true,
  valor: true,
  quantidade: true,
});

/** Schema parcial para Step 4 - Pagamento */
export const step4Schema = pedidoFormSchema.pick({
  taxa_entrega: true,
  pagamento: true,
  status_pagamento: true,
  observacoes: true,
});
