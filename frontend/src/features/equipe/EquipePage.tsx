import { Suspense, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Box, Typography, Tabs, Tab, Paper } from '@mui/material';
import { People, AccountBalance } from '@mui/icons-material';
import UserListPage from '../users/components/UserListPage';
import LedgerPage from '../ledger/LedgerPage';
import { useAuth } from '../auth/authStore';
import { Loading } from '../../components/common/Loading';

export default function EquipePage() {
  const { getUserRole } = useAuth();
  const isAdmin = getUserRole() === 'admin';

  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') === 'recebiveis' && isAdmin
    ? 'recebiveis'
    : 'funcionarios';
  const [tabValue, setTabValue] = useState(initialTab);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: string) => {
    setTabValue(newValue);
    setSearchParams({ tab: newValue }, { replace: true });
  };

  return (
    <Box>
      <Box mb={3}>
        <Typography variant="h5" component="h1">
          Equipe
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Gerencie funcionários e recebíveis
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
          <Tab value="funcionarios" icon={<People />} label="Funcionários" iconPosition="start" />
          {isAdmin && <Tab value="recebiveis" icon={<AccountBalance />} label="Recebíveis" iconPosition="start" />}
        </Tabs>
      </Paper>

      <Box sx={{ mt: 2 }}>
        <Suspense fallback={<Loading />}>
          {tabValue === 'funcionarios' && <UserListPage />}
          {isAdmin && tabValue === 'recebiveis' && <LedgerPage />}
        </Suspense>
      </Box>
    </Box>
  );
}
