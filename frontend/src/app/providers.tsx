import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AuthProvider } from '../features/auth/authStore';
import { ReactNode, useState, useEffect, useCallback, useMemo } from 'react';
import { ToastProvider } from '../components/system/ToastProvider';
import { ConfirmProvider } from '../components/system/ConfirmProvider';
import { OfflineProvider } from '../lib/offline/OfflineProvider';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import 'dayjs/locale/pt-br';
import {
  createAppTheme,
  getStoredThemeMode,
  resolveThemeMode,
  THEME_MODE_KEY,
  type ThemeMode,
} from './theme';
import { ThemeContext } from './ThemeContext';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
});

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [mode, setModeState] = useState<ThemeMode>(getStoredThemeMode);
  const [resolvedMode, setResolvedMode] = useState<'light' | 'dark'>(() => resolveThemeMode(mode));

  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode);
    try {
      localStorage.setItem(THEME_MODE_KEY, newMode);
    } catch { /* ignore */ }
    setResolvedMode(resolveThemeMode(newMode));
  }, []);

  useEffect(() => {
    if (mode !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => setResolvedMode(resolveThemeMode('system'));
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [mode]);

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', resolvedMode);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute('content', resolvedMode === 'dark' ? '#121212' : '#143d28');
    }
  }, [resolvedMode]);

  const theme = useMemo(() => createAppTheme(resolvedMode), [resolvedMode]);
  const ctxValue = useMemo(() => ({ mode, resolvedMode, setMode }), [mode, resolvedMode, setMode]);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeContext.Provider value={ctxValue}>
        <MuiThemeProvider theme={theme}>
          <CssBaseline />
          <LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale="pt-br">
            <AuthProvider>
              <ToastProvider>
                <OfflineProvider>
                  <ConfirmProvider>
                    {children}
                  </ConfirmProvider>
                </OfflineProvider>
              </ToastProvider>
            </AuthProvider>
          </LocalizationProvider>
        </MuiThemeProvider>
      </ThemeContext.Provider>
    </QueryClientProvider>
  );
}
