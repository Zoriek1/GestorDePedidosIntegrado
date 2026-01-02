import { Box, Paper, Stack, Typography } from '@mui/material';
import { ReactNode } from 'react';

export interface KPICardProps {
  title: string;
  value: ReactNode;
  helperText?: string;
  icon: ReactNode;
  iconBg: string;
  iconColor: string;
}

export function KPICard({ title, value, helperText, icon, iconBg, iconColor }: KPICardProps) {
  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="caption" color="text.secondary" noWrap>
            {title}
          </Typography>
          <Typography variant="h5" fontWeight={700} noWrap>
            {value}
          </Typography>
          {helperText && (
            <Typography variant="body2" color="text.secondary" noWrap>
              {helperText}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            width: 56,
            height: 56,
            borderRadius: '50%',
            backgroundColor: iconBg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Box sx={{ color: iconColor, fontSize: 28, lineHeight: 0 }}>{icon}</Box>
        </Box>
      </Stack>
    </Paper>
  );
}


