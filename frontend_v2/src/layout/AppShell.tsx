/**
 * App Shell - Responsive layout wrapper
 */

import React, { ReactNode, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
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
  Tooltip,
  Badge,
  Divider,
  Fab,
} from '@mui/material';
import {
  LocalFlorist,
  Logout,
  Person,
  CloudOff,
  CloudDone,
  Menu as MenuIcon,
  NotificationsNone,
  Add as AddIcon,
} from '@mui/icons-material';
import { useAuth } from '../features/auth/authStore';
import { useOffline } from '../lib/offline/OfflineProvider';
import { Chip } from '@mui/material';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, getCredentials, logout: handleLogout } = useAuth();
  const { isOnline, outboxCount } = useOffline();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [navMenuEl, setNavMenuEl] = React.useState<null | HTMLElement>(null);
  
  // Full width para páginas de wizard de pedido
  const isOrderWizardPage =
    location.pathname === '/pedidos/novo' ||
    location.pathname.startsWith('/pedidos/') && location.pathname.endsWith('/editar');

  const authenticated = isAuthenticated();
  const credentials = authenticated ? getCredentials() : null;
  const username = credentials?.username;

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleNavMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setNavMenuEl(event.currentTarget);
  };

  const handleNavMenuClose = useCallback(() => {
    setNavMenuEl(null);
  }, []);

  const handleCreateOrder = useCallback(() => {
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.removeItem('puf_pedido_draft_v2');
        window.localStorage.removeItem('puf_pedido_step_v2');
      } catch {
        // ignorar falhas de limpeza
      }
    }
    handleNavMenuClose();
    navigate('/pedidos/novo', { state: { orderReset: Date.now() } });
  }, [handleNavMenuClose, navigate]);

  const handleNavigate = (path: string) => {
    navigate(path);
    handleNavMenuClose();
  };

  const handleLogoutClick = () => {
    handleLogout();
    handleMenuClose();
    navigate('/login', { replace: true });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="sticky" sx={{ bgcolor: 'primary.main' }}>
        <Toolbar sx={{ gap: 2 }}>
          {/* Seção Esquerda: Marca */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 0 }}>
            <LocalFlorist />
            <Typography
              variant="h6"
              component="div"
              sx={{
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                fontWeight: 600,
              }}
            >
              Plante Uma Flor
            </Typography>
          </Box>

          {/* Seção Centro: Navegação (desktop) */}
          <Box
            sx={{
              flex: 1,
              display: { xs: 'none', md: 'flex' },
              justifyContent: 'center',
              gap: 1,
            }}
          >
            <Button color="inherit" onClick={() => handleNavigate('/')} sx={{ textTransform: 'none' }}>
              Pedidos
            </Button>
            <Button color="inherit" onClick={() => handleNavigate('/clientes')} sx={{ textTransform: 'none' }}>
              Clientes
            </Button>
            <Button color="inherit" onClick={() => handleNavigate('/fontes-pedido')} sx={{ textTransform: 'none' }}>
              Fontes
            </Button>
            <Button color="inherit" onClick={() => handleNavigate('/rota-entrega')} sx={{ textTransform: 'none' }}>
              Rota
            </Button>
          </Box>

          {/* Seção Direita: Status + Notificações + Perfil */}
          {authenticated && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Chip
                icon={isOnline ? <CloudDone /> : <CloudOff />}
                label={isOnline ? 'Online' : 'Offline'}
                color={isOnline ? 'success' : 'default'}
                size="small"
              />
              <Tooltip title={outboxCount > 0 ? `${outboxCount} item(ns) pendente(s) de sincronização` : 'Sem pendências'}>
                <span>
                  <Badge badgeContent={outboxCount || 0} color={outboxCount > 0 ? 'warning' : 'default'}>
                    <NotificationsNone sx={{ color: 'inherit' }} />
                  </Badge>
                </span>
              </Tooltip>
              <Divider flexItem orientation="vertical" sx={{ borderColor: 'rgba(255,255,255,0.2)' }} />
              <IconButton color="inherit" onClick={handleMenuOpen} sx={{ ml: 0.5 }}>
                <Person />
              </IconButton>
              <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose}>
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
            </Box>
          )}

          {/* Mobile: Menu hamburger */}
          <Box sx={{ display: { xs: 'flex', md: 'none' }, ml: authenticated ? 1 : 0 }}>
            <IconButton color="inherit" onClick={handleNavMenuOpen}>
              <MenuIcon />
            </IconButton>
            <Menu anchorEl={navMenuEl} open={Boolean(navMenuEl)} onClose={handleNavMenuClose}>
              <MenuItem onClick={() => handleNavigate('/')}>Pedidos</MenuItem>
              <MenuItem onClick={() => handleNavigate('/clientes')}>Clientes</MenuItem>
              <MenuItem onClick={() => handleNavigate('/fontes-pedido')}>Fontes</MenuItem>
              <MenuItem onClick={() => handleNavigate('/rota-entrega')}>Rota</MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>
      {authenticated && (
        <Fab
          color="primary"
          aria-label="Criar pedido"
          onClick={handleCreateOrder}
          sx={{
            position: 'fixed',
            top: { xs: 72, sm: 80 },
            right: { xs: 16, sm: 20 },
            zIndex: (theme) => theme.zIndex.drawer + 1,
            boxShadow: 6,
          }}
        >
          <AddIcon />
        </Fab>
      )}
      <Container
        maxWidth={isOrderWizardPage ? false : 'xl'}
        sx={{
          flex: 1,
          py: 3,
          px: isOrderWizardPage ? { xs: 2, sm: 3, md: 4 } : 3,
          bgcolor: isOrderWizardPage ? 'grey.100' : undefined,
        }}
      >
        {children}
      </Container>
    </Box>
  );
}

