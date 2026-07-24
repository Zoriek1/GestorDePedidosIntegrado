import React, { ReactNode, useCallback, useState } from 'react';
import { useNavigate, useLocation, NavLink } from 'react-router-dom';
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
  Avatar,
} from '@mui/material';
import {
  Logout,
  Menu as MenuIcon,
  NotificationsNone,
  Add as AddIcon,
  Bolt as BoltIcon,
  AddShoppingCart as AddShoppingCartIcon,
  LocalShipping as LocalShippingIcon,
  Settings,
  LightMode,
  DarkMode,
  Brightness7 as AutoIcon,
} from '@mui/icons-material';

import { useAuth } from '../features/auth/authStore';
import { useThemeMode } from '../app/useThemeMode';
import { NotificationManager } from '../features/notifications/NotificationManager';
import { useOffline } from '../lib/offline/useOffline';
import { QuickEntryModal } from '../features/pedidos/components/QuickEntryModal';
import { BrandLogo } from './BrandLogo';
import { BottomNav } from './BottomNav';
import { BRAND } from '../app/theme';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isJwtUser, getCredentials, getUser, logout: handleLogout } = useAuth();
  const { isOnline, outboxCount } = useOffline();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [navMenuEl, setNavMenuEl] = React.useState<null | HTMLElement>(null);
  const [quickEntryOpen, setQuickEntryOpen] = useState(false);
  const [speedDialOpen, setSpeedDialOpen] = useState(false);

  // Full width para páginas de wizard de pedido
  const isOrderWizardPage =
    location.pathname === '/pedidos/novo' ||
    (location.pathname.startsWith('/pedidos/') && location.pathname.endsWith('/editar'));

  // Mostrar botão flutuante apenas na página de pedidos
  const isOrdersPage = location.pathname === '/';

  const authenticated = isAuthenticated();
  const { mode: themeMode, resolvedMode, setMode: setThemeMode } = useThemeMode();
  const currentUser = authenticated ? getUser() : null;
  const credentials = authenticated ? getCredentials() : null;
  const username = currentUser?.name ?? currentUser?.email ?? credentials?.username;
  const userRole = currentUser?.role ?? credentials?.role ?? 'admin';
  const isEntregador = userRole === 'entregador';
  const isAdmin = userRole === 'admin';
  const isVendedor = userRole === 'vendedor';
  const jwtUser = isJwtUser();
  // Leads é opt-in por loja. Sessões legadas (Basic Auth, sem payload de loja)
  // mantêm o menu visível — nesses casos só existe a loja default.
  const canViewLeads = !isEntregador && (currentUser?.leads_enabled ?? !jwtUser);
  const canViewEquipe = isAdmin || isVendedor;

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
  const navButtonSx = (active: boolean) => ({
    color: active ? BRAND.gold : BRAND.textNeutral,
    fontWeight: active ? 500 : 400,
    fontSize: 14,
    fontFamily: '"Jost", "Inter", sans-serif',
    textTransform: 'none' as const,
    px: 1,
    py: 0.5,
    minWidth: 0,
    minHeight: 32,
    borderRadius: 0,
    position: 'relative' as const,
    '&::after': active
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
              <MenuItem
                component={NavLink}
                to="/"
                end
                onClick={handleNavMenuClose}
                sx={{ color: isActive('/') ? BRAND.gold : 'inherit' }}
              >
                Pedidos
              </MenuItem>
              {!isEntregador && (
                <MenuItem
                  component={NavLink}
                  to="/clientes"
                  onClick={handleNavMenuClose}
                  sx={{ color: isActive('/clientes') ? BRAND.gold : 'inherit' }}
                >
                  Clientes
                </MenuItem>
              )}
              {!isEntregador && (
                <MenuItem
                  component={NavLink}
                  to="/vendas"
                  onClick={handleNavMenuClose}
                  sx={{ color: isActive('/vendas') ? BRAND.gold : 'inherit' }}
                >
                  Vendas
                </MenuItem>
              )}
              {canViewLeads && (
                <MenuItem
                  component={NavLink}
                  to="/leads"
                  onClick={handleNavMenuClose}
                  sx={{ color: isActive('/leads') ? BRAND.gold : 'inherit' }}
                >
                  Leads UTM
                </MenuItem>
              )}
              <MenuItem
                component={NavLink}
                to={routePath}
                onClick={handleNavMenuClose}
                sx={{ color: isActive(routePath) ? BRAND.gold : 'inherit' }}
              >
                {routeLabel}
              </MenuItem>
              {canViewEquipe && (
                <MenuItem
                  component={NavLink}
                  to="/equipe"
                  onClick={handleNavMenuClose}
                  sx={{ color: isActive('/equipe') ? BRAND.gold : 'inherit' }}
                >
                  Equipe
                </MenuItem>
              )}
              {isEntregador && (
                <MenuItem
                  component={NavLink}
                  to="/recebiveis"
                  onClick={handleNavMenuClose}
                  sx={{ color: isActive('/recebiveis') ? BRAND.gold : 'inherit' }}
                >
                  Recebíveis
                </MenuItem>
              )}
              <Divider sx={{ borderColor: BRAND.goldBorder, my: 0.5 }} />
              <MenuItem
                component={NavLink}
                to="/configuracoes"
                onClick={handleNavMenuClose}
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
            <NavLink to="/" end>{({ isActive }) => (
              <Button disableRipple sx={navButtonSx(isActive)}>Pedidos</Button>
            )}</NavLink>
            {!isEntregador && (
              <NavLink to="/clientes">{({ isActive }) => (
                <Button disableRipple sx={navButtonSx(isActive)}>Clientes</Button>
              )}</NavLink>
            )}
            {!isEntregador && (
              <>
                <NavLink to="/vendas">{({ isActive }) => (
                  <Button disableRipple sx={navButtonSx(isActive)}>Vendas</Button>
                )}</NavLink>
                {canViewLeads && (
                  <NavLink to="/leads">{({ isActive }) => (
                    <Button disableRipple sx={navButtonSx(isActive)}>Leads</Button>
                  )}</NavLink>
                )}
              </>
            )}
            <NavLink to={routePath}>{({ isActive }) => (
              <Button disableRipple sx={navButtonSx(isActive)}>{routeLabel}</Button>
            )}</NavLink>
            {canViewEquipe && (
              <NavLink to="/equipe">{({ isActive }) => (
                <Button disableRipple sx={navButtonSx(isActive)}>Equipe</Button>
              )}</NavLink>
            )}
            {isEntregador && (
              <NavLink to="/recebiveis">{({ isActive }) => (
                <Button disableRipple sx={navButtonSx(isActive)}>Recebíveis</Button>
              )}</NavLink>
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
                <Avatar sx={{ width: 34, height: 34, bgcolor: BRAND.gold, color: BRAND.green, fontSize: 14, fontWeight: 600 }}>
                  {username?.[0]?.toUpperCase() || '?'}
                </Avatar>
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
                  onClick={() => {
                    const next = themeMode === 'light' ? 'dark' : themeMode === 'dark' ? 'system' : 'light';
                    setThemeMode(next);
                  }}
                  sx={{ color: BRAND.textNeutral, '&:hover': { color: BRAND.gold, bgcolor: 'rgba(212, 175, 122, 0.06)' } }}
                >
                  {resolvedMode === 'dark' ? (
                    <DarkMode sx={{ mr: 1, fontSize: 18 }} />
                  ) : themeMode === 'system' ? (
                    <AutoIcon sx={{ mr: 1, fontSize: 18 }} />
                  ) : (
                    <LightMode sx={{ mr: 1, fontSize: 18 }} />
                  )}
                  {themeMode === 'light' ? 'Claro' : themeMode === 'dark' ? 'Escuro' : 'Sistema'}
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
          onClick={() => navigate('/rota-entrega', { state: { pickup: true } })}
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

      {/* Push Notification Manager (invisível, registra subscription) */}
      {authenticated && <NotificationManager />}

      {/* Modal de Entrada Rápida */}
      <QuickEntryModal open={quickEntryOpen} onClose={handleQuickEntryClose} />

      {authenticated && <BottomNav role={userRole} />}

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
