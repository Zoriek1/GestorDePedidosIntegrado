import React, { Suspense, useState } from 'react';
import { Box, Typography, Tabs, Tab, Paper, Stack, Button } from '@mui/material';
import { LocalShipping, Build, Payment, Calculate, Group, Storefront, People, CreditCard, BarChart } from '@mui/icons-material';
import { TaxaEntregaSettings } from './components/TaxaEntregaSettings';
import { TaxaCartaoSettings } from './components/TaxaCartaoSettings';
import { Loading } from '../../components/common/Loading';
import { DailyFreightDialog } from '../pedidos/components/DailyFreightDialog';
import { FreightBySourceDialog } from '../pedidos/components/FreightBySourceDialog';
import { createApiRequest } from '../../api/http';
import { useAuth } from '../auth/authStore';
import { useToast } from '../../components/system/useToast';
import { useConfirm } from '../../components/system/useConfirm';
import CustomersPage from '../customers/CustomersPage';
import NuvemshopPage from '../integrations/NuvemshopPage';
import FontesPage from '../fontes/FontesPage';
import UserListPage from '../users/components/UserListPage';

function BatchActionsTab() {
  const { getAuthHeader } = useAuth();
  const { success, error: showError } = useToast();
  const confirm = useConfirm();
  const [freightDialogOpen, setFreightDialogOpen] = useState(false);
  const [freightBySourceOpen, setFreightBySourceOpen] = useState(false);

  const handleBatchMarkPaid = async () => {
    const confirmed = await confirm({
      title: 'Marcar todos como Pago',
      description: 'Todos os pedidos com pagamento Pendente ou sem status de pagamento serão marcados como "Pago". Deseja continuar?',
      confirmColor: 'primary',
      confirmText: 'Marcar como Pago',
    });
    if (!confirmed) return;
    try {
      const apiRequest = createApiRequest(getAuthHeader);
      const res = await apiRequest<{ message?: string }>('/pedidos/batch-mark-paid', {
        method: 'POST',
      });
      if (!res.ok) throw new Error(res.message);
      success(res.data.message || 'Pedidos atualizados');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao marcar pedidos como pagos');
    }
  };

  const handleBatchRecalcTaxa = async () => {
    const confirmed = await confirm({
      title: 'Recalcular taxas de entrega',
      description: 'A taxa de entrega de todos os pedidos com distância registrada será recalculada com base nas faixas atuais. Deseja continuar?',
      confirmColor: 'primary',
      confirmText: 'Recalcular',
    });
    if (!confirmed) return;
    try {
      const apiRequest = createApiRequest(getAuthHeader);
      const res = await apiRequest<{ message?: string }>('/pedidos/batch-recalc-taxa', {
        method: 'POST',
      });
      if (!res.ok) throw new Error(res.message);
      success(res.data.message || 'Taxas recalculadas');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao recalcular taxas');
    }
  };

  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        Ações em lote sobre pedidos
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Operações administrativas que afetam múltiplos pedidos de uma vez.
      </Typography>

      <Stack spacing={2} sx={{ maxWidth: 400 }}>
        <Button
          variant="outlined"
          startIcon={<Payment />}
          onClick={handleBatchMarkPaid}
          fullWidth
        >
          Marcar todos como Pago
        </Button>
        <Button
          variant="outlined"
          startIcon={<Calculate />}
          onClick={handleBatchRecalcTaxa}
          fullWidth
        >
          Recalcular taxas de entrega
        </Button>
        <Button
          variant="outlined"
          startIcon={<LocalShipping />}
          onClick={() => setFreightDialogOpen(true)}
          fullWidth
        >
          Frete do dia
        </Button>
        <Button
          variant="outlined"
          startIcon={<BarChart />}
          onClick={() => setFreightBySourceOpen(true)}
          fullWidth
        >
          Frete médio por fonte
        </Button>
      </Stack>

      <DailyFreightDialog open={freightDialogOpen} onClose={() => setFreightDialogOpen(false)} />
      <FreightBySourceDialog
        open={freightBySourceOpen}
        onClose={() => setFreightBySourceOpen(false)}
      />
    </Box>
  );
}

export default function SettingsPage() {
  const { getUserRole } = useAuth();
  const [tabValue, setTabValue] = React.useState(0);
  const userRole = getUserRole() ?? 'admin';
  const isEntregador = userRole === 'entregador';
  const isAdmin = userRole === 'admin';

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box>
      <Box mb={3}>
        <Typography variant="h5" component="h1">
          Configurações
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Gerencie as configurações do sistema
        </Typography>
      </Box>

      <Paper sx={{ width: '100%', mb: 2 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab icon={<LocalShipping />} label="Taxa de Entrega" iconPosition="start" />
          {isAdmin && <Tab icon={<CreditCard />} label="Taxa de Cartão" iconPosition="start" />}
          <Tab icon={<Build />} label="Ações em Lote" iconPosition="start" />
          {!isEntregador && <Tab icon={<Build />} label="Fontes" iconPosition="start" />}
          {!isEntregador && <Tab icon={<Group />} label="Clientes" iconPosition="start" />}
          {!isEntregador && <Tab icon={<Storefront />} label="Nuvemshop" iconPosition="start" />}
          {isAdmin && <Tab icon={<People />} label="Funcionários" iconPosition="start" />}
        </Tabs>
      </Paper>

      <Box sx={{ mt: 2 }}>
        <Suspense fallback={<Loading />}>
          {tabValue === 0 && <TaxaEntregaSettings />}
          {isAdmin && tabValue === 1 && <TaxaCartaoSettings />}
          {tabValue === (isAdmin ? 2 : 1) && <BatchActionsTab />}
          {!isEntregador && tabValue === (isAdmin ? 3 : 2) && <FontesPage />}
          {!isEntregador && tabValue === (isAdmin ? 4 : 3) && <CustomersPage />}
          {!isEntregador && tabValue === (isAdmin ? 5 : 4) && <NuvemshopPage />}
          {isAdmin && tabValue === 6 && <UserListPage />}
        </Suspense>
      </Box>
    </Box>
  );
}
