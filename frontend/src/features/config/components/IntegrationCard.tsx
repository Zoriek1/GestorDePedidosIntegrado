import {
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  IconButton,
  Stack,
  Typography,
} from '@mui/material';
import { Settings, Zap } from 'lucide-react';
import type { ChannelDef } from '../constants';
import type { IntegrationSettingsConfig, ChannelStatus } from '../services/configService';

interface Props {
  channel: ChannelDef;
  config: IntegrationSettingsConfig;
  status: ChannelStatus | null | undefined;
  onOpenModal: () => void;
  onTest?: () => Promise<boolean> | void;
  testing?: boolean;
}

function resolveFieldStatus(config: IntegrationSettingsConfig, channel: ChannelDef): {
  label: string;
  color: 'default' | 'success' | 'warning';
  bgcolor: string;
} {
  if (!channel.fields) return { label: 'Não configurado', color: 'default', bgcolor: '#f5f5f5' };

  const allRequiredFilled = channel.fields
    .filter(f => f.required)
    .every(f => {
      if (f.type === 'password') {
        return config[`has_${f.key}` as keyof IntegrationSettingsConfig];
      }
      const val = config[f.key as keyof IntegrationSettingsConfig];
      return val !== null && val !== '' && val !== undefined;
    });

  if (!allRequiredFilled) {
    return { label: 'Não configurado', color: 'default', bgcolor: '#f5f5f5' };
  }

  return { label: 'Pendente', color: 'warning', bgcolor: '#fff8e1' };
}

function resolveStatusChip(
  status: ChannelStatus | null | undefined,
  fieldStatus: { label: string; color: 'default' | 'success' | 'warning'; bgcolor: string },
) {
  if (!status || status.ok === null) return fieldStatus;
  if (status.ok) {
    return { label: 'Validado', color: 'success' as const, bgcolor: '#e8f5e9' };
  }
  return { label: 'Falhou', color: 'default' as const, bgcolor: '#ffebee' };
}

export function IntegrationCard({ channel, config, status, onOpenModal, onTest, testing }: Props) {
  const fieldStatus = resolveFieldStatus(config, channel);
  const { label, color, bgcolor } = resolveStatusChip(status, fieldStatus);

  return (
    <Card
      variant="outlined"
      sx={{
        height: '100%',
        bgcolor,
        cursor: 'pointer',
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 3 },
      }}
      onClick={onOpenModal}
    >
      <CardContent>
        <Stack spacing={1.5}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle1" fontWeight={600}>
              {channel.label}
            </Typography>
            <Stack direction="row" spacing={0.5} alignItems="center">
              <Chip
                label={label}
                color={color}
                size="small"
                variant={color === 'default' ? 'outlined' : 'filled'}
              />
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenModal();
                }}
              >
                <Settings fontSize="small" />
              </IconButton>
            </Stack>
          </Stack>

          {channel.testable && onTest && (
            <Stack direction="row" spacing={1} alignItems="center">
              <Button
                size="small"
                variant="outlined"
                startIcon={testing ? <CircularProgress size={14} /> : <Zap size={14} />}
                onClick={(e) => {
                  e.stopPropagation();
                  void onTest();
                }}
                disabled={testing}
              >
                Testar
              </Button>
              {testing && (
                <Typography variant="caption" color="text.secondary">
                  Validando credenciais…
                </Typography>
              )}
            </Stack>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
