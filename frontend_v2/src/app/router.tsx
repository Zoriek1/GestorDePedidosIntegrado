/**
 * Router configuration
 */

import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom';
import { RequireAuth } from '../features/auth/RequireAuth';
import { AppShell } from '../layout/AppShell';
import LoginPage from '../features/auth/LoginPage';
import OrdersPage from '../features/pedidos/OrdersPage';
import CustomersPage from '../features/customers/CustomersPage';
import CreateOrderPage from '../features/pedidos/CreateOrderPage';
import OrderDetailsPage from '../features/pedidos/OrderDetailsPage';

// Layout route that wraps protected routes with AppShell
function Layout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

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
        path: '/pedidos/novo',
        element: (
          <RequireAuth>
            <CreateOrderPage />
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
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}

