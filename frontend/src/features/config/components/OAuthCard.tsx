import {
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  IconButton,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from '@mui/material';
import { Link2, RefreshCw, Settings, Unlink, Zap } from 'lucide-react';
import { useConfirm } from '../../../components/system/useConfirm';

interface Props {
  provider: 'nuvemshop' | 'bling';
  label: string;
  connected: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  onTest?: () => Promise<boolean> | void;
  testing?: boolean;
  /** Abre a configuração avançada do provedor (vendedor padrão, mapeamento etc). */
  onOpenAdvanced?: () => void;
  /** Texto secundário exibido abaixo do label (ex: info da loja conectada). */
  subtitle?: string;
}

export function OAuthCard({
  label,
  connected,
  onConnect,
  onDisconnect,
  onTest,
  testing,
  onOpenAdvanced,
  subtitle,
}: Props) {
  const confirm = useConfirm();
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  const handleDisconnect = async () => {
    const confirmed = await confirm({
      title: `Desconectar ${label}`,
      description: `A integração com ${label} será desativada. Você poderá reconectar depois.`,
      confirmColor: 'warning',
      confirmText: 'Desconectar',
    });
    if (confirmed) onDisconnect();
  };

  return (
    <Card variant="outlined" sx={{ height: '100%', bgcolor: connected ? (isDark ? '#143d28' : '#e8f5e9') : (isDark ? '#2a2a2a' : '#f5f5f5') }}>
      <CardContent>
        <Stack spacing={2}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack spacing={0}>
              <Typography variant="subtitle1" fontWeight={600}>
                {label}
              </Typography>
              {subtitle && (
                <Typography variant="caption" color="text.secondary">
                  {subtitle}
                </Typography>
              )}
            </Stack>
            <Stack direction="row" spacing={0.5} alignItems="center">
              <Chip
                label={connected ? 'Conectado' : 'Não conectado'}
                color={connected ? 'success' : 'default'}
                size="small"
                variant={connected ? 'filled' : 'outlined'}
              />
              {onOpenAdvanced && (
                <Tooltip title="Configuração avançada">
                  <IconButton size="small" onClick={onOpenAdvanced} aria-label="Configuração avançada">
                    <Settings size={16} />
                  </IconButton>
                </Tooltip>
              )}
            </Stack>
          </Stack>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {!connected ? (
              <Button variant="contained" size="small" startIcon={<Link2 />} onClick={onConnect}>
                Conectar
              </Button>
            ) : (
              <>
                <Button variant="outlined" size="small" startIcon={<RefreshCw />} onClick={onConnect}>
                  Reconectar
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  color="warning"
                  startIcon={<Unlink />}
                  onClick={handleDisconnect}
                >
                  Desconectar
                </Button>
              </>
            )}
            {connected && onTest && (
              <Button
                variant="outlined"
                size="small"
                startIcon={testing ? <CircularProgress size={14} /> : <Zap size={14} />}
                onClick={() => void onTest()}
                disabled={testing}
              >
                Testar
              </Button>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
