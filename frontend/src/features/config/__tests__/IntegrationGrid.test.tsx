import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { IntegrationCard } from '../components/IntegrationCard';
import { OAuthCard } from '../components/OAuthCard';
import { INTEGRATION_CHANNELS } from '../constants';
import { ConfirmProvider } from '../../../components/system/ConfirmProvider';

const mockConfig: any = {
  store: { id: 1, name: 'Teste', slug: 'default' },
  configured: true,
  has_meta_capi_access_token: true,
  meta_pixel_id: '1234567890',
  meta_capi_access_token: null,
  has_ga4_api_secret: false,
  ga4_measurement_id: '',
  ga4_api_secret: '',
  ga4_validate_only: false,
  google_datamanager_enabled: false,
  google_ads_customer_id: '',
  google_ads_conversion_action_id: '',
  has_utmify_api_token: false,
  utmify_api_token: '',
  utmify_platform: '',
  utmify_enabled: false,
  utmify_is_test: false,
  loja_cep: '',
  endereco_floricultura: '',
  marketing_dispatch_enabled: false,
};

function renderWithProviders(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ConfirmProvider>{ui}</ConfirmProvider>
    </QueryClientProvider>,
  );
}

// --- IntegrationCard ---

describe('IntegrationCard', () => {
  it('renders green chip when all required fields filled and status ok', () => {
    const channel = INTEGRATION_CHANNELS.find(c => c.id === 'meta_capi')!;
    const status = { channel: 'meta_capi', ok: true, last_test_at: '2026-01-01T00:00:00', error: null };
    render(
      <IntegrationCard channel={channel} config={mockConfig} status={status} onOpenModal={() => {}} />,
    );
    expect(screen.getByText('Validado')).toBeDefined();
  });

  it('renders yellow chip when saved but not validated', () => {
    const channel = INTEGRATION_CHANNELS.find(c => c.id === 'meta_capi')!;
    render(
      <IntegrationCard channel={channel} config={mockConfig} status={null} onOpenModal={() => {}} />,
    );
    expect(screen.getByText('Pendente')).toBeDefined();
  });

  it('renders gray chip when required fields are missing', () => {
    const emptyConfig = { ...mockConfig, meta_pixel_id: '', has_meta_capi_access_token: false };
    const channel = INTEGRATION_CHANNELS.find(c => c.id === 'meta_capi')!;
    render(
      <IntegrationCard channel={channel} config={emptyConfig} status={null} onOpenModal={() => {}} />,
    );
    expect(screen.getByText('Não configurado')).toBeDefined();
  });

  it('renders red chip when validation failed', () => {
    const channel = INTEGRATION_CHANNELS.find(c => c.id === 'meta_capi')!;
    const status = { channel: 'meta_capi', ok: false, last_test_at: '2026-01-01T00:00:00', error: 'Token inválido' };
    render(
      <IntegrationCard channel={channel} config={mockConfig} status={status} onOpenModal={() => {}} />,
    );
    expect(screen.getByText('Falhou')).toBeDefined();
  });
});

// --- OAuthCard ---

describe('OAuthCard', () => {
  it('shows Conectar when not connected', () => {
    renderWithProviders(
      <OAuthCard provider="nuvemshop" label="Nuvemshop" connected={false} onConnect={vi.fn()} onDisconnect={vi.fn()} />,
    );
    expect(screen.getByText('Conectar')).toBeDefined();
    expect(screen.getByText('Não conectado')).toBeDefined();
  });

  it('shows Reconectar and Desconectar when connected', () => {
    renderWithProviders(
      <OAuthCard provider="bling" label="Bling" connected={true} onConnect={vi.fn()} onDisconnect={vi.fn()} />,
    );
    expect(screen.getByText('Conectado')).toBeDefined();
    expect(screen.getByText('Reconectar')).toBeDefined();
    expect(screen.getByText('Desconectar')).toBeDefined();
  });
});

// --- IntegrationGrid (render smoke test) ---

// Mock API endpoints
vi.mock('../../../api/endpoints/nuvemshop', () => ({
  useNuvemshopConfig: () => ({ data: { connected: false } }),
  useNuvemshopInstall: () => ({ mutate: vi.fn() }),
}));

vi.mock('../../../api/endpoints/bling', () => ({
  useBlingStatus: () => ({ data: { connected: false } }),
  useBlingInstall: () => ({ mutate: vi.fn() }),
}));

vi.mock('../../../api/http', () => ({
  createApiRequest: () => vi.fn(),
}));

vi.mock('../../auth/authStore', () => ({
  useAuth: () => ({
    getAuthHeader: () => 'Bearer test',
    getUser: () => ({ store_slug: 'default', store_ref_id: 1, role: 'admin' }),
  }),
}));

vi.mock('../../../components/system/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../hooks/useConfig', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../hooks/useConfig')>();
  return {
    ...actual,
    useIntegrationSettings: () => ({
      config: mockConfig,
      isLoading: false,
      error: null,
    }),
    useOAuthDisconnect: () => ({ mutate: vi.fn() }),
  };
});

// Need to import after mocks
const { IntegrationGrid } = await import('../components/IntegrationGrid');

describe('IntegrationGrid', () => {
  it('renders all 7 channel cards', () => {
    renderWithProviders(
      <MemoryRouter>
        <IntegrationGrid />
      </MemoryRouter>,
    );
    expect(screen.getByText('Meta CAPI')).toBeDefined();
    expect(screen.getByText('Google Analytics 4')).toBeDefined();
    expect(screen.getByText('Google Ads')).toBeDefined();
    expect(screen.getByText('UTMify')).toBeDefined();
    expect(screen.getByText('Dados Operacionais')).toBeDefined();
    expect(screen.getByText('Nuvemshop')).toBeDefined();
    expect(screen.getByText('Bling')).toBeDefined();
  });

  it('renders the tenant info header', () => {
    renderWithProviders(
      <MemoryRouter>
        <IntegrationGrid />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Configuração do tenant/)).toBeDefined();
  });
});

// --- Store switch isolation ---

import { tenantKey } from '../../../lib/tenantKey';

describe('Store switch isolation', () => {
  it('queryClient.clear() prevents stale data after logout', () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(tenantKey('store-a', 'pedidos'), [{ id: 1 }]);
    client.setQueryData(tenantKey('store-a', 'stats'), { total: 10 });
    expect(client.getQueryData(tenantKey('store-a', 'pedidos'))).toBeDefined();
    client.clear();
    expect(client.getQueryData(tenantKey('store-a', 'pedidos'))).toBeUndefined();
  });

  it('tenantKey scopes data correctly between stores', () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(tenantKey('store-a', 'pedidos'), [{ id: 1 }]);
    client.setQueryData(tenantKey('store-b', 'pedidos'), [{ id: 2 }]);
    const storeA = client.getQueryData(tenantKey('store-a', 'pedidos')) as any[];
    const storeB = client.getQueryData(tenantKey('store-b', 'pedidos')) as any[];
    expect(storeA[0].id).toBe(1);
    expect(storeB[0].id).toBe(2);
    expect(storeA).not.toEqual(storeB);
  });
});