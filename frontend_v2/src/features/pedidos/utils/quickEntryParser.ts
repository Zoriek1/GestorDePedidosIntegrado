/**
 * Quick Entry Parser
 * Converte texto estruturado do cliente para dados de formulário de pedido.
 * Parser tolerante: extrai o que for possível e retorna warnings para campos problemáticos.
 */

import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import type { PedidoFormData } from '../schemas';

dayjs.extend(customParseFormat);

// ============================================================================
// Tipos
// ============================================================================

export interface QuickEntryResult {
  /** Dados do formulário extraídos (parcial) */
  formData: Partial<PedidoFormData>;
  /** Lista de avisos sobre campos não encontrados ou inválidos */
  warnings: string[];
  /** Lista de campos extraídos com sucesso */
  extractedFields: string[];
}

// ============================================================================
// Regex para extração de campos
// ============================================================================

const FIELD_PATTERNS: Record<string, RegExp[]> = {
  produto: [
    /nome\s*do\s*produto\s*:\s*(.+)/i,
    /produto\s*:\s*(.+)/i,
    /pedido\s*:\s*(.+)/i,
  ],
  cliente: [
    /quem\s*envi(?:ou|a)\s*:\s*(.+)/i,
    /cliente\s*:\s*(.+)/i,
    /remetente\s*:\s*(.+)/i,
    /enviado\s*por\s*:\s*(.+)/i,
  ],
  destinatario: [
    /destinat[aá]rio\s*:\s*(.+)/i,
    /para\s*:\s*(.+)/i,
    /entregar\s*para\s*:\s*(.+)/i,
    /recebedor\s*:\s*(.+)/i,
  ],
  anonimo: [
    /an[oô]nimo\s*:\s*(.+)/i,
    /esconder\s*remetente\s*:\s*(.+)/i,
  ],
  tipo_pedido: [
    /entrega\s*ou\s*retirada\s*:\s*(.+)/i,
    /tipo\s*:\s*(.+)/i,
    /modalidade\s*:\s*(.+)/i,
  ],
  horario: [
    /hor[aá]rio\s*(?:de\s*prefer[eê]ncia)?\s*:\s*(.+)/i,
    /hor[aá]rio\s*:\s*(.+)/i,
    /per[ií]odo\s*:\s*(.+)/i,
    /turno\s*:\s*(.+)/i,
  ],
  dia_entrega: [
    /dia\s*(?:de\s*entrega\s*\/?\s*retirada|da\s*entrega)?\s*:\s*(.+)/i,
    /data\s*(?:de\s*entrega)?\s*:\s*(.+)/i,
    /quando\s*:\s*(.+)/i,
  ],
  mensagem: [
    /carta\s*gratu[ií]ta\s*:\s*[""]?(.+?)[""]?\s*$/im,
    /mensagem\s*(?:do\s*cart[aã]o)?\s*:\s*[""]?(.+?)[""]?\s*$/im,
    /cart[aã]o\s*:\s*[""]?(.+?)[""]?\s*$/im,
  ],
  endereco: [
    /endere[çc]o\s*:\s*(.+)/i,
    /local\s*(?:de\s*entrega)?\s*:\s*(.+)/i,
  ],
  telefone: [
    /telefone\s*:\s*(.+)/i,
    /tel\s*:\s*(.+)/i,
    /whatsapp\s*:\s*(.+)/i,
    /contato\s*:\s*(.+)/i,
  ],
  valor: [
    /valor\s*:\s*(.+)/i,
    /pre[çc]o\s*:\s*(.+)/i,
    /total\s*:\s*(.+)/i,
    /r\$\s*([\d.,]+)/i,
  ],
  observacoes: [
    /observa[çc][oõ]es?\s*:\s*(.+)/i,
    /obs\s*:\s*(.+)/i,
    /nota\s*:\s*(.+)/i,
  ],
};

// ============================================================================
// Funções de Parsing Individuais
// ============================================================================

/**
 * Extrai um campo do texto usando múltiplos padrões regex
 */
function extractField(text: string, patterns: RegExp[]): string | null {
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match && match[1]) {
      return match[1].trim();
    }
  }
  return null;
}

/**
 * Normaliza data para formato YYYY-MM-DD
 * Suporta: "hoje", "amanhã", "25/12", "25/12/2024", "2024-12-25"
 */
function parseDate(dateStr: string): string | null {
  const normalized = dateStr.toLowerCase().trim();
  
  // "hoje"
  if (normalized === 'hoje' || normalized === 'today') {
    return dayjs().format('YYYY-MM-DD');
  }
  
  // "amanhã"
  if (normalized === 'amanhã' || normalized === 'amanha' || normalized === 'tomorrow') {
    return dayjs().add(1, 'day').format('YYYY-MM-DD');
  }
  
  // Dias da semana (próxima ocorrência)
  const diasSemana: Record<string, number> = {
    'domingo': 0, 'segunda': 1, 'terça': 2, 'terca': 2, 'quarta': 3,
    'quinta': 4, 'sexta': 5, 'sábado': 6, 'sabado': 6
  };
  
  for (const [dia, num] of Object.entries(diasSemana)) {
    if (normalized.includes(dia)) {
      let targetDate = dayjs().day(num);
      if (targetDate.isBefore(dayjs(), 'day')) {
        targetDate = targetDate.add(7, 'day');
      }
      return targetDate.format('YYYY-MM-DD');
    }
  }
  
  // Formatos de data
  const formats = [
    'DD/MM/YYYY', 'DD-MM-YYYY', 'DD.MM.YYYY',
    'DD/MM/YY', 'DD-MM-YY', 'DD.MM.YY',
    'DD/MM', 'DD-MM', 'DD.MM',
    'YYYY-MM-DD',
  ];
  
  for (const format of formats) {
    const parsed = dayjs(normalized, format, true);
    if (parsed.isValid()) {
      // Se o formato não tem ano, usar o ano atual ou próximo
      if (!format.includes('YYYY') && !format.includes('YY')) {
        let result = parsed.year(dayjs().year());
        if (result.isBefore(dayjs(), 'day')) {
          result = result.add(1, 'year');
        }
        return result.format('YYYY-MM-DD');
      }
      return parsed.format('YYYY-MM-DD');
    }
  }
  
  return null;
}

/**
 * Normaliza tipo de pedido para 'Entrega' ou 'Retirada'
 */
function parseTipoPedido(value: string): 'Entrega' | 'Retirada' | null {
  const normalized = value.toLowerCase().trim();
  
  if (normalized.includes('entrega') || normalized === 'e' || normalized === 'delivery') {
    return 'Entrega';
  }
  
  if (normalized.includes('retirada') || normalized.includes('retira') || 
      normalized === 'r' || normalized === 'pickup' || normalized.includes('buscar')) {
    return 'Retirada';
  }
  
  return null;
}

/**
 * Verifica se o pedido é anônimo
 */
function parseAnonimo(value: string): boolean {
  const normalized = value.toLowerCase().trim();
  return ['sim', 's', 'yes', 'y', 'true', '1', 'anonimo', 'anônimo'].includes(normalized);
}

/**
 * Formata valor monetário para o formato esperado pelo formulário
 */
function parseValor(value: string): string | null {
  // Extrair apenas números e separadores
  const cleaned = value.replace(/[^\d,.\s]/g, '').trim();
  
  if (!cleaned) return null;
  
  // Converter para float
  let num: number;
  if (cleaned.includes(',')) {
    // Formato brasileiro (1.234,56)
    num = parseFloat(cleaned.replace(/\./g, '').replace(',', '.'));
  } else {
    num = parseFloat(cleaned);
  }
  
  if (isNaN(num)) return null;
  
  // Formatar como moeda BR
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(num);
}

/**
 * Extrai telefone e formata
 */
function parseTelefone(value: string): string | null {
  // Extrair apenas dígitos
  const digits = value.replace(/\D/g, '');
  
  // Deve ter entre 10 e 11 dígitos
  if (digits.length < 10 || digits.length > 11) {
    return null;
  }
  
  // Formatar como (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
  if (digits.length === 11) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
  } else {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  }
}

/**
 * Tenta extrair cor das flores a partir do nome do produto
 */
function extractCorFromProduto(produto: string): string | null {
  const cores = [
    'vermelh', 'branc', 'amarel', 'rosa', 'roxo', 'roxa', 'lilás', 'lilas',
    'laranja', 'azul', 'verde', 'preto', 'preta', 'dourad', 'prata',
    'champagne', 'champanhe', 'nude', 'coral', 'salmão', 'salmao',
    'vinho', 'bordô', 'bordo', 'marsala', 'terracota', 'mostarda',
    'colorid', 'mist', 'variado', 'sortid'
  ];
  
  const produtoLower = produto.toLowerCase();
  
  for (const cor of cores) {
    if (produtoLower.includes(cor)) {
      // Encontrar a palavra completa
      const regex = new RegExp(`\\b(${cor}\\w*)\\b`, 'i');
      const match = produto.match(regex);
      if (match) {
        // Capitalizar primeira letra
        return match[1].charAt(0).toUpperCase() + match[1].slice(1).toLowerCase();
      }
    }
  }
  
  return null;
}

/**
 * Tenta separar endereço em componentes
 */
function parseEndereco(endereco: string): { 
  endereco: string; 
  rua?: string; 
  numero?: string; 
  bairro?: string; 
  cidade?: string;
  cep?: string;
} {
  const result: ReturnType<typeof parseEndereco> = {
    endereco: endereco.trim(),
  };
  
  // Tentar extrair CEP
  const cepMatch = endereco.match(/(\d{5}[-.]?\d{3})/);
  if (cepMatch) {
    result.cep = cepMatch[1].replace('.', '-');
    if (!result.cep.includes('-')) {
      result.cep = result.cep.slice(0, 5) + '-' + result.cep.slice(5);
    }
  }
  
  // Tentar extrair número (ex: "nº 123" ou ", 123" ou "número 123")
  const numeroMatch = endereco.match(/(?:n[º°]?\s*|,\s*|número\s*)(\d+)/i);
  if (numeroMatch) {
    result.numero = numeroMatch[1];
  }
  
  // Tentar separar por vírgulas
  const partes = endereco.split(',').map(p => p.trim());
  
  if (partes.length >= 2) {
    // Primeira parte geralmente é a rua
    result.rua = partes[0].replace(/,?\s*n[º°]?\s*\d+/i, '').trim();
    
    // Última parte geralmente é cidade/estado
    const ultimaParte = partes[partes.length - 1];
    if (!ultimaParte.match(/\d{5}/)) { // Não é CEP
      result.cidade = ultimaParte.replace(/\s*-\s*\w{2}$/, '').trim(); // Remove estado (ex: "- SP")
    }
    
    // Penúltima parte pode ser bairro
    if (partes.length >= 3) {
      const penultima = partes[partes.length - 2];
      if (!penultima.match(/\d{5}/) && !penultima.match(/^\d+$/)) {
        result.bairro = penultima.trim();
      }
    }
  }
  
  return result;
}

// ============================================================================
// Parser formato Goomer (Catálogo / Goomer Delivery)
// ============================================================================

const GOOMER_MARKERS = [
  'goomer',
  'pedido goomer',
  'goomer delivery',
  'goomer.app',
  'planteumaflor.goomer.app',
];

function isGoomerFormat(text: string): boolean {
  const lower = text.toLowerCase();
  return GOOMER_MARKERS.some((m) => lower.includes(m));
}

/**
 * Extrai dados do formato Goomer Delivery (Catálogo).
 * Exemplo: "*1x Buquê de Girassóis R$ 165,00*", "*Pedido para retirada*", "*Nome*", "(64) 99265-1886", etc.
 */
function parseGoomerEntry(text: string): {
  formData: Partial<PedidoFormData>;
  warnings: string[];
  extractedFields: string[];
} {
  const formData: Partial<PedidoFormData> = {
    cliente_modo: 'novo',
    tipo_pedido: 'Retirada',
    status_pagamento: 'Pendente',
    quantidade: 1,
  };
  const warnings: string[] = [];
  const extractedFields: string[] = [];
  const norm = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  // Produto: primeira linha *Nx Nome do produto R$ X,XX*
  const produtoMatch = norm.match(/\*\s*\d+x\s+(.+?)\s+R\$\s*[\d.,]+\s*\*/);
  if (produtoMatch && produtoMatch[1]) {
    formData.produto = produtoMatch[1].trim();
    extractedFields.push('produto');
    const cor = extractCorFromProduto(formData.produto);
    if (cor) {
      formData.flores_cor = cor;
      extractedFields.push('flores_cor');
    }
  } else {
    warnings.push('Produto não encontrado no formato Goomer');
  }

  // Valor: *Total com desconto: R$ X,XX* ou *Total:* R$ X,XX
  const totalMatch =
    norm.match(/\*Total com desconto:\s*R\$\s*([\d.,]+)\s*\*/i) ||
    norm.match(/\*Total[^:*]*:\s*R\$\s*([\d.,]+)\s*\*/i);
  if (totalMatch && totalMatch[1]) {
    const parsed = parseValor(totalMatch[1]);
    if (parsed) {
      formData.valor = parsed;
      extractedFields.push('valor');
    }
  } else {
    warnings.push('Valor total não encontrado');
  }

  // Tipo: *Pedido para retirada* ou *Pedido para entrega*
  if (/\*Pedido para retirada\s*\*/i.test(norm)) {
    formData.tipo_pedido = 'Retirada';
    extractedFields.push('tipo_pedido');
  } else if (/\*Pedido para entrega\s*\*/i.test(norm)) {
    formData.tipo_pedido = 'Entrega';
    extractedFields.push('tipo_pedido');
  }

  // Cliente: linha *Nome* logo após "*Pedido para retirada*" ou "*Pedido para entrega*"
  const pedidoParaMatch = norm.match(
    /\*Pedido para (?:retirada|entrega)\s*\*[\s\n]+\*([^*\n]+)\*/
  );
  if (pedidoParaMatch && pedidoParaMatch[1]) {
    formData.cliente = pedidoParaMatch[1].trim();
    extractedFields.push('cliente');
  } else {
    warnings.push('Nome do cliente não encontrado');
  }

  // Telefone: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX após o nome
  const telMatch = norm.match(/\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}/);
  if (telMatch) {
    const parsed = parseTelefone(telMatch[0]);
    if (parsed) {
      formData.telefone_cliente = parsed;
      extractedFields.push('telefone_cliente');
    }
  } else {
    warnings.push('Telefone não encontrado');
  }

  // Destinatário e mensagem do cartão: _Obs: Nome: X ... Cartão: Y_ (pode ter quebra de linha)
  const obsBlock = norm.match(/_Obs:[\s\S]+?_/);
  if (obsBlock) {
    const block = obsBlock[0];
    const nomeMatch = block.match(/Nome:\s*([^\n_]+)/);
    if (nomeMatch && nomeMatch[1]) {
      formData.destinatario = nomeMatch[1].trim();
      extractedFields.push('destinatario');
    }
    const cartaoMatch = block.match(/Cartão:\s*([\s\S]+?)(?:_|$)/i);
    if (cartaoMatch && cartaoMatch[1]) {
      formData.mensagem = cartaoMatch[1].trim();
      extractedFields.push('mensagem');
    }
  }
  if (!formData.destinatario) {
    formData.destinatario = formData.cliente ?? '';
    if (formData.cliente) extractedFields.push('destinatario');
  }

  // Pagamento: *Pagamento:* Dinheiro / Pix / etc
  const pagMatch = norm.match(/\*Pagamento:\s*([^*\n]+)\*/i);
  if (pagMatch && pagMatch[1]) {
    formData.pagamento = pagMatch[1].trim();
    extractedFields.push('pagamento');
  }

  // Observações: Troco, Obs, etc.
  const obsParts: string[] = [];
  const trocoMatch = norm.match(/\*?Troco para:\s*R\$\s*[\d.,]+\s*\*?/i);
  if (trocoMatch) obsParts.push(trocoMatch[0].replace(/\*/g, '').trim());
  if (formData.pagamento) obsParts.push(`Pagamento: ${formData.pagamento}`);
  const obsItalic = norm.match(/_Obs:[\s\S]+?_/);
  if (obsItalic) obsParts.push(obsItalic[0].replace(/^_Obs:\s*|_$/g, '').trim());
  if (obsParts.length > 0) {
    formData.observacoes = obsParts.join('\n');
    extractedFields.push('observacoes');
  }

  // Goomer não traz data/hora de entrega no texto — usar hoje e faixa ampla para o usuário ajustar
  formData.dia_entrega = dayjs().format('YYYY-MM-DD');
  formData.horario = '08:00 - 18:00';
  extractedFields.push('dia_entrega', 'horario');
  warnings.push('Data/horário de entrega não vêm no pedido Goomer; confira e ajuste no wizard se precisar.');
  return { formData, warnings, extractedFields };
}

// ============================================================================
// Função Principal
// ============================================================================

/**
 * Parseia texto estruturado e extrai dados do pedido
 * Aceita formato WhatsApp (template com campos nomeados) ou formato Goomer (Catálogo).
 * @param text Texto colado pelo usuário
 * @param fontePedidoId ID da fonte do pedido (obrigatório)
 * @returns Resultado com formData parcial, warnings e campos extraídos
 */
export function parseQuickEntry(text: string, fontePedidoId: number): QuickEntryResult {
  const formData: Partial<PedidoFormData> = {
    fonte_pedido_id: fontePedidoId,
    cliente_modo: 'novo',
    tipo_pedido: 'Entrega', // Default
    status_pagamento: 'Pendente',
    quantidade: 1,
  };
  const warnings: string[] = [];
  const extractedFields: string[] = [];
  
  // Normalizar quebras de linha
  const normalizedText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  // Formato Goomer (Catálogo) tem estrutura diferente
  if (isGoomerFormat(normalizedText)) {
    const goomer = parseGoomerEntry(normalizedText);
    Object.assign(formData, goomer.formData);
    formData.fonte_pedido_id = fontePedidoId;
    return {
      formData,
      warnings: goomer.warnings,
      extractedFields: goomer.extractedFields,
    };
  }
  
  // ===== Formato WhatsApp (campos nomeados) =====
  // ===== Extrair Produto =====
  const produto = extractField(normalizedText, FIELD_PATTERNS.produto);
  if (produto) {
    formData.produto = produto;
    extractedFields.push('produto');
    
    // Tentar extrair cor das flores
    const cor = extractCorFromProduto(produto);
    if (cor) {
      formData.flores_cor = cor;
      extractedFields.push('flores_cor');
    }
  } else {
    warnings.push('Produto não encontrado');
  }
  
  // ===== Extrair Cliente =====
  const cliente = extractField(normalizedText, FIELD_PATTERNS.cliente);
  if (cliente) {
    formData.cliente = cliente;
    extractedFields.push('cliente');
  } else {
    warnings.push('Cliente (quem enviou) não encontrado');
  }
  
  // ===== Extrair Destinatário =====
  const destinatario = extractField(normalizedText, FIELD_PATTERNS.destinatario);
  if (destinatario) {
    formData.destinatario = destinatario;
    extractedFields.push('destinatario');
  } else {
    warnings.push('Destinatário não encontrado');
  }
  
  // ===== Verificar Anônimo =====
  const anonimo = extractField(normalizedText, FIELD_PATTERNS.anonimo);
  if (anonimo && parseAnonimo(anonimo)) {
    // Se anônimo, limpar nome do cliente
    formData.cliente = 'Anônimo';
    extractedFields.push('anonimo');
  }
  
  // ===== Extrair Tipo de Pedido =====
  const tipoPedido = extractField(normalizedText, FIELD_PATTERNS.tipo_pedido);
  if (tipoPedido) {
    const parsed = parseTipoPedido(tipoPedido);
    if (parsed) {
      formData.tipo_pedido = parsed;
      extractedFields.push('tipo_pedido');
    } else {
      warnings.push(`Tipo de pedido "${tipoPedido}" não reconhecido (usando "Entrega")`);
    }
  } else {
    // Tentar inferir do texto
    if (normalizedText.toLowerCase().includes('retirada') || 
        normalizedText.toLowerCase().includes('buscar') ||
        normalizedText.toLowerCase().includes('pegar')) {
      formData.tipo_pedido = 'Retirada';
      extractedFields.push('tipo_pedido');
    }
  }
  
  // ===== Extrair Horário =====
  const horario = extractField(normalizedText, FIELD_PATTERNS.horario);
  if (horario) {
    formData.horario = horario;
    extractedFields.push('horario');
  } else {
    warnings.push('Horário não encontrado');
  }
  
  // ===== Extrair Data de Entrega =====
  const diaEntrega = extractField(normalizedText, FIELD_PATTERNS.dia_entrega);
  if (diaEntrega) {
    const parsed = parseDate(diaEntrega);
    if (parsed) {
      formData.dia_entrega = parsed;
      extractedFields.push('dia_entrega');
    } else {
      warnings.push(`Data "${diaEntrega}" não reconhecida`);
    }
  } else {
    warnings.push('Data de entrega não encontrada');
  }
  
  // ===== Extrair Mensagem do Cartão =====
  const mensagem = extractField(normalizedText, FIELD_PATTERNS.mensagem);
  if (mensagem) {
    // Remover aspas extras
    formData.mensagem = mensagem.replace(/^[""]|[""]$/g, '').trim();
    extractedFields.push('mensagem');
  }
  
  // ===== Extrair Endereço =====
  const enderecoRaw = extractField(normalizedText, FIELD_PATTERNS.endereco);
  if (enderecoRaw && enderecoRaw.trim() && formData.tipo_pedido === 'Entrega') {
    const enderecoData = parseEndereco(enderecoRaw);
    formData.endereco = enderecoData.endereco;
    extractedFields.push('endereco');
    
    if (enderecoData.rua) {
      formData.rua = enderecoData.rua;
    }
    if (enderecoData.numero) {
      formData.numero = enderecoData.numero;
    }
    if (enderecoData.bairro) {
      formData.bairro = enderecoData.bairro;
    }
    if (enderecoData.cidade) {
      formData.cidade = enderecoData.cidade;
    }
    if (enderecoData.cep) {
      formData.cep = enderecoData.cep;
    }
  } else if (formData.tipo_pedido === 'Entrega') {
    warnings.push('Endereço não encontrado (obrigatório para entrega)');
  }
  
  // ===== Extrair Telefone =====
  const telefone = extractField(normalizedText, FIELD_PATTERNS.telefone);
  if (telefone) {
    const parsed = parseTelefone(telefone);
    if (parsed) {
      formData.telefone_cliente = parsed;
      extractedFields.push('telefone_cliente');
    } else {
      warnings.push(`Telefone "${telefone}" em formato inválido`);
    }
  } else {
    warnings.push('Telefone não encontrado');
  }
  
  // ===== Extrair Valor =====
  const valor = extractField(normalizedText, FIELD_PATTERNS.valor);
  if (valor) {
    const parsed = parseValor(valor);
    if (parsed) {
      formData.valor = parsed;
      extractedFields.push('valor');
    } else {
      warnings.push(`Valor "${valor}" não reconhecido`);
    }
  }
  
  // ===== Extrair Observações =====
  const observacoes = extractField(normalizedText, FIELD_PATTERNS.observacoes);
  if (observacoes) {
    formData.observacoes = observacoes;
    extractedFields.push('observacoes');
  }
  
  console.log('=== Quick Entry Parse Result ===');
  console.log('Form Data:', formData);
  console.log('Extracted Fields:', extractedFields);
  console.log('Warnings:', warnings);
  
  return {
    formData,
    warnings,
    extractedFields,
  };
}

/**
 * Template de texto para enviar aos clientes
 */
export const QUICK_ENTRY_TEMPLATE = `Preencha aqui as informações que precisamos para entregar seu pedido:

Nome do Produto:

Quem enviou:
Destinatario:
Anonimo:

Entrega ou retirada: 

Horario de preferência:
Dia de Entrega / Retirada:

Carta gratuita: ""

Endereço:

em caso de não ser entrega, deixe o campo de endereço em branco 😁`;
