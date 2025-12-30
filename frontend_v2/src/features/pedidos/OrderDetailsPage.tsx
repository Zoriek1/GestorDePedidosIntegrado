/**
 * Order Details Page (Placeholder)
 * Coming soon - will be migrated in next phase
 */

import { Box, Typography, Paper } from '@mui/material';
import { useParams } from 'react-router-dom';

export default function OrderDetailsPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Detalhes do Pedido #{id}
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          Em breve - Esta funcionalidade será migrada na próxima fase
        </Typography>
      </Paper>
    </Box>
  );
}

