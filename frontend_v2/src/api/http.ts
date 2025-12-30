/**
 * Single API Client
 * All API calls go through this client
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
const DEFAULT_TIMEOUT = 15000; // 15 seconds

export interface ApiError {
  ok: false;
  success: false;
  status?: number;
  code: string;
  message: string;
  error?: string;
  details?: any;
  requestId: string;
  timeout?: boolean;
  offline?: boolean;
  networkError?: boolean;
}

export interface ApiSuccess<T = any> {
  ok: true;
  success: true;
  data: T;
  status: number;
  requestId: string;
}

export type ApiResponse<T = any> = ApiSuccess<T> | ApiError;

/**
 * Generate unique request ID
 */
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Parse HTTP response
 */
async function parseResponse(response: Response): Promise<{ data: any; isJson: boolean; parseError: Error | null }> {
  // 204 No Content - no body
  if (response.status === 204) {
    return { data: null, isJson: false, parseError: null };
  }

  const contentType = response.headers.get('content-type');
  const isLikelyJson = contentType && contentType.includes('application/json');

  try {
    const text = await response.text();

    if (!text || text.trim() === '') {
      return { data: null, isJson: false, parseError: null };
    }

    if (isLikelyJson || text.trim().startsWith('{') || text.trim().startsWith('[')) {
      try {
        const parsed = JSON.parse(text);
        return { data: parsed, isJson: true, parseError: null };
      } catch (e) {
        if (isLikelyJson) {
          return { data: null, isJson: false, parseError: e as Error };
        }
        return { data: text, isJson: false, parseError: null };
      }
    }

    return { data: text, isJson: false, parseError: null };
  } catch (e) {
    return { data: null, isJson: false, parseError: e as Error };
  }
}

/**
 * Get auth header (simplified: attach to all /api/* except auth endpoints)
 */
function getAuthHeader(endpoint: string, getAuthHeaderFn: () => Record<string, string>): Record<string, string> {
  // Do NOT attach to auth endpoints
  // Note: endpoint does NOT include /api prefix (BASE_URL already includes it)
  if (endpoint === '/auth/login' || endpoint === '/auth/check' || endpoint.startsWith('/auth/login') || endpoint.startsWith('/auth/check')) {
    return {};
  }

  // Attach to all other /api/* requests if credentials exist
  return getAuthHeaderFn();
}

/**
 * Make HTTP request
 */
export async function request<T = any>(
  endpoint: string,
  options: RequestInit = {},
  getAuthHeaderFn: () => Record<string, string>
): Promise<ApiResponse<T>> {
  const url = `${BASE_URL}${endpoint}`;
  const method = options.method || 'GET';
  const requestId = generateRequestId();
  const startTime = Date.now();

  // Headers - IMPORTANT: options.headers primeiro, depois auth injection
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };

  // Simplified auth injection: attach to all /api/* except auth endpoints
  // BUT: if Authorization header is already provided in options.headers, use it (for login check)
  const authHeader = getAuthHeader(endpoint, getAuthHeaderFn);
  Object.assign(headers, authHeader);
  
  // Apply options.headers AFTER auth injection (so explicit headers override)
  Object.assign(headers, options.headers as Record<string, string> || {});

  // Content-Type for POST/PUT with body
  if ((method === 'POST' || method === 'PUT') && options.body) {
    headers['Content-Type'] = 'application/json';
  }

  // Timeout with AbortController
  const timeoutMs = (options as any).timeoutMs ?? DEFAULT_TIMEOUT;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const config: RequestInit = {
    method,
    headers,
    ...options,
    signal: controller.signal
  };

  try {
    const response = await fetch(url, config);
    clearTimeout(timeoutId);

    const durationMs = Date.now() - startTime;
    const parseResult = await parseResponse(response);

    if (parseResult.parseError) {
      console.warn(`[API] Parse error:`, parseResult.parseError);
      if (response.ok) {
        return {
          ok: true,
          success: true,
          data: parseResult.data || null,
          status: response.status,
          requestId
        };
      }
      throw new Error(`Erro ${response.status} - Resposta não é JSON válido`);
    }

    if (!response.ok) {
      const errorMsg = parseResult.isJson && parseResult.data
        ? (parseResult.data.error || parseResult.data.message || `Erro ${response.status}`)
        : `Erro ${response.status}`;

      return {
        ok: false,
        success: false,
        status: response.status,
        code: `HTTP_${response.status}`,
        message: errorMsg,
        details: parseResult.isJson ? parseResult.data : null,
        requestId
      };
    }

    return {
      ok: true,
      success: true,
      data: parseResult.data,
      status: response.status,
      requestId
    };
  } catch (error) {
    clearTimeout(timeoutId);
    const durationMs = Date.now() - startTime;

    // Handle AbortError (timeout)
    if ((error as Error).name === 'AbortError') {
      return {
        ok: false,
        success: false,
        error: 'Timeout na requisição',
        code: 'TIMEOUT',
        message: 'Timeout na requisição',
        timeout: true,
        requestId
      };
    }

    // Handle offline
    if (!navigator.onLine) {
      return {
        ok: false,
        success: false,
        offline: true,
        error: (error as Error).message,
        code: 'OFFLINE',
        message: (error as Error).message,
        requestId
      };
    }

    // Handle network error
    if ((error as Error).name === 'TypeError' && (error as Error).message.includes('fetch')) {
      return {
        ok: false,
        success: false,
        error: 'Erro de conexão. Verifique sua internet e se o servidor está rodando.',
        code: 'NETWORK_ERROR',
        message: 'Erro de conexão. Verifique sua internet e se o servidor está rodando.',
        networkError: true,
        requestId
      };
    }

    return {
      ok: false,
      success: false,
      error: (error as Error).message || 'Erro desconhecido na requisição',
      code: 'UNKNOWN_ERROR',
      message: (error as Error).message || 'Erro desconhecido na requisição',
      requestId
    };
  }
}

/**
 * Create API request function with auth
 * This should be called from React Query hooks, not directly
 */
export function createApiRequest(getAuthHeaderFn: () => Record<string, string>) {
  return <T = any>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> => {
    return request<T>(endpoint, options, getAuthHeaderFn);
  };
}

