/**
 * Route Guard - Requires authentication
 * Redirects to /login if not authenticated
 */

import { Navigate, useLocation } from 'react-router-dom';
import { ReactNode } from 'react';
import { useAuth } from './authStore';
import { Box, Paper, Typography, Button } from '@mui/material';
import { WifiOff } from '@mui/icons-material';

interface RequireAuthProps {
  children: ReactNode;
}

export function RequireAuth({ children }: RequireAuthProps) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated()) {
    // Offline UX: if no credentials, don't redirect-loop to login; show a clear message.
    if (!navigator.onLine) {
      return (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '60vh',
          }}
        >
          <Paper sx={{ p: 3, maxWidth: 520, width: '100%', textAlign: 'center' }}>
            <WifiOff sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Sem conexão para login
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Para entrar, conecte-se à internet e tente novamente.
            </Typography>
            <Button variant="contained" onClick={() => window.location.reload()}>
              Tentar novamente
            </Button>
          </Paper>
        </Box>
      );
    }
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

