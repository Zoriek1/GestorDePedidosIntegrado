import { createApiRequest } from '../../../api/http';

export interface TaxaEntregaFaixa {
  de_km?: number;
  ate_km?: number | null;
  taxa: number;
  descricao?: string;
}

export interface TaxaEntregaConfig {
  tipo: 'faixas' | 'por_km';
  faixas?: TaxaEntregaFaixa[];
  valor_por_km?: number;
  taxa_base?: number;
  taxa_minima?: number;
  taxa_maxima?: number;
}

export const ConfigService = {
  getTaxaEntrega: async (apiRequest: ReturnType<typeof createApiRequest>): Promise<TaxaEntregaConfig> => {
    const response = await apiRequest<{ success: boolean; config: TaxaEntregaConfig }>('/config/taxa-entrega');
    if (!response.ok) {
        throw new Error(response.message || 'Erro ao carregar configurações');
    }
    return response.data.config;
  },
  
  updateTaxaEntrega: async (apiRequest: ReturnType<typeof createApiRequest>, config: TaxaEntregaConfig): Promise<void> => {
    const response = await apiRequest<{ success: boolean }>('/config/taxa-entrega', {
        method: 'POST',
        body: JSON.stringify(config)
    });
    if (!response.ok) {
        throw new Error(response.message || 'Erro ao atualizar configurações');
    }
  },

  getTaxaCartao: async (apiRequest: ReturnType<typeof createApiRequest>): Promise<TaxaCartaoConfig> => {
    const response = await apiRequest<{ success: boolean; config: TaxaCartaoConfig }>('/config/taxa-cartao');
    if (!response.ok) {
      throw new Error(response.message || 'Erro ao carregar taxas de cartão');
    }
    return response.data.config;
  },

  updateTaxaCartao: async (apiRequest: ReturnType<typeof createApiRequest>, config: TaxaCartaoConfig): Promise<void> => {
    const response = await apiRequest<{ success: boolean }>('/config/taxa-cartao', {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      throw new Error(response.message || 'Erro ao atualizar taxas de cartão');
    }
  },
};

export interface TaxaCartaoCreditoFaixa {
  parcelas: number;
  taxa_pct: number;
}

export interface TaxaCartaoConfig {
  debito_pct: number;
  credito: TaxaCartaoCreditoFaixa[];
}

/**
 * Calcula a taxa do adquirente (R$) para uma forma de pagamento.
 * Espelha a lógica do backend em services/taxa_cartao.py.
 */
export function calcularTaxaCartao(
  config: TaxaCartaoConfig | undefined,
  formaPagamento: string | undefined | null,
  parcelas: number | undefined | null,
  valor: number,
): number {
  if (!config || !formaPagamento || !valor || valor <= 0) return 0;
  const forma = formaPagamento.trim();
  if (forma === 'Cartão de Débito') {
    return Number(((valor * (config.debito_pct ?? 0)) / 100).toFixed(2));
  }
  if (forma === 'Cartão de Crédito') {
    const faixas = [...(config.credito ?? [])].sort((a, b) => a.parcelas - b.parcelas);
    if (!faixas.length) return 0;
    const n = Math.max(1, Number(parcelas || 1));
    const faixa = faixas.find((f) => f.parcelas === n) ?? faixas[faixas.length - 1];
    return Number(((valor * (faixa.taxa_pct ?? 0)) / 100).toFixed(2));
  }
  return 0;
}
