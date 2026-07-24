import { z } from 'zod';

const pixelIdSchema = z
  .string()
  .regex(/^\d{6,30}$/, 'Pixel ID deve ter entre 6 e 30 dígitos')
  .or(z.literal(''));

const tokenSchema = (label: string, minLen: number) =>
  z.string().min(minLen, `${label} muito curto`).or(z.literal(''));

const gaIdSchema = z
  .string()
  .regex(/^G-[A-Z0-9]{4,12}$/i, 'Formato: G-XXXXXXXXXX')
  .or(z.literal(''));

const customerIdSchema = z
  .string()
  .regex(/^\d{3}-\d{3}-\d{4}$/, 'Formato: 123-456-7890')
  .or(z.literal(''));

const actionIdSchema = z
  .string()
  .regex(/^\d{5,15}$/, 'Deve ter entre 5 e 15 dígitos')
  .or(z.literal(''));

const cepSchema = z
  .string()
  .regex(/^\d{5}-?\d{3}$/, 'Formato: 00000-000')
  .or(z.literal(''));

const platformSchema = z.enum(['WhatsAppManual', 'Loja', 'Outro']).or(z.literal(''));

const fieldSchemas: Record<string, z.ZodTypeAny> = {
  meta_pixel_id: pixelIdSchema,
  meta_capi_access_token: tokenSchema('Access Token', 20),
  ga4_measurement_id: gaIdSchema,
  ga4_api_secret: tokenSchema('API Secret', 16),
  ga4_validate_only: z.boolean(),
  google_ads_customer_id: customerIdSchema,
  google_ads_conversion_action_id: actionIdSchema,
  google_datamanager_enabled: z.boolean(),
  utmify_api_token: tokenSchema('API Token', 16),
  utmify_platform: platformSchema,
  utmify_enabled: z.boolean(),
  utmify_is_test: z.boolean(),
  loja_cep: cepSchema,
  endereco_floricultura: z.string().max(255).or(z.literal('')),
  mercado_pago_access_token: tokenSchema('Access Token', 20),
  mercado_pago_public_key: z.string().min(10, 'Public Key muito curta').or(z.literal('')),
  mercado_pago_client_id: z.string().min(10, 'Client ID muito curto').or(z.literal('')),
  mercado_pago_client_secret: z.string().min(10, 'Client Secret muito curto').or(z.literal('')),
};

export function fieldSchema(fieldKey: string): z.ZodTypeAny {
  return fieldSchemas[fieldKey] ?? z.string();
}