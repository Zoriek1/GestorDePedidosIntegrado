import { Grid, Typography, useTheme } from '@mui/material';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import PaidIcon from '@mui/icons-material/Paid';
import ReceiptIcon from '@mui/icons-material/Receipt';
import { StatsCard } from '../../../components/uiverse/StatsCard/StatsCard';
import { SEMANTIC } from '../../../app/theme';

interface SalesKPIs {
  quantidade: number;
  totalVendasBruto: number;
  totalRecebido: number;
  totalEfetivo: number;
  ticketMedioEfetivo: number;
  projecaoFaturamento?: number;
}

interface KPIComparativo {
  quantidade?: number | null;
  totalVendasBruto?: number | null;
  totalRecebido?: number | null;
  totalEfetivo?: number | null;
  ticketMedioEfetivo?: number | null;
  projecaoFaturamento?: number | null;
}

interface SalesKPIGridProps {
  kpis: SalesKPIs;
  comparativo?: KPIComparativo;
  comparativoLabel?: string;
}

export function SalesKPIGrid({ kpis, comparativo, comparativoLabel }: SalesKPIGridProps) {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  const formatMoney = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1).replace('.', ',')}%`;
  };

  const resolveIconBg = (token: { light: string; dark: string }) => isDark ? token.dark : token.light;

  const comparativoHelper = (key: keyof KPIComparativo): string | undefined => {
    if (!comparativoLabel || !comparativo) return undefined;
    const val = comparativo[key];
    if (val === null || val === undefined) return undefined;
    return `${formatPercent(val)} vs. ${comparativoLabel}`;
  };

  const items = [
    {
      key: 'quantidade' as const,
      title: 'Quantidade de Pedidos',
      value: kpis.quantidade,
      icon: <ShoppingCartIcon fontSize="inherit" />,
      iconBg: resolveIconBg(SEMANTIC.iconBgBlue),
      iconColor: SEMANTIC.info,
    },
    {
      key: 'totalVendasBruto' as const,
      title: 'Total de Vendas no Mês',
      value: formatMoney(kpis.totalVendasBruto),
      icon: <AttachMoneyIcon fontSize="inherit" />,
      iconBg: resolveIconBg(SEMANTIC.iconBgGreen),
      iconColor: SEMANTIC.success,
    },
    ...(kpis.projecaoFaturamento !== undefined
      ? [{
          key: 'projecaoFaturamento' as const,
          title: 'Projeção de Faturamento',
          value: formatMoney(kpis.projecaoFaturamento),
          icon: <TrendingUpIcon fontSize="inherit" />,
          iconBg: resolveIconBg(SEMANTIC.iconBgPurple),
          iconColor: SEMANTIC.sky,
        }]
      : []),
    {
      key: 'totalRecebido' as const,
      title: 'Total Recebido',
      value: formatMoney(kpis.totalRecebido),
      icon: <AccountBalanceWalletIcon fontSize="inherit" />,
      iconBg: resolveIconBg(SEMANTIC.iconBgYellow),
      iconColor: SEMANTIC.warning,
    },
    {
      key: 'totalEfetivo' as const,
      title: 'Total Efetivo',
      value: formatMoney(kpis.totalEfetivo),
      icon: <PaidIcon fontSize="inherit" />,
      iconBg: resolveIconBg(SEMANTIC.iconBgPurple),
      iconColor: SEMANTIC.purple,
    },
    {
      key: 'ticketMedioEfetivo' as const,
      title: 'Ticket Médio',
      value: formatMoney(kpis.ticketMedioEfetivo),
      icon: <ReceiptIcon fontSize="inherit" />,
      iconBg: resolveIconBg(SEMANTIC.iconBgGreen),
      iconColor: SEMANTIC.success,
    },
  ];

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {items.map((item, index) => (
        <Grid size={{ xs: 12, sm: 6, md: 3 }} key={item.title}>
          <StatsCard
            title={item.title}
            value={
              <Typography variant="h5" fontWeight="bold" sx={{ color: item.iconColor }}>
                {item.value}
              </Typography>
            }
            helperText={comparativoHelper(item.key)}
            icon={item.icon}
            index={index}
            iconBg={item.iconBg}
            iconColor={item.iconColor}
          />
        </Grid>
      ))}
    </Grid>
  );
}
