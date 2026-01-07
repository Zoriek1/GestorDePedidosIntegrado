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
  details?: unknown;
  requestId: string;
  timeout?: boolean;
  offline?: boolean;
  networkError?: boolean;
}

export interface ApiSuccess<T = unknown> {
  ok: true;
  success: true;
  data: T;
  status: number;
  requestId: string;
}

export type ApiResponse<T = unknown> = ApiSuccess<T> | ApiError;

/**
 * Generate unique request ID
 */
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Parse HTTP response
 */
async function parseResponse(response: Response): Promise<{ data: unknown; isJson: boolean; parseError: Error | null; isHtml?: boolean }> {
  // 204 No Content - no body
  if (response.status === 204) {
    return { data: null, isJson: false, parseError: null, isHtml: false };
  }

  const contentType = response.headers.get('content-type') || '';
  const isLikelyJson = contentType.includes('application/json');
  const isLikelyHtml = contentType.includes('text/html') || contentType.includes('text/html;');

  try {
    const text = await response.text();

    if (!text || text.trim() === '') {
      return { data: null, isJson: false, parseError: null, isHtml: false };
    }

    // Detectar HTML: content-type text/html ou começa com <!doctype (case insensitive)
    const trimmedText = text.trim();
    const isHtmlContent = isLikelyHtml || /^\s*<!doctype\s+html/i.test(trimmedText) || trimmedText.startsWith('<html');

    // Se recebemos HTML quando esperamos JSON (API), tratar como erro
    if (isHtmlContent) {
      return {
        data: text,
        isJson: false,
        parseError: new Error('Resposta HTML recebida quando esperava JSON. O endpoint da API pode não estar acessível.'),
        isHtml: true
      };
    }

    if (isLikelyJson || trimmedText.startsWith('{') || trimmedText.startsWith('[')) {
      try {
        const parsed = JSON.parse(text);
        return { data: parsed, isJson: true, parseError: null, isHtml: false };
      } catch (e) {
        if (isLikelyJson) {
          return { data: null, isJson: false, parseError: e as Error, isHtml: false };
        }
        return { data: text, isJson: false, parseError: null, isHtml: false };
      }
    }

    return { data: text, isJson: false, parseError: null, isHtml: false };
  } catch (e) {
    return { data: null, isJson: false, parseError: e as Error, isHtml: false };
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
export async function request<T = unknown>(
  endpoint: string,
  options: RequestInit = {},
  getAuthHeaderFn: () => Record<string, string>
): Promise<ApiResponse<T>> {
  const url = `${BASE_URL}${endpoint}`;
  const method = options.method || 'GET';
  const requestId = generateRequestId();

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
  const timeoutMs = (options as RequestInit & { timeoutMs?: number }).timeoutMs ?? DEFAULT_TIMEOUT;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // IMPORTANT: não permitir que options.headers sobrescreva o header mergeado
  // (caso contrário, POST/PUT com headers custom perde Authorization)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { headers: _ignoredHeaders, ...restOptions } = options as RequestInit & { timeoutMs?: number };
  const config: RequestInit = {
    method,
    ...restOptions,
    headers,
    signal: controller.signal,
  };

  try {
    const response = await fetch(url, config);
    clearTimeout(timeoutId);

    const parseResult = await parseResponse(response);

    // Se recebemos HTML quando esperamos JSON, tratar como erro crítico
    if (parseResult.isHtml) {
      const errorMsg = parseResult.parseError?.message || 'Endpoint da API retornou HTML ao invés de JSON. Verifique se o backend está rodando e se o roteamento está correto.';
      return {
        ok: false,
        success: false,
        status: response.status || 500,
        code: 'HTML_RESPONSE',
        message: errorMsg,
        details: null,
        requestId
      };
    }

    if (parseResult.parseError) {
      // Log removido em produção
      if (response.ok) {
        return {
          ok: true,
          success: true,
          data: (parseResult.data || null) as T,
          status: response.status,
          requestId
        };
      }
      throw new Error(`Erro ${response.status} - Resposta não é JSON válido`);
    }

    if (!response.ok) {
      const errorData = parseResult.data as { error?: string; message?: string } | null;
      const errorMsg = parseResult.isJson && errorData
        ? (errorData.error || errorData.message || `Erro ${response.status}`)
        : `Erro ${response.status}`;

      // Notificar listeners de auth inválida (401/403)
      if (response.status === 401 || response.status === 403) {
        try {
          window.dispatchEvent(new CustomEvent('puf_auth_invalid'));
        } catch {
          // silencioso
        }
      }

      // NÃO disparar logout automático. Apenas retornar erro.
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
      data: parseResult.data as T,
      status: response.status,
      requestId
    };
  } catch (error) {
    clearTimeout(timeoutId);

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
  return <T = unknown>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> => {
    return request<T>(endpoint, options, getAuthHeaderFn);
  };
}

