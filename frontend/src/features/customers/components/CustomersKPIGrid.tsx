import { Grid, Card, CardContent, Typography } from '@mui/material';
import type { CustomerKPIs } from '../services/ICustomerInsightsService';

interface CustomersKPIGridProps {
  kpis: CustomerKPIs;
}

export function CustomersKPIGrid({ kpis }: CustomersKPIGridProps) {
  const items = [
    { title: 'Novos no mês', value: kpis.novosMes, color: '#2563eb' },
    { title: 'Ticket médio global', value: kpis.ticketMedioGlobal, color: '#16a34a', isCurrency: true },
    { title: 'LTV médio', value: kpis.ltvMedio, color: '#f59e0b', isCurrency: true },
  ];

  const formatValue = (val: number, isCurrency?: boolean) =>
    isCurrency ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val) : val;

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {items.map((item) => (
        <Grid size={{ xs: 12, sm: 6, md: 4 }} key={item.title}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                {item.title}
              </Typography>
              <Typography variant="h5" fontWeight="bold" sx={{ color: item.color }}>
                {formatValue(item.value, item.isCurrency)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

