import { Button, Card, CardContent, Chip, Stack, Typography } from '@mui/material';
import { Link2, RefreshCw, Unlink } from 'lucide-react';
import { useConfirm } from '../../../components/system/useConfirm';

interface Props {
  provider: 'nuvemshop' | 'bling';
  label: string;
  connected: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
}

export function OAuthCard({ label, connected, onConnect, onDisconnect }: Props) {
  const confirm = useConfirm();

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
    <Card variant="outlined" sx={{ height: '100%', bgcolor: connected ? '#e8f5e9' : '#f5f5f5' }}>
      <CardContent>
        <Stack spacing={2}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle1" fontWeight={600}>
              {label}
            </Typography>
            <Chip
              label={connected ? 'Conectado' : 'Não conectado'}
              color={connected ? 'success' : 'default'}
              size="small"
              variant={connected ? 'filled' : 'outlined'}
            />
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
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}