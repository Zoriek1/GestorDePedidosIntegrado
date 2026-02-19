import React, { Suspense } from 'react';
import { Box, Typography, Tabs, Tab, Paper } from '@mui/material';
import { LocalShipping } from '@mui/icons-material';
import { TaxaEntregaSettings } from './components/TaxaEntregaSettings';
import { Loading } from '../../components/common/Loading';

export default function SettingsPage() {
  const [tabValue, setTabValue] = React.useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
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
        </Tabs>
      </Paper>

      <Box sx={{ mt: 2 }}>
        <Suspense fallback={<Loading />}>
          {tabValue === 0 && <TaxaEntregaSettings />}
        </Suspense>
      </Box>
    </Box>
  );
}
