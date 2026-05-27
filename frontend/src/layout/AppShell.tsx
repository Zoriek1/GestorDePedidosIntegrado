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
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Fab,
} from '@mui/material';
import {
  Logout,
  Person,
  Menu as MenuIcon,
  NotificationsNone,
  Add as AddIcon,
  Bolt as BoltIcon,
  AddShoppingCart as AddShoppingCartIcon,
  LocalShipping as LocalShippingIcon,
  Settings,
} from '@mui/icons-material';

import { useAuth } from '../features/auth/authStore';
import { NotificationManager } from '../features/notifications/NotificationManager';
import { useOffline } from '../lib/offline/useOffline';
import { QuickEntryModal } from '../features/pedidos/components/QuickEntryModal';
import { AssignDeliveryDialog } from '../features/entregas/AssignDeliveryDialog';
import { BrandLogo } from './BrandLogo';

interface AppShellProps {
  children: ReactNode;
}

const BRAND = {
  green: '#143d28',
  greenMuted: '#0a2818',
  gold: '#d4af7a',
  goldMuted: 'rgba(212, 175, 122, 0.5)',
  goldBorder: 'rgba(212, 175, 122, 0.18)',
  textNeutral: '#d4d4cc',
  textBright: '#f5f1e8',
  onlineBg: 'rgba(151, 196, 89, 0.12)',
  onlineText: '#b3d77a',
  onlineDot: '#97c459',
  offlineBg: 'rgba(255, 255, 255, 0.08)',
} as const;

export function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isJwtUser, getCredentials, getUser, logout: handleLogout } = useAuth();
  const { isOnline, outboxCount } = useOffline();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [navMenuEl, setNavMenuEl] = React.useState<null | HTMLElement>(null);
  const [quickEntryOpen, setQuickEntryOpen] = useState(false);
  const [speedDialOpen, setSpeedDialOpen] = useState(false);
  const [assignDeliveryOpen, setAssignDeliveryOpen] = useState(false);

  // Full width para páginas de wizard de pedido
  const isOrderWizardPage =
    location.pathname === '/pedidos/novo' ||
    (location.pathname.startsWith('/pedidos/') && location.pathname.endsWith('/editar'));

  // Mostrar botão flutuante apenas na página de pedidos
  const isOrdersPage = location.pathname === '/';

  const authenticated = isAuthenticated();
  const currentUser = authenticated ? getUser() : null;
  const credentials = authenticated ? getCredentials() : null;
  const username = currentUser?.name ?? currentUser?.email ?? credentials?.username;
  const userRole = currentUser?.role ?? credentials?.role ?? 'admin';
  const isEntregador = userRole === 'entregador';
  const isAdmin = userRole === 'admin';
  const isVendedor = userRole === 'vendedor';
  const jwtUser = isJwtUser();
  const canViewLedger = jwtUser && (isAdmin || isVendedor || isEntregador);
  const ledgerLabel = isAdmin
    ? 'Funcionários'
    : isEntregador
      ? 'Recebíveis Hoje'
      : 'Recebíveis';

  const routePath = isEntregador ? '/entregador/mapa' : '/rota-entrega';
  const routeLabel = isEntregador ? 'Minhas entregas' : 'Rota';

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };
  const handleMenuClose = () => setAnchorEl(null);
  const handleNavMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setNavMenuEl(event.currentTarget);
  };
  const handleNavMenuClose = useCallback(() => setNavMenuEl(null), []);

  const handleCreateOrder = useCallback(() => {
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.removeItem('puf_pedido_draft_v2');
        window.localStorage.removeItem('puf_pedido_step_v2');
      } catch {
        /* ignorar */
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
  const handleQuickEntryClose = useCallback(() => setQuickEntryOpen(false), []);

  const handleNavigate = (path: string) => {
    navigate(path);
    handleNavMenuClose();
  };

  const handleLogoutClick = () => {
    handleLogout();
    handleMenuClose();
    navigate('/login', { replace: true });
  };

  const handleSettingsClick = () => {
    handleMenuClose();
    navigate('/configuracoes');
  };

  // Estilo dos botões de navegação desktop (aba ativa em dourado com sublinhado)
  const navButtonSx = (path: string) => ({
    color: isActive(path) ? BRAND.gold : BRAND.textNeutral,
    fontWeight: isActive(path) ? 500 : 400,
    fontSize: 14,
    fontFamily: '"Jost", "Inter", sans-serif',
    textTransform: 'none' as const,
    px: 1,
    py: 0.5,
    minWidth: 0,
    minHeight: 32,
    borderRadius: 0,
    position: 'relative' as const,
    '&::after': isActive(path)
      ? {
          content: '""',
          position: 'absolute',
          left: 8,
          right: 8,
          bottom: -2,
          height: '1.5px',
          backgroundColor: BRAND.gold,
        }
      : undefined,
    '&:hover': {
      backgroundColor: 'transparent',
      color: BRAND.gold,
    },
  });

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar
        position="sticky"
        sx={{
          bgcolor: BRAND.green,
          borderBottom: `0.5px solid ${BRAND.goldBorder}`,
          borderRadius: 0,
          boxShadow: 'none',
          backgroundImage: 'none',
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
              aria-label="Abrir menu de navegação"
              onClick={handleNavMenuOpen}
              sx={{
                color: BRAND.textNeutral,
                minWidth: 44,
                minHeight: 44,
              }}
            >
              <MenuIcon />
            </IconButton>
            <Menu
              anchorEl={navMenuEl}
              open={Boolean(navMenuEl)}
              onClose={handleNavMenuClose}
              slotProps={{
                paper: {
                  sx: {
                    bgcolor: BRAND.green,
                    color: BRAND.textNeutral,
                    border: `1px solid ${BRAND.goldBorder}`,
                  },
                },
              }}
            >
              <MenuItem onClick={() => handleNavigate('/')} sx={{ color: isActive('/') ? BRAND.gold : 'inherit' }}>
                Pedidos
              </MenuItem>
              {!isEntregador && (
                <MenuItem onClick={() => handleNavigate('/vendas')} sx={{ color: isActive('/vendas') ? BRAND.gold : 'inherit' }}>
                  Vendas
                </MenuItem>
              )}
              {!isEntregador && (
                <MenuItem onClick={() => handleNavigate('/leads')} sx={{ color: isActive('/leads') ? BRAND.gold : 'inherit' }}>
                  Leads UTM
                </MenuItem>
              )}
              <MenuItem onClick={() => handleNavigate(routePath)} sx={{ color: isActive(routePath) ? BRAND.gold : 'inherit' }}>
                {routeLabel}
              </MenuItem>
              {canViewLedger && (
                <MenuItem onClick={() => handleNavigate('/recebiveis')} sx={{ color: isActive('/recebiveis') ? BRAND.gold : 'inherit' }}>
                  {ledgerLabel}
                </MenuItem>
              )}
              <Divider sx={{ borderColor: BRAND.goldBorder, my: 0.5 }} />
              <MenuItem
                onClick={() => handleNavigate('/configuracoes')}
                sx={{ color: isActive('/configuracoes') ? BRAND.gold : 'inherit' }}
              >
                <Settings sx={{ mr: 1, fontSize: 18 }} />
                Configurações
              </MenuItem>
            </Menu>
          </Box>

          {/* Logo + Wordmark — esquerda no desktop, wordmark serifa no mobile */}
          <Box
            onClick={() => navigate('/')}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              cursor: 'pointer',
              minWidth: 0,
              flexShrink: 1,
            }}
            role="button"
            aria-label="Ir para a página inicial"
          >
            <BrandLogo
              size={34}
              color={BRAND.gold}
              sx={{ display: { xs: 'none', sm: 'block' } }}
            />
            {/* Desktop: wordmark CAPS em Jost */}
            <Typography
              component="span"
              sx={{
                fontFamily: '"Jost", "Inter", sans-serif',
                fontWeight: 500,
                fontSize: 14,
                letterSpacing: '2.2px',
                textTransform: 'uppercase',
                color: BRAND.textBright,
                whiteSpace: 'nowrap',
                display: { xs: 'none', sm: 'inline' },
              }}
            >
              PLANTE UMA FLOR
            </Typography>
            {/* Mobile: wordmark em Fraunces serifa */}
            <Typography
              component="span"
              sx={{
                fontFamily: '"Fraunces", Georgia, serif',
                fontWeight: 500,
                fontSize: 18,
                letterSpacing: 'normal',
                textTransform: 'none',
                color: BRAND.textBright,
                whiteSpace: 'nowrap',
                display: { xs: 'inline', sm: 'none' },
              }}
            >
              Plante Uma Flor
            </Typography>
          </Box>

          {/* Navegação central (desktop) */}
          <Box
            sx={{
              flex: 1,
              display: { xs: 'none', md: 'flex' },
              justifyContent: 'center',
              alignItems: 'center',
              gap: '22px',
              ml: 4,
            }}
          >
            <Button disableRipple onClick={() => handleNavigate('/')} sx={navButtonSx('/')}>
              Pedidos
            </Button>
            {!isEntregador && (
              <>
                <Button disableRipple onClick={() => handleNavigate('/vendas')} sx={navButtonSx('/vendas')}>
                  Vendas
                </Button>
                <Button disableRipple onClick={() => handleNavigate('/leads')} sx={navButtonSx('/leads')}>
                  Leads
                </Button>
              </>
            )}
            <Button disableRipple onClick={() => handleNavigate(routePath)} sx={navButtonSx(routePath)}>
              {routeLabel}
            </Button>
            {canViewLedger && (
              <Button disableRipple onClick={() => handleNavigate('/recebiveis')} sx={navButtonSx('/recebiveis')}>
                {ledgerLabel}
              </Button>
            )}
          </Box>

          {/* Seção Direita: Online/Offline + Notificações + Avatar */}
          {authenticated && (
            <Stack
              direction="row"
              spacing="14px"
              alignItems="center"
              sx={{ flexShrink: 0, ml: 'auto' }}
            >
              {/* Pílula Online/Offline */}
              <Box
                sx={{
                  display: { xs: 'none', sm: 'inline-flex' },
                  alignItems: 'center',
                  gap: '6px',
                  px: '10px',
                  py: '4px',
                  borderRadius: '99px',
                  fontFamily: '"Jost", sans-serif',
                  fontSize: 11,
                  fontWeight: 500,
                  bgcolor: isOnline ? BRAND.onlineBg : BRAND.offlineBg,
                  color: isOnline ? BRAND.onlineText : BRAND.textNeutral,
                }}
              >
                <Box
                  sx={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    bgcolor: isOnline ? BRAND.onlineDot : BRAND.textNeutral,
                    opacity: isOnline ? 1 : 0.6,
                  }}
                />
                {isOnline ? 'Online' : 'Offline'}
              </Box>

              {/* Notificações (sino + badge de outbox) */}
              <Tooltip
                title={
                  outboxCount > 0
                    ? `${outboxCount} item(ns) pendente(s) de sincronização`
                    : 'Sem pendências'
                }
              >
                <IconButton
                  aria-label="Notificações"
                  sx={{
                    color: BRAND.textNeutral,
                    minWidth: 44,
                    minHeight: 44,
                    '&:hover': { color: BRAND.gold },
                  }}
                >
                  <Badge
                    badgeContent={outboxCount || 0}
                    color={outboxCount > 0 ? 'warning' : 'default'}
                  >
                    <NotificationsNone sx={{ fontSize: 20 }} />
                  </Badge>
                </IconButton>
              </Tooltip>

              {/* Divider (apenas desktop) */}
              <Divider
                flexItem
                orientation="vertical"
                sx={{
                  borderColor: BRAND.goldBorder,
                  display: { xs: 'none', sm: 'block' },
                }}
              />

              {/* Avatar do Usuário */}
              <IconButton
                aria-label="Abrir menu do perfil"
                onClick={handleMenuOpen}
                sx={{
                  color: BRAND.textNeutral,
                  minWidth: 44,
                  minHeight: 44,
                  '&:hover': { color: BRAND.gold },
                }}
              >
                <Person sx={{ fontSize: 22 }} />
              </IconButton>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleMenuClose}
                slotProps={{
                  paper: {
                    sx: {
                      bgcolor: BRAND.green,
                      color: BRAND.textNeutral,
                      border: `1px solid ${BRAND.goldBorder}`,
                      minWidth: 220,
                    },
                  },
                }}
              >
                {username && (
                  <MenuItem disabled sx={{ opacity: '1 !important' }}>
                    <Typography
                      variant="body2"
                      sx={{ color: BRAND.textBright, fontWeight: 500 }}
                    >
                      {username}
                    </Typography>
                  </MenuItem>
                )}
                <Divider sx={{ borderColor: BRAND.goldBorder, my: 0.5 }} />
                <MenuItem
                  onClick={handleSettingsClick}
                  sx={{ color: BRAND.textNeutral, '&:hover': { color: BRAND.gold, bgcolor: 'rgba(212, 175, 122, 0.06)' } }}
                >
                  <Settings sx={{ mr: 1, fontSize: 18 }} />
                  Configurações
                </MenuItem>
                <MenuItem
                  disabled
                  sx={{
                    opacity: '1 !important',
                    cursor: 'default',
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                    fontSize: 11,
                    color: BRAND.goldMuted,
                    pointerEvents: 'none',
                  }}
                >
                  Versão: {__BUILD_VERSION__}
                </MenuItem>
                <Divider sx={{ borderColor: BRAND.goldBorder, my: 0.5 }} />
                <MenuItem
                  onClick={handleLogoutClick}
                  sx={{ color: BRAND.textNeutral, '&:hover': { color: BRAND.gold, bgcolor: 'rgba(212, 175, 122, 0.06)' } }}
                >
                  <Logout sx={{ mr: 1, fontSize: 18 }} />
                  Sair
                </MenuItem>
              </Menu>
            </Stack>
          )}
        </Toolbar>
      </AppBar>

      {/* FAB principal — entregador vê "Entregar"; demais veem SpeedDial de criação */}
      {authenticated && isOrdersPage && isEntregador && (
        <Fab
          color="primary"
          aria-label="Pegar entregas"
          variant="extended"
          onClick={() => setAssignDeliveryOpen(true)}
          sx={{ position: 'fixed', bottom: 24, right: 24, gap: 1 }}
        >
          <LocalShippingIcon />
          Entregar
        </Fab>
      )}
      {authenticated && isOrdersPage && !isEntregador && (
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
      {authenticated && (
        <AssignDeliveryDialog
          open={assignDeliveryOpen}
          onClose={() => setAssignDeliveryOpen(false)}
        />
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
