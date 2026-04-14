/**
 * Router configuration
 */

import { createBrowserRouter, RouterProvider, Outlet, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { RequireAuth } from '../features/auth/RequireAuth';
import { AppShell } from '../layout/AppShell';
import LoginPage from '../features/auth/LoginPage';
import OrdersPage from '../features/pedidos/OrdersPage';
import CreateOrderPage from '../features/pedidos/CreateOrderPage';
import OrderDetailsPage from '../features/pedidos/OrderDetailsPage';
import FontesPage from '../features/fontes/FontesPage';
import EditOrderPage from '../features/pedidos/EditOrderPage';
import { Loading } from '../components/common/Loading';

const CustomersPage = lazy(() => import('../features/customers/CustomersPage'));
const SalesPage = lazy(() => import('../features/sales/SalesPage'));
const RoutePage = lazy(() => import('../features/rotas/RoutePage'));
const TestOfflinePage = lazy(() => import('../features/pedidos/TestOfflinePage'));
const OfflineDiagnostics = lazy(() => import('../features/offline/OfflineDiagnostics'));
const NuvemshopPage = lazy(() => import('../features/integrations/NuvemshopPage'));
const SettingsPage = lazy(() => import('../features/config/SettingsPage'));
const LeadsPage = lazy(() => import('../features/leads/LeadsPage'));
const LedgerPage = lazy(() => import('../features/ledger/LedgerPage'));
const UserListPage = lazy(() => import('../features/users/components/UserListPage'));

// Componente vazio para rotas do backend que não devem ser processadas pelo React Router
// Essas rotas são processadas pelo backend Flask
function BackendRoute() {
  return null;
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
      {
        path: '/integracoes/nuvemshop',
        element: (
          <RequireAuth>
            <Suspense fallback={<Loading />}>
              <NuvemshopPage />
            </Suspense>
          </RequireAuth>
        ),
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
            <Suspense fallback={<Loading />}>
              <LeadsPage />
            </Suspense>
          </RequireAuth>
        ),
      },
      {
        path: '/recebiveis',
        element: (
          <RequireAuth>
            <Suspense fallback={<Loading />}>
              <LedgerPage />
            </Suspense>
          </RequireAuth>
        ),
      },
      {
        path: '/usuarios',
        element: (
          <RequireAuth>
            <Suspense fallback={<Loading />}>
              <UserListPage />
            </Suspense>
          </RequireAuth>
        ),
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

