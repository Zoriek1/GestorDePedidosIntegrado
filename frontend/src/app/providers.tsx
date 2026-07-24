/**
 * App Providers
 * Single QueryClient and ThemeProvider instance
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AuthProvider } from '../features/auth/authStore';
import { ReactNode } from 'react';
import { ToastProvider } from '../components/system/ToastProvider';
import { ConfirmProvider } from '../components/system/ConfirmProvider';
import { OfflineProvider } from '../lib/offline/OfflineProvider';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import 'dayjs/locale/pt-br';
import { theme } from './theme';

// Single QueryClient instance (prevents duplicate initialization)
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
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
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
      </ThemeProvider>
    </QueryClientProvider>
  );
}

