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
};
