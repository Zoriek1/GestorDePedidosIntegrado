/**
 * App Shell - Responsive layout wrapper
 */

import React, { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Button,
  IconButton,
  Menu,
  MenuItem,
} from '@mui/material';
import { LocalFlorist, Logout, Person, CloudOff, CloudDone, Sync } from '@mui/icons-material';
import { useAuth } from '../features/auth/authStore';
import { useOffline } from '../lib/offline/OfflineProvider';
import { Chip, Tooltip, Badge } from '@mui/material';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate();
  const { isAuthenticated, getCredentials, logout: handleLogout } = useAuth();
  const { isOnline, outboxCount } = useOffline();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  const authenticated = isAuthenticated();
  const credentials = authenticated ? getCredentials() : null;
  const username = credentials?.username;

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogoutClick = () => {
    handleLogout();
    handleMenuClose();
    navigate('/login', { replace: true });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="sticky" sx={{ bgcolor: 'primary.main' }}>
        <Toolbar>
          <LocalFlorist sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Plante Uma Flor - Gestão de Pedidos
          </Typography>

          {/* Navigation Links */}
          <Box sx={{ display: 'flex', gap: 1, mr: 2 }}>
            <Button
              color="inherit"
              onClick={() => navigate('/')}
              sx={{ textTransform: 'none' }}
            >
              Pedidos
            </Button>
            <Button
              color="inherit"
              onClick={() => navigate('/clientes')}
              sx={{ textTransform: 'none' }}
            >
              Clientes
            </Button>
            <Button
              color="inherit"
              onClick={() => navigate('/pedidos/novo')}
              sx={{ textTransform: 'none' }}
            >
              Novo Pedido
            </Button>
          </Box>

          {/* Offline Status Indicators */}
          {authenticated && (
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mr: 2 }}>
              <Chip
                icon={isOnline ? <CloudDone /> : <CloudOff />}
                label={isOnline ? 'Online' : 'Offline'}
                color={isOnline ? 'success' : 'default'}
                size="small"
              />
              {outboxCount > 0 && (
                <Tooltip title={`${outboxCount} item(ns) pendente(s) de sincronização`}>
                  <Badge badgeContent={outboxCount} color="warning">
                    <Sync fontSize="small" />
                  </Badge>
                </Tooltip>
              )}
            </Box>
          )}

          {/* User Menu */}
          {authenticated && (
            <>
              <IconButton
                color="inherit"
                onClick={handleMenuOpen}
                sx={{ ml: 1 }}
              >
                <Person />
              </IconButton>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleMenuClose}
              >
                {username && (
                  <MenuItem disabled>
                    <Typography variant="body2">{username}</Typography>
                  </MenuItem>
                )}
                <MenuItem onClick={handleLogoutClick}>
                  <Logout sx={{ mr: 1 }} fontSize="small" />
                  Sair
                </MenuItem>
              </Menu>
            </>
          )}
        </Toolbar>
      </AppBar>
      <Container maxWidth="xl" sx={{ flex: 1, py: 3 }}>
        {children}
      </Container>
    </Box>
  );
}

