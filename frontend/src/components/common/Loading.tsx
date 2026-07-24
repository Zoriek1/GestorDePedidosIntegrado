import { Box, CircularProgress, Skeleton, Stack, Typography } from '@mui/material';

interface LoadingProps {
  variant?: 'spinner' | 'skeleton';
  count?: number;
  heights?: number[];
  message?: string;
}

const DEFAULT_HEIGHTS = [40, 40, 120, 60];

export function Loading({ variant = 'spinner', count = 3, heights, message }: LoadingProps) {
  if (variant === 'spinner') {
    return (
      <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" minHeight="200px" gap={2}>
        <CircularProgress />
        {message && <Typography variant="body2" color="text.secondary">{message}</Typography>}
      </Box>
    );
  }

  const skeletonHeights = heights ?? Array.from({ length: count }, (_, i) => DEFAULT_HEIGHTS[i % DEFAULT_HEIGHTS.length]);

  return (
    <Stack spacing={2} sx={{ mt: 2 }}>
      {skeletonHeights.map((h, i) => (
        <Skeleton key={i} variant="rectangular" height={h} sx={{ borderRadius: 1 }} />
      ))}
    </Stack>
  );
}

