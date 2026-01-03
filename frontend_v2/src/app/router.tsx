/**
 * Router configuration
 */

import { createBrowserRouter, RouterProvider, Outlet, Navigate } from 'react-router-dom';
import { RequireAuth } from '../features/auth/RequireAuth';
import { AppShell } from '../layout/AppShell';
import LoginPage from '../features/auth/LoginPage';
import OrdersPage from '../features/pedidos/OrdersPage';
import CustomersPage from '../features/customers/CustomersPage';
import SalesPage from '../features/sales/SalesPage';
import CreateOrderPage from '../features/pedidos/CreateOrderPage';
import OrderDetailsPage from '../features/pedidos/OrderDetailsPage';
import TestOfflinePage from '../features/pedidos/TestOfflinePage';
import OfflineDiagnostics from '../features/offline/OfflineDiagnostics';
import FontesPage from '../features/fontes/FontesPage';
import RoutePage from '../features/rotas/RoutePage';
import EditOrderPage from '../features/pedidos/EditOrderPage';

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
            <CustomersPage />
          </RequireAuth>
        ),
      },
      {
        path: '/vendas',
        element: (
          <RequireAuth>
            <SalesPage />
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
            <RoutePage />
          </RequireAuth>
        ),
      },
      {
        path: '/test-offline',
        element: (
          <RequireAuth>
            {enableOfflineDiagnostics ? <TestOfflinePage /> : <Navigate to="/" replace />}
          </RequireAuth>
        ),
      },
      {
        path: '/offline-diagnostics',
        element: (
          <RequireAuth>
            {enableOfflineDiagnostics ? <OfflineDiagnostics /> : <Navigate to="/" replace />}
          </RequireAuth>
        ),
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}

