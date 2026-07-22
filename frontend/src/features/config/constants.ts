export interface ChannelFieldDef {
  key: string;
  label: string;
  type: 'text' | 'password' | 'boolean' | 'select';
  options?: string[];
  placeholder?: string;
  required?: boolean;
}

export interface ChannelDef {
  id: string;
  label: string;
  icon: string;
  type: 'field' | 'oauth';
  fields?: ChannelFieldDef[];
  testable?: boolean;
}

export const INTEGRATION_CHANNELS: ChannelDef[] = [
  {
    id: 'meta_capi',
    label: 'Meta CAPI',
    icon: 'Facebook',
    type: 'field',
    testable: true,
    fields: [
      { key: 'meta_pixel_id', label: 'Pixel ID', type: 'text', placeholder: '1234567890123456', required: true },
      { key: 'meta_capi_access_token', label: 'Access Token', type: 'password', required: true },
    ],
  },
  {
    id: 'ga4',
    label: 'Google Analytics 4',
    icon: 'BarChart3',
    type: 'field',
    testable: false,
    fields: [
      { key: 'ga4_measurement_id', label: 'Measurement ID', type: 'text', placeholder: 'G-XXXXXXXXXX', required: true },
      { key: 'ga4_api_secret', label: 'API Secret', type: 'password', required: true },
      { key: 'ga4_validate_only', label: 'Somente validação', type: 'boolean' },
    ],
  },
  {
    id: 'google_ads',
    label: 'Google Ads',
    icon: 'Megaphone',
    type: 'field',
    testable: false,
    fields: [
      { key: 'google_ads_customer_id', label: 'Customer ID', type: 'text', placeholder: '123-456-7890', required: true },
      { key: 'google_ads_conversion_action_id', label: 'Conversion Action ID', type: 'text', placeholder: '12345678901', required: true },
      { key: 'google_datamanager_enabled', label: 'Data Manager ativo', type: 'boolean' },
    ],
  },
  {
    id: 'utmify',
    label: 'UTMify',
    icon: 'Link',
    type: 'field',
    testable: true,
    fields: [
      { key: 'utmify_api_token', label: 'API Token', type: 'password', required: true },
      { key: 'utmify_platform', label: 'Plataforma', type: 'select', options: ['WhatsAppManual', 'Loja', 'Outro'], required: true },
      { key: 'utmify_enabled', label: 'UTMify ativa', type: 'boolean' },
      { key: 'utmify_is_test', label: 'Ambiente de teste', type: 'boolean' },
    ],
  },
  {
    id: 'dados_operacionais',
    label: 'Dados Operacionais',
    icon: 'Building2',
    type: 'field',
    testable: true,
    fields: [
      { key: 'loja_cep', label: 'CEP da loja', type: 'text', placeholder: '00000-000', required: true },
      { key: 'endereco_floricultura', label: 'Endereço de origem', type: 'text' },
    ],
  },
  {
    id: 'nuvemshop',
    label: 'Nuvemshop',
    icon: 'ShoppingBag',
    type: 'oauth',
    testable: true,
  },
  {
    id: 'bling',
    label: 'Bling',
    icon: 'Package',
    type: 'oauth',
    testable: true,
  },
];