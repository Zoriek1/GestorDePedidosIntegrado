import React, { ReactNode, useCallback, useState } from 'react';
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
  Stack,
  Chip,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
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
  Bolt as BoltIcon,
  AddShoppingCart as AddShoppingCartIcon,
  Settings,
} from '@mui/icons-material';

import { useAuth } from '../features/auth/authStore';
import { NotificationManager } from '../features/notifications/NotificationManager';
import { useOffline } from '../lib/offline/useOffline';
import { QuickEntryModal } from '../features/pedidos/components/QuickEntryModal';

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
  const [quickEntryOpen, setQuickEntryOpen] = useState(false);
  const [speedDialOpen, setSpeedDialOpen] = useState(false);
  
  // Full width para páginas de wizard de pedido
  const isOrderWizardPage =
    location.pathname === '/pedidos/novo' ||
    location.pathname.startsWith('/pedidos/') && location.pathname.endsWith('/editar');

  // Mostrar botão flutuante apenas na página de pedidos
  const isOrdersPage = location.pathname === '/';

  const authenticated = isAuthenticated();
  const credentials = authenticated ? getCredentials() : null;
  const username = credentials?.username;
  const userRole = credentials?.role || 'admin'; // Default para admin se não especificado
  const isEntregador = userRole === 'entregador';

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
    setSpeedDialOpen(false);
    navigate('/pedidos/novo', { state: { orderReset: Date.now() } });
  }, [handleNavMenuClose, navigate]);

  const handleQuickEntryOpen = useCallback(() => {
    setSpeedDialOpen(false);
    setQuickEntryOpen(true);
  }, []);

  const handleQuickEntryClose = useCallback(() => {
    setQuickEntryOpen(false);
  }, []);

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
      <AppBar 
        position="sticky" 
        sx={{ 
          bgcolor: 'rgba(15, 104, 70, 0.85)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 0,
          boxShadow: 'none',
        }}
      >
        <Toolbar 
          sx={{ 
            position: 'relative',
            display: 'flex',
            justifyContent: { xs: 'space-between', md: 'flex-start' },
            gap: { xs: 1, sm: 2 },
            minHeight: { xs: 56, sm: 64 },
            px: { xs: 1.5, sm: 2, md: 3 },
          }}
        >
          {/* Mobile: Menu hamburger (esquerda) */}
          <Box sx={{ display: { xs: 'flex', md: 'none' }, flexShrink: 0 }}>
            <IconButton 
              edge="start"
              color="inherit" 
              onClick={handleNavMenuOpen}
              sx={{
                minWidth: 44,
                minHeight: 44,
              }}
            >
              <MenuIcon />
            </IconButton>
            <Menu anchorEl={navMenuEl} open={Boolean(navMenuEl)} onClose={handleNavMenuClose}>
              <MenuItem onClick={() => handleNavigate('/')}>Pedidos</MenuItem>
              {!isEntregador && (
                <>
                  <MenuItem onClick={() => handleNavigate('/vendas')}>Vendas</MenuItem>
                  <MenuItem onClick={() => handleNavigate('/clientes')}>Clientes</MenuItem>
                  <MenuItem onClick={() => handleNavigate('/fontes-pedido')}>Fontes</MenuItem>
                  <MenuItem onClick={() => handleNavigate('/integracoes/nuvemshop')}>Nuvemshop</MenuItem>
                </>
              )}
              <MenuItem onClick={() => handleNavigate('/rota-entrega')}>Rota</MenuItem>
              <MenuItem onClick={() => handleNavigate('/configuracoes')}>
                <Settings sx={{ mr: 1, fontSize: 20, color: 'text.secondary' }} />
                Configurações
              </MenuItem>
            </Menu>
          </Box>

          {/* Logo: Centralizado no mobile, normal no desktop */}
          <Box 
            sx={{ 
              display: { xs: 'flex', md: 'flex' },
              alignItems: 'center',
              gap: { xs: 1, sm: 1.5 },
              position: { xs: 'absolute', md: 'static' },
              left: { xs: '50%', md: 'auto' },
              transform: { xs: 'translateX(-50%)', md: 'none' },
              minWidth: 0,
              flexShrink: 0,
            }}
          >
            <LocalFlorist sx={{ fontSize: { xs: 20, sm: 24 } }} />
            <Typography
              variant="h6"
              component="div"
              sx={{
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                fontWeight: 'bold',
                fontSize: { xs: '1rem', sm: '1.25rem' },
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
              ml: 3,
            }}
          >
            <Button color="inherit" onClick={() => handleNavigate('/')} sx={{ textTransform: 'none' }}>
              Pedidos
            </Button>
            {!isEntregador && (
              <>
                <Button color="inherit" onClick={() => handleNavigate('/vendas')} sx={{ textTransform: 'none' }}>
                  Vendas
                </Button>
                <Button color="inherit" onClick={() => handleNavigate('/clientes')} sx={{ textTransform: 'none' }}>
                  Clientes
                </Button>
                <Button color="inherit" onClick={() => handleNavigate('/fontes-pedido')} sx={{ textTransform: 'none' }}>
                  Fontes
                </Button>
                <Button color="inherit" onClick={() => handleNavigate('/integracoes/nuvemshop')} sx={{ textTransform: 'none' }}>
                  Nuvemshop
                </Button>
              </>
            )}
            <Button color="inherit" onClick={() => handleNavigate('/rota-entrega')} sx={{ textTransform: 'none' }}>
              Rota
            </Button>
            <Tooltip title="Configurações">
              <IconButton color="inherit" onClick={() => handleNavigate('/configuracoes')}>
                <Settings />
              </IconButton>
            </Tooltip>
          </Box>

          {/* Seção Direita: Notificações + Avatar */}
          {authenticated && (
            <Stack 
              direction="row" 
              spacing={1} 
              alignItems="center" 
              sx={{ flexShrink: 0 }}
            >
              {/* Status Online/Offline (apenas desktop) */}
              <Chip
                icon={isOnline ? <CloudDone /> : <CloudOff />}
                label={isOnline ? 'Online' : 'Offline'}
                color={isOnline ? 'success' : 'default'}
                size="small"
                sx={{ display: { xs: 'none', sm: 'flex' } }}
              />
              {/* Notificações */}
              <Tooltip title={outboxCount > 0 ? `${outboxCount} item(ns) pendente(s) de sincronização` : 'Sem pendências'}>
                <IconButton 
                  color="inherit"
                  sx={{ 
                    minWidth: 44,
                    minHeight: 44,
                  }}
                >
                  <Badge badgeContent={outboxCount || 0} color={outboxCount > 0 ? 'warning' : 'default'}>
                    <NotificationsNone />
                  </Badge>
                </IconButton>
              </Tooltip>
              
              {/* Divider (apenas desktop) */}
              <Divider 
                flexItem 
                orientation="vertical" 
                sx={{ 
                  borderColor: 'rgba(255,255,255,0.2)',
                  display: { xs: 'none', sm: 'block' },
                }} 
              />
              
              {/* Avatar do Usuário */}
              <IconButton 
                color="inherit" 
                onClick={handleMenuOpen} 
                sx={{ 
                  minWidth: 44,
                  minHeight: 44,
                }}
              >
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
            </Stack>
          )}
        </Toolbar>
      </AppBar>
      {/* SpeedDial com opções de criar pedido */}
      {authenticated && isOrdersPage && (
        <SpeedDial
          ariaLabel="Opções de criação"
          sx={{ 
            position: 'fixed', 
            bottom: 24, 
            right: 24,
            '& .MuiFab-primary': {
              bgcolor: 'primary.main',
              '&:hover': {
                bgcolor: 'primary.dark',
              },
            },
          }}
          icon={<SpeedDialIcon openIcon={<AddIcon />} />}
          open={speedDialOpen}
          onOpen={() => setSpeedDialOpen(true)}
          onClose={() => setSpeedDialOpen(false)}
        >
          <SpeedDialAction
            icon={<AddShoppingCartIcon />}
            tooltipTitle="Novo Pedido"
            tooltipOpen
            onClick={handleCreateOrder}
            sx={{
              '& .MuiSpeedDialAction-staticTooltipLabel': {
                whiteSpace: 'nowrap',
              },
            }}
          />
          <SpeedDialAction
            icon={<BoltIcon />}
            tooltipTitle="Entrada Rápida"
            tooltipOpen
            onClick={handleQuickEntryOpen}
            sx={{
              '& .MuiFab-primary': {
                bgcolor: 'warning.main',
                color: 'warning.contrastText',
                '&:hover': {
                  bgcolor: 'warning.dark',
                },
              },
              '& .MuiSpeedDialAction-staticTooltipLabel': {
                whiteSpace: 'nowrap',
              },
            }}
          />
        </SpeedDial>
      )}

      {/* Push Notification Manager (invisível, registra subscription) */}
      {authenticated && <NotificationManager />}

      {/* Modal de Entrada Rápida */}
      <QuickEntryModal open={quickEntryOpen} onClose={handleQuickEntryClose} />
      <Container
        maxWidth={isOrderWizardPage ? false : 'xl'}
        sx={{
          flex: 1,
          py: { xs: 2, sm: 3 },
          px: isOrderWizardPage ? { xs: 1.5, sm: 2, md: 4 } : { xs: 2, sm: 3 },
          bgcolor: isOrderWizardPage ? 'grey.100' : undefined,
          // Garantir que conteúdo não fique escondido atrás do FAB
          pb: { xs: 10, sm: 12 },
        }}
      >
        {children}
      </Container>
    </Box>
  );
}

