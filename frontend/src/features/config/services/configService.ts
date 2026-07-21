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

export interface IntegrationSettingsConfig {
  store: { id: number; name: string; slug: string };
  configured: boolean;
  marketing_dispatch_enabled: boolean;
  meta_pixel_id: string | null;
  meta_capi_access_token: string | null;
  has_meta_capi_access_token: boolean;
  ga4_measurement_id: string | null;
  ga4_api_secret: string | null;
  has_ga4_api_secret: boolean;
  ga4_validate_only: boolean;
  google_datamanager_enabled: boolean;
  google_ads_customer_id: string | null;
  google_ads_conversion_action_id: string | null;
  utmify_enabled: boolean;
  utmify_api_token: string | null;
  has_utmify_api_token: boolean;
  utmify_platform: string | null;
  utmify_is_test: boolean;
  endereco_floricultura: string | null;
  loja_cep: string | null;
}

export type IntegrationSettingsPayload = Omit<
  IntegrationSettingsConfig,
  | 'store'
  | 'configured'
  | 'has_meta_capi_access_token'
  | 'has_ga4_api_secret'
  | 'has_utmify_api_token'
>;

export const IntegrationSettingsService = {
  get: async (
    apiRequest: ReturnType<typeof createApiRequest>,
  ): Promise<IntegrationSettingsConfig> => {
    const response = await apiRequest<{
      success: boolean;
      config: IntegrationSettingsConfig;
    }>('/config/integrations');
    if (!response.ok) throw new Error(response.message || 'Erro ao carregar integrações');
    return response.data.config;
  },

  update: async (
    apiRequest: ReturnType<typeof createApiRequest>,
    config: IntegrationSettingsPayload,
  ): Promise<IntegrationSettingsConfig> => {
    const response = await apiRequest<{
      success: boolean;
      config: IntegrationSettingsConfig;
    }>('/config/integrations', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
    if (!response.ok) throw new Error(response.message || 'Erro ao atualizar integrações');
    return response.data.config;
  },
};

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

// --- E6: per-field PATCH/validate/disconnect ---

export interface ValidationResult {
  ok: boolean;
  error: string | null;
  last_test_at: string | null;
}

export interface ChannelStatus {
  channel: string;
  ok: boolean | null;
  last_test_at: string | null;
  error: string | null;
}

export interface ValidationEntry {
  id: number;
  store_ref_id: number;
  channel: string;
  field: string | null;
  ok: boolean;
  error: string | null;
  validated_at: string;
}

export const IntegrationFieldService = {
  patchChannelField: async (
    apiRequest: ReturnType<typeof createApiRequest>,
    channel: string,
    field: string,
    value: unknown,
  ): Promise<IntegrationSettingsConfig> => {
    const response = await apiRequest<{
      success: boolean;
      config: IntegrationSettingsConfig;
      error?: string;
    }>(`/config/integrations/${channel}/${field}`, {
      method: 'PATCH',
      body: JSON.stringify({ value }),
    });
    if (!response.ok) throw new Error(response.error || response.message || 'Erro ao salvar campo');
    return response.data.config;
  },

  validateChannelField: async (
    apiRequest: ReturnType<typeof createApiRequest>,
    channel: string,
    field: string,
    value?: string,
  ): Promise<ValidationResult> => {
    const body: Record<string, unknown> = {};
    if (value !== undefined) body.value = value;
    const response = await apiRequest<{
      success: boolean;
      ok: boolean;
      error: string | null;
      last_test_at: string | null;
    }>(`/config/integrations/${channel}/${field}/validate`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(response.message || 'Erro ao validar campo');
    return {
      ok: response.data.ok,
      error: response.data.error,
      last_test_at: response.data.last_test_at,
    };
  },

  getChannelValidationStatus: async (
    apiRequest: ReturnType<typeof createApiRequest>,
    channel: string,
  ): Promise<ChannelStatus> => {
    const response = await apiRequest<{ success: boolean } & ChannelStatus>(
      `/config/integrations/${channel}/status`,
    );
    if (!response.ok) throw new Error(response.message || 'Erro ao verificar status');
    return response.data;
  },

  getValidationLogEntries: async (
    apiRequest: ReturnType<typeof createApiRequest>,
    channel?: string,
  ): Promise<ValidationEntry[]> => {
    const qs = channel ? `?channel=${encodeURIComponent(channel)}` : '';
    const response = await apiRequest<{
      success: boolean;
      entries: ValidationEntry[];
    }>(`/config/integrations/validation${qs}`);
    if (!response.ok) throw new Error(response.message || 'Erro ao listar validações');
    return response.data.entries;
  },

  disconnectOAuth: async (
    apiRequest: ReturnType<typeof createApiRequest>,
    provider: 'bling' | 'nuvemshop',
  ): Promise<void> => {
    const response = await apiRequest<{ success: boolean }>(
      `/integrations/${provider}/disconnect`,
      { method: 'DELETE' },
    );
    if (!response.ok) throw new Error(response.message || 'Erro ao desconectar');
  },
};
