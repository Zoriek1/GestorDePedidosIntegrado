/**
 * Router configuration
 */

import { createBrowserRouter, RouterProvider, Outlet, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { RequireAuth } from '../features/auth/RequireAuth';
import { RequireLeadsEnabled } from '../features/auth/RequireLeadsEnabled';
import { AppShell } from '../layout/AppShell';
import LoginPage from '../features/auth/LoginPage';
import OrdersPage from '../features/pedidos/OrdersPage';
import CreateOrderPage from '../features/pedidos/CreateOrderPage';
import OrderDetailsPage from '../features/pedidos/OrderDetailsPage';
import FontesPage from '../features/fontes/FontesPage';
import EditOrderPage from '../features/pedidos/EditOrderPage';
import { Loading } from '../components/common/Loading';
import { useAuth } from '../features/auth/authStore';

const CustomersPage = lazy(() => import('../features/customers/CustomersPage'));
const SalesPage = lazy(() => import('../features/sales/SalesPage'));
const RoutePage = lazy(() => import('../features/rotas/RoutePage'));
const TestOfflinePage = lazy(() => import('../features/pedidos/TestOfflinePage'));
const OfflineDiagnostics = lazy(() => import('../features/offline/OfflineDiagnostics'));
const SettingsPage = lazy(() => import('../features/config/SettingsPage'));
const LeadsPage = lazy(() => import('../features/leads/LeadsPage'));
const LedgerPage = lazy(() => import('../features/ledger/LedgerPage'));
const EquipePage = lazy(() => import('../features/equipe/EquipePage'));
const MinhasEntregasMapaPage = lazy(() => import('../features/entregas/MinhasEntregasMapaPage'));
const TrackingPage = lazy(() => import('../features/tracking/TrackingPage'));

// Componente vazio para rotas do backend que não devem ser processadas pelo React Router
// Essas rotas são processadas pelo backend Flask
function BackendRoute() {
  return null;
}

// Redirect: admin/vendedor vão para /equipe?tab=recebiveis; entregador vê LedgerPage diretamente
function RecebiveisRedirect() {
  const { getUserRole } = useAuth();
  if (getUserRole() === 'entregador') {
    return (
      <RequireAuth>
        <Suspense fallback={<Loading />}>
          <LedgerPage />
        </Suspense>
      </RequireAuth>
    );
  }
  return <Navigate to="/equipe?tab=recebiveis" replace />;
}

// Layout route that wraps protected routes with AppShell
function Layout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

const enableOfflineDiagnostics =
  import.meta.env.DEV || import.meta.env.VITE_ENABLE_OFFLINE_DIAGNOSTICS === 'true';

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  // Página pública de acompanhamento do pedido pelo cliente (sem login, fora do AppShell).
  {
    path: '/acompanhar/:token',
    element: (
      <Suspense fallback={<Loading />}>
        <TrackingPage />
      </Suspense>
    ),
  },
  // Rotas do Meta Gateway - devem ser processadas pelo backend, não pelo React Router
  // Essas rotas são ignoradas pelo React Router para que o backend Flask as processe
  {
    path: '/capig/*',
    element: <BackendRoute />,
  },
  {
    path: '/meta-gateway/*',
    element: <BackendRoute />,
  },
  {
    element: <Layout />,
    children: [
      {
        path: '/',
        element: (
          <RequireAuth>
            <OrdersPage />
          </RequireAuth>
        ),
      },
      {
        path: '/clientes',
        element: (
          <RequireAuth>
            <Suspense fallback={<Loading />}>
              <CustomersPage />
            </Suspense>
          </RequireAuth>
        ),
      },
      {
        path: '/vendas',
        element: (
          <RequireAuth>
            <Suspense fallback={<Loading />}>
              <SalesPage />
            </Suspense>
          </RequireAuth>
        ),
      },
      {
        path: '/pedidos/novo',
        element: (
          <RequireAuth>
            <CreateOrderPage />
          </RequireAuth>
        ),
      },
      {
        path: '/fontes-pedido',
        element: (
          <RequireAuth>
            <FontesPage />
          </RequireAuth>
        ),
      },
      {
        path: '/pedidos/:id',
        element: (
          <RequireAuth>
            <OrderDetailsPage />
          </RequireAuth>
        ),
      },
      {
        path: '/pedidos/:id/editar',
        element: (
          <RequireAuth>
            <EditOrderPage />
          </RequireAuth>
        ),
      },
      {
        path: '/rota-entrega',
        element: (
          <RequireAuth>
            <Suspense fallback={<Loading />}>
              <RoutePage />
            </Suspense>
          </RequireAuth>
        ),
      },
      // As telas dedicadas de integração foram consolidadas na aba Integrações
      // de /configuracoes. Mantemos o redirect para não quebrar links antigos.
      {
        path: '/integracoes/nuvemshop',
        element: <Navigate to="/configuracoes" replace />,
      },
      {
        path: '/integracoes/bling',
        element: <Navigate to="/configuracoes" replace />,
      },
      {
        path: '/configuracoes',
        element: (
          <RequireAuth>
            <Suspense fallback={<Loading />}>
              <SettingsPage />
            </Suspense>
          </RequireAuth>
        ),
      },
      {
        path: '/leads',
        element: (
          <RequireAuth>
            <RequireLeadsEnabled>
              <Suspense fallback={<Loading />}>
                <LeadsPage />
              </Suspense>
            </RequireLeadsEnabled>
          </RequireAuth>
        ),
      },
      {
        path: '/entregador/mapa',
        element: (
          <RequireAuth>
            <Suspense fallback={<Loading />}>
              <MinhasEntregasMapaPage />
            </Suspense>
          </RequireAuth>
        ),
      },
      {
        path: '/recebiveis',
        element: <RecebiveisRedirect />,
      },
      {
        path: '/equipe',
        element: (
          <RequireAuth>
            <Suspense fallback={<Loading />}>
              <EquipePage />
            </Suspense>
          </RequireAuth>
        ),
      },
      {
        path: '/usuarios',
        element: <Navigate to="/configuracoes" replace />,
      },
      {
        path: '/test-offline',
        element: (
          <RequireAuth>
            {enableOfflineDiagnostics ? (
              <Suspense fallback={<Loading />}>
                <TestOfflinePage />
              </Suspense>
            ) : (
              <Navigate to="/" replace />
            )}
          </RequireAuth>
        ),
      },
      {
        path: '/offline-diagnostics',
        element: (
          <RequireAuth>
            {enableOfflineDiagnostics ? (
              <Suspense fallback={<Loading />}>
                <OfflineDiagnostics />
              </Suspense>
            ) : (
              <Navigate to="/" replace />
            )}
          </RequireAuth>
        ),
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
