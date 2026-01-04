/**
 * Error State component with retry
 */

import { Box, Button, Typography } from '@mui/material';
import { ErrorOutline, Refresh } from '@mui/icons-material';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = 'Erro ao carregar dados', onRetry }: ErrorStateProps) {
  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="200px"
      p={3}
    >
      <ErrorOutline sx={{ fontSize: 48, color: 'error.main', mb: 2 }} />
      <Typography variant="h6" color="text.secondary" gutterBottom>
        {message}
      </Typography>
      {onRetry && (
        <Button
          variant="contained"
          startIcon={<Refresh />}
          onClick={onRetry}
          sx={{ mt: 2 }}
        >
          Tentar Novamente
        </Button>
      )}
    </Box>
  );
}

