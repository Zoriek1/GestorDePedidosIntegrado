/**
 * App Providers
 * Single QueryClient and ThemeProvider instance
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AuthProvider } from '../features/auth/authStore';
import { ReactNode } from 'react';
import { ToastProvider } from '../components/system/ToastProvider';
import { ConfirmProvider } from '../components/system/ConfirmProvider';
import { OfflineProvider } from '../lib/offline/OfflineProvider';

// Single QueryClient instance (prevents duplicate initialization)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,
      retry: 1,
      staleTime: 30000,
    },
  },
});

// MUI Theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#047857', // Same as legacy
    },
    secondary: {
      main: '#059669',
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
        <AuthProvider>
          <ToastProvider>
            <OfflineProvider>
              <ConfirmProvider>
                {children}
              </ConfirmProvider>
            </OfflineProvider>
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

