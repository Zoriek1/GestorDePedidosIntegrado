import { Box, Chip, Grid, useMediaQuery, useTheme } from '@mui/material';
import ListAltIcon from '@mui/icons-material/ListAlt';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import BuildIcon from '@mui/icons-material/Build';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { StatsCard } from '../../../components/uiverse/StatsCard/StatsCard';
import { SEMANTIC } from '../../../app/theme';

interface OrdersKPIGridProps {
  stats?: {
    total: number;
    agendados: number;
    producao: number;
    prontos: number;
    emRota: number;
    atrasados: number;
  };
  activeStatus?: string;
  onFilterByStatus?: (status: string) => void;
}

const STATUS_MAP = [
  { key: 'total', filter: '', icon: <ListAltIcon fontSize="inherit" /> },
  { key: 'agendados', filter: 'agendado', icon: <AccessTimeIcon fontSize="inherit" /> },
  { key: 'producao', filter: 'em_producao', icon: <BuildIcon fontSize="inherit" /> },
  { key: 'prontos', filter: 'pronto_entrega', icon: <CheckCircleIcon fontSize="inherit" /> },
  { key: 'emRota', filter: 'em_rota', icon: <LocalShippingIcon fontSize="inherit" /> },
  { key: 'atrasados', filter: '', icon: <WarningAmberIcon fontSize="inherit" /> },
] as const;

export function OrdersKPIGrid({ stats, activeStatus, onFilterByStatus }: OrdersKPIGridProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  if (!stats) return null;

  const cards = [
    {
      title: 'Total',
      value: stats.total,
      icon: <ListAltIcon fontSize="inherit" />,
      iconBg: SEMANTIC.iconBgBlue,
      iconColor: SEMANTIC.info,
    },
    {
      title: 'Agendados',
      value: stats.agendados,
      icon: <AccessTimeIcon fontSize="inherit" />,
      iconBg: SEMANTIC.iconBgGray,
      iconColor: 'text.secondary',
    },
    {
      title: 'Produção',
      value: stats.producao,
      icon: <BuildIcon fontSize="inherit" />,
      iconBg: SEMANTIC.iconBgYellow,
      iconColor: 'warning.main',
    },
    {
      title: 'Prontos',
      value: stats.prontos,
      icon: <CheckCircleIcon fontSize="inherit" />,
      iconBg: SEMANTIC.iconBgGreen,
      iconColor: SEMANTIC.success,
    },
    {
      title: 'Em rota',
      value: stats.emRota,
      icon: <LocalShippingIcon fontSize="inherit" />,
      iconBg: SEMANTIC.iconBgPurple,
      iconColor: SEMANTIC.purple,
    },
    {
      title: 'Atrasados',
      value: stats.atrasados,
      icon: <WarningAmberIcon fontSize="inherit" />,
      iconBg: SEMANTIC.iconBgRed,
      iconColor: SEMANTIC.error,
    },
  ];

  const chipValues = [
    { label: 'Total', count: stats.total, filter: '' },
    { label: 'Agendados', count: stats.agendados, filter: 'agendado' },
    { label: 'Produção', count: stats.producao, filter: 'em_producao' },
    { label: 'Prontos', count: stats.prontos, filter: 'pronto_entrega' },
    { label: 'Em rota', count: stats.emRota, filter: 'em_rota' },
    { label: 'Atrasados', count: stats.atrasados, filter: '' },
  ];

  if (isMobile) {
    return (
      <Box
        sx={{
          display: 'flex',
          overflowX: 'auto',
          gap: 1,
          flexWrap: 'nowrap',
          pb: 1,
          mb: 3,
          scrollbarWidth: 'none',
          '&::-webkit-scrollbar': { display: 'none' },
        }}
      >
        {chipValues.map((chip) => {
          const isActive = chip.filter === (activeStatus ?? '');
          return (
            <Chip
              key={chip.label}
              icon={STATUS_MAP.find((s) => s.key.toLowerCase().includes(chip.label.toLowerCase().split(' ')[0].toLowerCase()))?.icon ?? undefined}
              label={`${chip.label} ${chip.count}`}
              onClick={onFilterByStatus ? () => onFilterByStatus(chip.filter) : undefined}
              variant={isActive ? 'filled' : 'outlined'}
              color={isActive ? 'primary' : 'default'}
              sx={{ flexShrink: 0, fontWeight: isActive ? 600 : 400 }}
            />
          );
        })}
      </Box>
    );
  }

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
