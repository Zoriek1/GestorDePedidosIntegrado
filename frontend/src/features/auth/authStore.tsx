/**
 * Auth Store — JWT (módulo Recebíveis) com fallback Basic Auth (env-var users legado)
 *
 * Prioridade de auth:
 *   1. JWT Bearer token (usuários DB) — session/localStorage conforme "Lembrar-me"
 *   2. Basic Auth (usuários env-var legado) — fallback durante transição
 */

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { createApiRequest } from '../../api/http';
import { createLogger } from '../../lib/logger';

const log = createLogger('AuthStore');

// Query key raiz do cache de integrações por loja. Mantido em sincronia com
// features/config/hooks/useConfig.ts para que o logout/troca de identidade limpe
// o cache correto sem vazar segredos entre lojas.
const INTEGRATIONS_QUERY_KEY = ['config', 'integrations'] as const;

// JWT: sessionStorage (sem lembrar) ou localStorage (lembrar-me)
const JWT_KEY = 'puf_jwt';
const JWT_USER_KEY = 'puf_jwt_user';
const JWT_REMEMBER_KEY = 'puf_jwt_remember';
// Legado: Basic Auth
const STORAGE_KEY = 'plante_uma_flor_auth';
const SESSION_KEY = 'plante_uma_flor_auth_session';

export interface AuthUser {
  id?: number;
  username?: string; // legado
  name?: string;
  email?: string;
  role: string;
  // Multi-tenant (Fase A): identidade da loja retornada pelo login/JWT.
  store_ref_id?: number | null;
  store_slug?: string | null;
}

interface LegacyCredentials {
  username: string;
  password: string;
  role?: string;
  timestamp: number;
}

interface AuthContextType {
  isAuthenticated: () => boolean;
  isJwtUser: () => boolean;
  getUserRole: () => string | null;
  getAuthHeader: () => Record<string, string>;
  getUser: () => AuthUser | null;
  /** @deprecated use getUser() */
  getCredentials: () => LegacyCredentials | null;
  /** @deprecated use getUser() */
  loadSavedCredentials: () => LegacyCredentials | null;
  /** @deprecated use login() */
  saveCredentials: (username: string, password: string, remember?: boolean, role?: string) => void;
  login: (
    username: string,
    password: string,
    remember?: boolean
  ) => Promise<{ success: boolean; error?: string; message?: string; role?: string }>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ---------------------------------------------------------------------------
// Helpers de storage
// ---------------------------------------------------------------------------
function readJwtToken(): string | null {
  try {
    return sessionStorage.getItem(JWT_KEY) || localStorage.getItem(JWT_KEY);
  } catch {
    return null;
  }
}

function readJwtUser(): AuthUser | null {
  try {
    const raw = sessionStorage.getItem(JWT_USER_KEY) || localStorage.getItem(JWT_USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

function writeJwt(token: string, user: AuthUser, remember: boolean): void {
  try {
    if (remember) {
      localStorage.setItem(JWT_KEY, token);
      localStorage.setItem(JWT_USER_KEY, JSON.stringify(user));
      localStorage.setItem(JWT_REMEMBER_KEY, '1');
      sessionStorage.removeItem(JWT_KEY);
      sessionStorage.removeItem(JWT_USER_KEY);
    } else {
      sessionStorage.setItem(JWT_KEY, token);
      sessionStorage.setItem(JWT_USER_KEY, JSON.stringify(user));
      sessionStorage.setItem(JWT_REMEMBER_KEY, '0');
      localStorage.removeItem(JWT_KEY);
      localStorage.removeItem(JWT_USER_KEY);
    }
  } catch {
    // storage pode estar indisponível
  }
}

function clearJwt(): void {
  try {
    sessionStorage.removeItem(JWT_KEY);
    sessionStorage.removeItem(JWT_USER_KEY);
    sessionStorage.removeItem(JWT_REMEMBER_KEY);
    localStorage.removeItem(JWT_KEY);
    localStorage.removeItem(JWT_USER_KEY);
    localStorage.removeItem(JWT_REMEMBER_KEY);
  } catch { /* empty */ }
}

function readLegacyCreds(): LegacyCredentials | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as LegacyCredentials) : null;
  } catch {
    return null;
  }
}

function writeLegacyCreds(creds: LegacyCredentials, remember: boolean): void {
  try {
    if (remember) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(creds));
    } else {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(creds));
    }
  } catch { /* empty */ }
}

function clearLegacyCreds(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem(SESSION_KEY);
  } catch { /* empty */ }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
export function AuthProvider({ children }: { children: ReactNode }) {
  // Token JWT em estado React (fonte primária de verdade para renders)
  const [jwtToken, setJwtToken] = useState<string | null>(() => readJwtToken());
  const [jwtUser, setJwtUser] = useState<AuthUser | null>(() => readJwtUser());
  const queryClient = useQueryClient();

  // Remove o cache de integrações (segredos mascarados por loja). Chamado no
  // logout e ao trocar de identidade autenticada, para não exibir dados da loja
  // anterior.
  const clearIntegrationsCache = useCallback(() => {
    queryClient.removeQueries({ queryKey: INTEGRATIONS_QUERY_KEY });
  }, [queryClient]);

  // ---------------------------------------------------------------------------
  const isAuthenticated = useCallback((): boolean => {
    if (jwtToken) return true;
    return readLegacyCreds() !== null;
  }, [jwtToken]);

  const isJwtUser = useCallback((): boolean => {
    return !!(jwtToken || readJwtToken());
  }, [jwtToken]);

  const getUser = useCallback((): AuthUser | null => {
    if (jwtUser) return jwtUser;
    const legacy = readLegacyCreds();
    if (legacy) {
      return { username: legacy.username, role: legacy.role || 'admin' };
    }
    return null;
  }, [jwtUser]);

  const getUserRole = useCallback((): string | null => {
    return getUser()?.role ?? null;
  }, [getUser]);

  // ---------------------------------------------------------------------------
  const getAuthHeader = useCallback((): Record<string, string> => {
    // Prioridade 1: JWT Bearer
    const token = jwtToken || readJwtToken();
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }

    // Prioridade 2: Basic Auth (legado env-var users)
    const legacy = readLegacyCreds();
    if (legacy) {
      try {
        const credentials = btoa(`${legacy.username}:${legacy.password}`);
        return { Authorization: `Basic ${credentials}` };
      } catch {
        const encoder = new TextEncoder();
        const data = encoder.encode(`${legacy.username}:${legacy.password}`);
        let binary = '';
        for (let i = 0; i < data.length; i += 8192) {
          binary += String.fromCharCode(...data.slice(i, i + 8192));
        }
        return { Authorization: `Basic ${btoa(binary)}` };
      }
    }

    return {};
  }, [jwtToken]);

  // ---------------------------------------------------------------------------
  const logout = useCallback(() => {
    clearJwt();
    clearLegacyCreds();
    setJwtToken(null);
    setJwtUser(null);
    clearIntegrationsCache();
  }, [clearIntegrationsCache]);

  // Logout automático em 401/403
  useEffect(() => {
    const handleAuthInvalid = () => {
      logout();
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    };
    window.addEventListener('puf_auth_invalid', handleAuthInvalid as EventListener);
    return () => window.removeEventListener('puf_auth_invalid', handleAuthInvalid as EventListener);
  }, [logout]);

  // ---------------------------------------------------------------------------
  const login = useCallback(
    async (
      username: string,
      password: string,
      remember = false
    ): Promise<{ success: boolean; error?: string; message?: string; role?: string }> => {
      try {
        const apiRequest = createApiRequest(() => ({}));
        const response = await apiRequest<{
          access_token?: string;
          user?: AuthUser;
          username?: string;
          role?: string;
          message?: string;
        }>('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email: username, password }),
        });

        if (!response.ok) {
          logout();
          return { success: false, error: response.message ?? 'Credenciais inválidas' };
        }

        const data = response.data;

        // --- JWT (usuário DB) ---
        if (data?.access_token) {
          const user: AuthUser = data.user ?? {
            role: data.role ?? 'vendedor',
            email: username,
          };
          // Nova identidade: descarta qualquer cache de integrações da sessão anterior.
          clearIntegrationsCache();
          writeJwt(data.access_token, user, remember);
          setJwtToken(data.access_token);
          setJwtUser(user);
          clearLegacyCreds();
          log.debug('JWT login OK', { role: user.role });
          return { success: true, message: 'Login realizado com sucesso', role: user.role };
        }

        // --- Basic Auth (usuário env-var legado) ---
        if (data?.username) {
          const role = data.role ?? 'admin';
          const creds: LegacyCredentials = { username: data.username, password, role, timestamp: Date.now() };
          clearIntegrationsCache();
          writeLegacyCreds(creds, remember);
          clearJwt();
          setJwtToken(null);
          setJwtUser(null);
          log.debug('Legacy login OK', { role });
          return { success: true, message: 'Login realizado com sucesso', role };
        }

        logout();
        return { success: false, error: 'Resposta inesperada do servidor' };
      } catch (error) {
        log.error('Erro ao fazer login:', error);
        logout();
        return { success: false, error: 'Erro ao conectar com o servidor. Verifique sua conexão.' };
      }
    },
    [logout, clearIntegrationsCache]
  );

  // ---------------------------------------------------------------------------
  const checkAuth = useCallback(async (): Promise<boolean> => {
    // JWT: verificar /api/auth/me
    const token = jwtToken || readJwtToken();
    if (token) {
      try {
        const response = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) return true;
        // Token expirado/inválido — só limpa se o servidor respondeu 401/403.
        // Erro de rede (catch) não deve apagar a sessão local.
        if (response.status === 401 || response.status === 403) {
          clearJwt();
          setJwtToken(null);
          setJwtUser(null);
        }
        return false;
      } catch {
        return false;
      }
    }

    // Legado: Basic Auth check
    const legacy = readLegacyCreds();
    if (!legacy) return false;
    try {
      const creds = btoa(`${legacy.username}:${legacy.password}`);
      const response = await fetch('/api/auth/check', {
        headers: { Authorization: `Basic ${creds}` },
      });
      const data = await response.json();
      const ok = !!(data.success && data.authenticated);
      if (!ok && (response.status === 401 || response.status === 403)) {
        clearLegacyCreds();
      }
      return ok;
    } catch {
      return false;
    }
  }, [jwtToken]);

  // Validação de auth no boot — confirma que sessão local ainda é válida no servidor.
  // Só revalida se já existe credencial; offline é ignorado para não invalidar à toa.
  useEffect(() => {
    const hasJwt = !!(jwtToken || readJwtToken());
    const hasLegacy = !!readLegacyCreds();
    if (!hasJwt && !hasLegacy) return;
    if (typeof navigator !== 'undefined' && !navigator.onLine) return;
    void checkAuth().then((ok) => {
      if (!ok) {
        // Sessão expirada/inválida — dispara fluxo padrão de logout + redirect.
        window.dispatchEvent(new Event('puf_auth_invalid'));
      }
    });
    // Executa apenas uma vez no boot do AuthProvider.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------------------
  // @deprecated compatibility shims
  const getCredentials = useCallback((): LegacyCredentials | null => readLegacyCreds(), []);
  const loadSavedCredentials = useCallback((): LegacyCredentials | null => readLegacyCreds(), []);
  const saveCredentials = useCallback(
    (username: string, password: string, remember = false, role?: string) => {
      writeLegacyCreds({ username, password, role, timestamp: Date.now() }, remember);
    },
    []
  );

  const value: AuthContextType = {
    isAuthenticated,
    isJwtUser,
    getUserRole,
    getAuthHeader,
    getUser,
    getCredentials,
    loadSavedCredentials,
    saveCredentials,
    login,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
