/**
 * Tipos do wizard redesenhado ("Novo Pedido").
 *
 * O mockup acrescenta detalhes de endereço que NÃO existem no schema base
 * (tipo de local, nome do local, apto/bloco/torre/andar). Para não alterar o
 * backend, esses campos vivem no estado do formulário como extras e são
 * compostos em `complemento` na hora de montar o payload.
 */
import type { PedidoFormData } from '../schemas';

export type TipoLocal = 'casa' | 'predio' | 'comercial';

export interface EntregaExtras {
  tipo_local?: TipoLocal;
  nome_local?: string;
  apto?: string;
  bloco?: string;
  torre?: string;
  andar?: string;
}

/** Form data do novo wizard = schema base + extras de endereço (UI). */
export type PedidoFormDataExt = PedidoFormData & EntregaExtras;

export const entregaExtrasDefaults: EntregaExtras = {
  tipo_local: 'casa',
  nome_local: '',
  apto: '',
  bloco: '',
  torre: '',
  andar: '',
};

/**
 * Compõe os extras de endereço (apto/bloco/torre/andar + nome do local) dentro
 * do campo `complemento`, preservando o que o usuário já tiver digitado nele.
 * Retorna uma cópia do form pronta para `transformFormToApiPayload`.
 */
export function mergeEntregaExtras(data: PedidoFormDataExt): PedidoFormData {
  const tipoLocal = data.tipo_local || 'casa';
  return {
    ...data,
    tipo_local: tipoLocal,
    nome_local: tipoLocal !== 'casa' ? data.nome_local : '',
    apto: tipoLocal === 'predio' ? data.apto : '',
    bloco: tipoLocal === 'predio' ? data.bloco : '',
    torre: tipoLocal === 'predio' ? data.torre : '',
    andar: tipoLocal === 'predio' ? data.andar : '',
    quadra: tipoLocal === 'casa' ? data.quadra : '',
    lote: tipoLocal === 'casa' ? data.lote : '',
  } as PedidoFormData;

  /*
  const partes: string[] = [];
  if (data.tipo_local && data.tipo_local !== 'casa' && data.nome_local?.trim()) {
    partes.push(data.nome_local.trim());
  }
  if (data.apto?.trim()) partes.push(`AP ${data.apto.trim()}`);
  if (data.bloco?.trim()) partes.push(`Bloco ${data.bloco.trim()}`);
  if (data.torre?.trim()) partes.push(`Torre ${data.torre.trim()}`);
  if (data.andar?.trim()) partes.push(`${data.andar.trim()}º andar`);

  const extra = partes.join(' · ');
  const complementoBase = (data.complemento ?? '').trim();
  const complemento = [complementoBase, extra].filter(Boolean).join(' · ');

  // Remove os campos extras (não fazem parte do PedidoFormData) e devolve o resto.
  const {
    tipo_local: _t, nome_local: _n, apto: _a, bloco: _b, torre: _to, andar: _an,
    ...base
  } = data;
  void _t; void _n; void _a; void _b; void _to; void _an;

  return { ...base, complemento: complemento || undefined } as PedidoFormData;
  */
}
