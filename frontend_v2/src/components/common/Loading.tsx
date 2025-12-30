/**
 * Loading component
 */

import { Box, CircularProgress, Skeleton, Stack } from '@mui/material';

interface LoadingProps {
  variant?: 'spinner' | 'skeleton';
  count?: number;
}

export function Loading({ variant = 'spinner', count = 3 }: LoadingProps) {
  if (variant === 'spinner') {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Stack spacing={2} sx={{ mt: 2 }}>
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} variant="rectangular" height={120} />
      ))}
    </Stack>
  );
}

