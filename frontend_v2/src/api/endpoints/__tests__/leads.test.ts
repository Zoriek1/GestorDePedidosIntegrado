/**
 * Testes do hook useLeads.
 * Garante que a chamada à API usa createApiRequest corretamente (função, não .get)
 * e que o response é tratado (ok + data).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { createElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useLeads, type LeadsResponse } from '../leads';

vi.mock('../../http', () => ({ createApiRequest: vi.fn() }));
vi.mock('../../../features/auth/authStore', () => ({
  useAuth: vi.fn(() => ({ getAuthHeader: vi.fn(() => ({})) })),
}));

import { createApiRequest } from '../../http';
const mockCreateApiRequest = vi.mocked(createApiRequest);

function createWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return createElement(QueryClientProvider, { client }, children);
  };
}

describe('useLeads', () => {
  const fakeResponse: LeadsResponse = {
    leads: [{ id: 1, event: 'whatsapp_click', utm_source: 'facebook', created_at: '2025-01-01T12:00:00Z', url: null, referrer: null, utm_medium: null, utm_campaign: null, utm_content: null, utm_term: null, src: null, sck: null, ip_address: null }],
    total: 1,
    page: 1,
    pages: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateApiRequest.mockImplementation(() => async () => ({
      ok: true,
      success: true,
      data: fakeResponse,
      status: 200,
      requestId: 'test',
    }));
  });

  it('chama createApiRequest e usa a função retornada (não .get)', async () => {
    const { result } = renderHook(() => useLeads({}), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(fakeResponse);
    expect(mockCreateApiRequest).toHaveBeenCalled();
    const apiFn = mockCreateApiRequest.mock.results[0]?.value;
    expect(typeof apiFn).toBe('function');
  });

  it('repassa filtros na query string', async () => {
    let capturedEndpoint = '';
    mockCreateApiRequest.mockImplementation(() => async (endpoint: string) => {
      capturedEndpoint = endpoint;
      return { ok: true, success: true, data: fakeResponse, status: 200, requestId: 'test' };
    });

    renderHook(() => useLeads({ page: 2, utm_source: 'facebook' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(capturedEndpoint).toContain('/leads');
      expect(capturedEndpoint).toContain('page=2');
      expect(capturedEndpoint).toContain('utm_source=facebook');
    });
  });
});
