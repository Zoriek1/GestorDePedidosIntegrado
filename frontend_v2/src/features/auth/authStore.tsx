/**
 * Auth Store - React Context + Hooks
 * Mirrors legacy auth.js behavior exactly for compatibility
 */

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';

const STORAGE_KEY = 'plante_uma_flor_auth';
const SESSION_KEY = 'plante_uma_flor_auth_session';
const CACHE_DURATION = 5000; // 5 seconds

interface AuthCredentials {
  username: string;
  password: string;
  role?: string; // Papel do usuário (admin, atendente, entregador)
  timestamp: number;
}

interface AuthContextType {
  isAuthenticated: () => boolean;
  getCredentials: () => AuthCredentials | null;
  getUserRole: () => string | null; // Retorna o papel do usuário
  loadSavedCredentials: () => AuthCredentials | null; // Public alias for getCredentials
  saveCredentials: (username: string, password: string, remember?: boolean) => void;
  getAuthHeader: () => Record<string, string>;
  login: (username: string, password: string, remember?: boolean) => Promise<{ success: boolean; error?: string; message?: string; role?: string }>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Initialize cache synchronously to avoid null state and setState during render
  const initialAuth = (() => {
    try {
      return (localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(SESSION_KEY)) !== null;
    } catch {
      return false;
    }
  })();
  
  const [authCache, setAuthCache] = useState<boolean>(initialAuth);
  const [cacheTimestamp, setCacheTimestamp] = useState<number>(Date.now());

  const getCredentials = useCallback((): AuthCredentials | null => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(SESSION_KEY);
      if (stored) {
        return JSON.parse(stored) as AuthCredentials;
      }
    } catch (error) {
      console.error('Erro ao obter credenciais:', error);
    }
    return null;
  }, []);

  // Update cache periodically and on mount (useEffect to avoid setState during render)
  useEffect(() => {
    const checkStorage = () => {
      const stored = localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(SESSION_KEY);
      const isAuth = stored !== null;
      const now = Date.now();
      
      // Only update if cache is invalid or different
      if (authCache !== isAuth || (now - cacheTimestamp) >= CACHE_DURATION) {
        setAuthCache(isAuth);
        setCacheTimestamp(now);
      }
    };

    // Initial check
    checkStorage();
    
    // Periodic check (every CACHE_DURATION)
    const interval = setInterval(checkStorage, CACHE_DURATION);
    
    // Listen for storage changes (from other tabs)
    const handleStorageChange = () => checkStorage();
    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []); // Empty deps - only run on mount/unmount

  const isAuthenticated = useCallback((): boolean => {
    // Check if cache is valid
    const now = Date.now();
    if ((now - cacheTimestamp) < CACHE_DURATION) {
      return authCache;
    }

    // If cache is invalid, check storage synchronously (read-only, no setState)
    // The useEffect will update the cache asynchronously
    try {
      const stored = localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(SESSION_KEY);
      return stored !== null;
    } catch {
      return false;
    }
  }, [authCache, cacheTimestamp]);

  const saveCredentials = useCallback((username: string, password: string, remember = false, role?: string): void => {
    const authData: AuthCredentials = {
      username,
      password,
      role,
      timestamp: Date.now()
    };

    if (remember) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(authData));
    } else {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(authData));
    }

    // Update cache
    setAuthCache(true);
    setCacheTimestamp(Date.now());
  }, []);

  const getUserRole = useCallback((): string | null => {
    const creds = getCredentials();
    return creds?.role || null;
  }, [getCredentials]);

  const getAuthHeader = useCallback((): Record<string, string> => {
    const creds = getCredentials();
    if (!creds) {
      return {};
    }

    // Create Basic Auth header
    // Important: btoa() does NOT handle UTF-8 correctly in general
    // Use btoa() as primary (works for ASCII), fallback only if it fails
    try {
      const credentials = btoa(`${creds.username}:${creds.password}`);
      return {
        'Authorization': `Basic ${credentials}`
      };
    } catch {
      // Fallback for non-ASCII: convert bytes to string in chunks
      // Critical: Avoid String.fromCharCode(...data) which can exceed argument limits
      const encoder = new TextEncoder();
      const data = encoder.encode(`${creds.username}:${creds.password}`);
      let binary = '';
      const chunkSize = 8192;
      for (let i = 0; i < data.length; i += chunkSize) {
        binary += String.fromCharCode(...data.slice(i, i + chunkSize));
      }
      const base64 = btoa(binary);
      return {
        'Authorization': `Basic ${base64}`
      };
    }
  }, [getCredentials]);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem(SESSION_KEY);

    // Clear cache
    setAuthCache(false);
    setCacheTimestamp(Date.now());
  }, []);

  // Logout e redireciona em 401/403
  useEffect(() => {
    const handleAuthInvalid = () => {
      logout();
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    };

    window.addEventListener('puf_auth_invalid', handleAuthInvalid as EventListener);
    return () => {
      window.removeEventListener('puf_auth_invalid', handleAuthInvalid as EventListener);
    };
  }, [logout]);

  const login = useCallback(async (username: string, password: string, remember = false): Promise<{ success: boolean; error?: string; message?: string; role?: string }> => {
    try {
      // Primary approach (robust): Save credentials first, then validate via GET /api/auth/check
      // This is the robust Basic Auth approach - do NOT require POST /api/auth/login
      saveCredentials(username, password, remember);

      // Validate credentials using GET /api/auth/check with Authorization header
      const { createApiRequest } = await import('../../api/http');
      const tempAuthHeader = () => {
        // Create auth header temporarily for validation
        try {
          const credentials = btoa(`${username}:${password}`);
          return { 'Authorization': `Basic ${credentials}` };
        } catch {
          const encoder = new TextEncoder();
          const data = encoder.encode(`${username}:${password}`);
          let binary = '';
          const chunkSize = 8192;
          for (let i = 0; i < data.length; i += chunkSize) {
            binary += String.fromCharCode(...data.slice(i, i + chunkSize));
          }
          return { 'Authorization': `Basic ${btoa(binary)}` };
        }
      };

      // Create request with explicit Authorization header (bypass getAuthHeader exclusion)
      const tempAuthHeaderValue = tempAuthHeader();
      const apiRequest = createApiRequest(tempAuthHeader);
      const response = await apiRequest<{ success: boolean; authenticated?: boolean; message?: string; role?: string }>('/auth/check', {
        headers: tempAuthHeaderValue
      });

      if (response.ok && response.data?.success && response.data?.authenticated === true) {
        const role = (response.data as any)?.role || 'admin'; // Default para admin se não especificado
        saveCredentials(username, password, remember, role);
        return { success: true, message: 'Login realizado com sucesso', role };
      } else {
        // Validation failed - clear credentials
        logout();
        const errorMessage = response.ok && response.data ? response.data.message : 'Credenciais inválidas';
        return { 
          success: false, 
          error: errorMessage
        };
      }
    } catch (error) {
      console.error('Erro ao fazer login:', error);
      // Clear credentials on error
      logout();
      return {
        success: false,
        error: 'Erro ao conectar com o servidor. Verifique sua conexão.'
      };
    }
  }, [saveCredentials, logout]);

  const checkAuth = useCallback(async (): Promise<boolean> => {
    try {
      const creds = getCredentials();
      if (!creds) {
        return false;
      }

      const response = await fetch('/api/auth/check', {
        headers: getAuthHeader()
      });

      const data = await response.json();
      if (data.success && data.authenticated === true) {
        // Atualizar papel se retornado pelo servidor
        if (data.role && creds.role !== data.role) {
          saveCredentials(creds.username, creds.password, !!localStorage.getItem(STORAGE_KEY), data.role);
        }
        return true;
      }
      return false;
    } catch (error) {
      console.error('Erro ao verificar autenticação:', error);
      return false;
    }
  }, [getCredentials, getAuthHeader, saveCredentials]);

  const loadSavedCredentials = useCallback((): AuthCredentials | null => {
    return getCredentials();
  }, [getCredentials]);

  const value: AuthContextType = {
    isAuthenticated,
    getCredentials,
    getUserRole,
    loadSavedCredentials,
    saveCredentials,
    getAuthHeader,
    login,
    logout,
    checkAuth
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

