import { Grid, Card, CardContent, Typography } from '@mui/material';

interface SalesKPIs {
  quantidade: number;
  totalVendasBruto: number;
  totalRecebido: number;
  totalEfetivo: number;
}

interface SalesKPIGridProps {
  kpis: SalesKPIs;
}

export function SalesKPIGrid({ kpis }: SalesKPIGridProps) {
  const formatMoney = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { 
      style: 'currency', 
      currency: 'BRL' 
    }).format(value);
  };

  const items = [
    { 
      title: 'Quantidade de Pedidos', 
      value: kpis.quantidade, 
      color: '#2563eb',
      isCurrency: false 
    },
    { 
      title: 'Total de Vendas no Mês', 
      value: formatMoney(kpis.totalVendasBruto), 
      color: '#16a34a',
      isCurrency: false, // Já formatado
      isText: true
    },
    { 
      title: 'Total Recebido', 
      value: formatMoney(kpis.totalRecebido), 
      color: '#f59e0b',
      isCurrency: false, // Já formatado
      isText: true
    },
    { 
      title: 'Total Efetivo', 
      value: formatMoney(kpis.totalEfetivo), 
      color: '#8b5cf6',
      isCurrency: false, // Já formatado
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
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
