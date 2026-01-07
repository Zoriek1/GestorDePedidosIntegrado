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
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import 'dayjs/locale/pt-br';

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

// MUI Theme com layout mais legível e sombras padrão
const theme = createTheme({
  palette: {
    primary: { main: '#047857' },
    secondary: { main: '#059669' },
    background: {
      default: '#f7f9fb',
      paper: '#ffffff',
    },
  },
  shape: {
    borderRadius: 10,
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    body1: { color: '#1f2937' },
    body2: { color: '#4b5563' },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 10px 30px -12px rgba(0,0,0,0.18)',
          borderRadius: 12,
          border: '1px solid #e5e7eb',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 10px 30px -12px rgba(0,0,0,0.20)',
          borderRadius: 12,
          border: '1px solid #e5e7eb',
        },
      },
    },
    MuiContainer: {
      styleOverrides: {
        root: {
          paddingLeft: '1rem',
          paddingRight: '1rem',
        },
      },
    },
    MuiTypography: {
      styleOverrides: {
        h6: { fontWeight: 700 },
        subtitle1: { fontWeight: 600 },
      },
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

