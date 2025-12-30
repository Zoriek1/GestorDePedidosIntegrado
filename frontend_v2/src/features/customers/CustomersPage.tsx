/**
 * Customers Page (Placeholder)
 * Coming soon - will be migrated in next phase
 * Structure prepared for customer search implementation
 */

import { Box, Typography, Paper } from '@mui/material';
import { useCustomerSearch } from '../../api/endpoints/customers';

export default function CustomersPage() {
  // Placeholder: hook is ready but not used yet (debounce to be implemented)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { data, isLoading } = useCustomerSearch('', 10);

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Clientes
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          Em breve - Esta funcionalidade será migrada na próxima fase
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Estrutura preparada: useCustomerSearch hook disponível
        </Typography>
      </Paper>
    </Box>
  );
}

