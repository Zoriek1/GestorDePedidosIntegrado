import { Grid, Card, CardContent, Typography } from '@mui/material';

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

  const items = [
    { 
      key: 'quantidade',
      title: 'Quantidade de Pedidos', 
      value: kpis.quantidade, 
      color: '#2563eb',
      isCurrency: false,
      isText: false
    },
    { 
      key: 'totalVendasBruto',
      title: 'Total de Vendas no Mês', 
      value: formatMoney(kpis.totalVendasBruto), 
      color: '#16a34a',
      isCurrency: false, // Já formatado como string
      isText: true
    },
    ...(kpis.projecaoFaturamento !== undefined
      ? [{
          key: 'projecaoFaturamento',
          title: 'Projeção de Faturamento',
          value: formatMoney(kpis.projecaoFaturamento),
          color: '#0ea5e9',
          isCurrency: false,
          isText: true
        }]
      : []),
    { 
      key: 'totalRecebido',
      title: 'Total Recebido', 
      value: formatMoney(kpis.totalRecebido), 
      color: '#f59e0b',
      isCurrency: false, // Já formatado como string
      isText: true
    },
    { 
      key: 'totalEfetivo',
      title: 'Total Efetivo', 
      value: formatMoney(kpis.totalEfetivo), 
      color: '#8b5cf6',
      isCurrency: false, // Já formatado como string
      isText: true
    },
    {
      key: 'ticketMedioEfetivo',
      title: 'Ticket Médio',
      value: formatMoney(kpis.ticketMedioEfetivo),
      color: '#22c55e',
      isCurrency: false,
      isText: true
    },
  ];

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {items.map((item) => (
        <Grid size={{ xs: 12, sm: 6, md: 3 }} key={item.title}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                {item.title}
              </Typography>
              <Typography 
                variant="h5" 
                fontWeight="bold" 
                sx={{ color: item.color }}
              >
                {item.isText ? item.value : (item.isCurrency ? formatMoney(item.value as number) : item.value)}
              </Typography>
              {comparativoLabel && comparativo && (
                <Typography
                  variant="caption"
                  sx={{
                    color:
                      comparativo[item.key as keyof KPIComparativo] === null ||
                      comparativo[item.key as keyof KPIComparativo] === undefined
                        ? 'text.secondary'
                        : (comparativo[item.key as keyof KPIComparativo] as number) >= 0
                          ? '#16a34a'
                          : '#dc2626',
                    display: 'block',
                    mt: 0.5,
                  }}
                >
                  {formatPercent(comparativo[item.key as keyof KPIComparativo])} vs. {comparativoLabel}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
