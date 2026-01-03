import { Grid } from '@mui/material';
import ListAltIcon from '@mui/icons-material/ListAlt';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import BuildIcon from '@mui/icons-material/Build';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { StatsCard } from '../../../components/uiverse/StatsCard/StatsCard';

interface OrdersKPIGridProps {
  stats?: {
    total: number;
    agendados: number;
    producao: number;
    prontos: number;
    entregues: number;
    atrasados: number;
  };
}

export function OrdersKPIGrid({ stats }: OrdersKPIGridProps) {
  if (!stats) return null;

  const cards = [
    {
      title: 'Total',
      value: stats.total,
      icon: <ListAltIcon fontSize="inherit" />,
      iconBg: '#e0f2fe',
      iconColor: '#2563eb',
    },
    {
      title: 'Agendados',
      value: stats.agendados,
      icon: <AccessTimeIcon fontSize="inherit" />,
      iconBg: '#f3f4f6',
      iconColor: '#6b7280',
    },
    {
      title: 'Produção',
      value: stats.producao,
      icon: <BuildIcon fontSize="inherit" />,
      iconBg: '#fef9c3',
      iconColor: '#d97706',
    },
    {
      title: 'Prontos',
      value: stats.prontos,
      icon: <CheckCircleIcon fontSize="inherit" />,
      iconBg: '#dcfce7',
      iconColor: '#16a34a',
    },
    {
      title: 'Entregues',
      value: stats.entregues,
      icon: <LocalShippingIcon fontSize="inherit" />,
      iconBg: '#ede9fe',
      iconColor: '#7c3aed',
    },
    {
      title: 'Atrasados',
      value: stats.atrasados,
      icon: <WarningAmberIcon fontSize="inherit" />,
      iconBg: '#fee2e2',
      iconColor: '#dc2626',
    },
  ];

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {cards.map((card, index) => (
        <Grid size={{ xs: 6, sm: 4, md: 2 }} key={card.title}>
          <StatsCard
            title={card.title}
            value={card.value}
            icon={card.icon}
            index={index}
          />
        </Grid>
      ))}
    </Grid>
  );
}


