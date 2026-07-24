import { useLocation, useNavigate } from 'react-router-dom';
import {
  BottomNavigation,
  BottomNavigationAction,
  Paper,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import ShoppingCart from '@mui/icons-material/ShoppingCart';
import People from '@mui/icons-material/People';
import PointOfSale from '@mui/icons-material/PointOfSale';
import Route from '@mui/icons-material/Route';
import Groups from '@mui/icons-material/Groups';
import LocalShipping from '@mui/icons-material/LocalShipping';
import AccountBalance from '@mui/icons-material/AccountBalance';

interface BottomNavProps {
  role: string;
}

const ADMIN_ITEMS = [
  { label: 'Pedidos', value: '/', icon: <ShoppingCart /> },
  { label: 'Clientes', value: '/clientes', icon: <People /> },
  { label: 'Vendas', value: '/vendas', icon: <PointOfSale /> },
  { label: 'Rota', value: '/rota-entrega', icon: <Route /> },
  { label: 'Equipe', value: '/equipe', icon: <Groups /> },
];

const ENTREGADOR_ITEMS = [
  { label: 'Entregas', value: '/entregador/mapa', icon: <LocalShipping /> },
  { label: 'Recebíveis', value: '/recebiveis', icon: <AccountBalance /> },
  { label: 'Pedidos', value: '/', icon: <ShoppingCart /> },
];

export function BottomNav({ role }: BottomNavProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const location = useLocation();
  const navigate = useNavigate();

  if (!isMobile) return null;

  const items = role === 'entregador' ? ENTREGADOR_ITEMS : ADMIN_ITEMS;

  const matchIndex = items.findIndex((item) => {
    if (item.value === '/') return location.pathname === '/';
    return location.pathname === item.value || location.pathname.startsWith(`${item.value}/`);
  });

  return (
    <Paper
      elevation={3}
      sx={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 1200,
        borderTop: '1px solid',
        borderColor: 'divider',
      }}
    >
      <BottomNavigation
        showLabels
        value={matchIndex >= 0 ? matchIndex : 0}
        onChange={(_e, newValue) => {
          navigate(items[newValue].value);
        }}
        sx={{
          height: 56,
          '& .MuiBottomNavigationAction-root': {
            minWidth: 0,
            py: 1,
          },
        }}
      >
        {items.map((item) => (
          <BottomNavigationAction
            key={item.value}
            label={item.label}
            icon={item.icon}
          />
        ))}
      </BottomNavigation>
    </Paper>
  );
}
