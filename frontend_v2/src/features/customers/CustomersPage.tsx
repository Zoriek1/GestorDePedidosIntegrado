import { useMemo, useState } from 'react';
import { Box, Typography, Stack, TextField } from '@mui/material';
import { useCustomers, useCustomerOrders, type Customer, type CustomersFilters } from '../../api/endpoints/customers';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { CustomersKPIGrid } from './components/CustomersKPIGrid';
import { CustomersTable } from './components/CustomersTable';
import { CustomerDetailsDrawer } from './components/CustomerDetailsDrawer';
import { CustomersAdvancedFilters } from './components/CustomersAdvancedFilters';
import { CustomerInsightsService } from './services/CustomerInsightsService';

const insights = new CustomerInsightsService();

export default function CustomersPage() {
  const [searchValue, setSearchValue] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [advancedFilters, setAdvancedFilters] = useState<CustomersFilters>({});

  const filters: CustomersFilters = {
    search: searchValue,
    includeStats: true,
    perPage: 100,
    ...advancedFilters,
  };

  const { data, isLoading, error, refetch } = useCustomers(filters);
  const ordersQuery = useCustomerOrders(selectedCustomer?.id, 50);

  const customers = data?.clientes || [];
  const kpis = useMemo(() => insights.computeKPIs(customers), [customers]);
  const vipThreshold = useMemo(() => insights.resolveVipThreshold(customers), [customers]);

  const badgesMap = useMemo(() => {
    const map: Record<number, any[]> = {};
    customers.forEach((c) => {
      map[c.id] = insights.getBadges(c, vipThreshold);
    });
    return map;
  }, [customers, vipThreshold]);

  const handleRowClick = (customer: Customer) => {
    setSelectedCustomer(customer);
  };

  return (
    <Box>
      <Stack direction={{ xs: 'column', md: 'row' }} alignItems={{ xs: 'flex-start', md: 'center' }} justifyContent="space-between" gap={2} mb={2}>
        <Typography variant="h4" component="h1">
          Clientes
        </Typography>
        <TextField
          size="small"
          placeholder="Buscar por nome ou telefone"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
        />
      </Stack>

      {isLoading ? (
        <Loading variant="skeleton" count={3} />
      ) : error ? (
        <ErrorState message="Erro ao carregar clientes" onRetry={() => refetch()} />
      ) : (
        <>
          <CustomersKPIGrid kpis={kpis} />

          <CustomersAdvancedFilters
            minPedidos={advancedFilters.minPedidos}
            maxPedidos={advancedFilters.maxPedidos}
            minLTV={advancedFilters.minLTV}
            maxLTV={advancedFilters.maxLTV}
            ultimoPedidoApos={advancedFilters.ultimoPedidoApos}
            ultimoPedidoAntes={advancedFilters.ultimoPedidoAntes}
            onChange={(filters) => setAdvancedFilters(filters)}
          />

          <CustomersTable customers={customers} badgesMap={badgesMap} onRowClick={handleRowClick} />
        </>
      )}

      <CustomerDetailsDrawer
        open={!!selectedCustomer}
        customer={selectedCustomer}
        orders={ordersQuery.data?.pedidos}
        badges={selectedCustomer ? badgesMap[selectedCustomer.id] : []}
        onClose={() => setSelectedCustomer(null)}
      />
    </Box>
  );
}
