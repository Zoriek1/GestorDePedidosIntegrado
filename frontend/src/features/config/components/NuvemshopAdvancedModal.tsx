import { useState } from 'react';
import {
  Alert,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
} from '@mui/material';
import { AppButton } from '../../../components/common/AppButton';
import { Loading } from '../../../components/common/Loading';
import { ErrorState } from '../../../components/common/ErrorState';
import { useToast } from '../../../components/system/useToast';
import {
  useListVendedores,
  useNuvemshopConfig,
  useProcessPendingNuvemshop,
  useSaveDefaultVendorNuvemshop,
  useSetupNuvemshopWebhooks,
} from '../../../api/endpoints/nuvemshop';
import { AssignVendorModal } from './AssignVendorModal';

interface Props {
  open: boolean;
  onClose: () => void;
}

/**
 * Configuração avançada da Nuvemshop: vendedor padrão, webhooks e backfill.
 *
 * Conectar/desconectar ficam no OAuthCard; aqui só o que exige mais de um clique.
 */
export function NuvemshopAdvancedModal({ open, onClose }: Props) {
  const nuvemshopConfig = useNuvemshopConfig();
  const vendedoresQuery = useListVendedores();
  const saveDefaultVendor = useSaveDefaultVendorNuvemshop();
  const setupWebhooks = useSetupNuvemshopWebhooks();
  const processPending = useProcessPendingNuvemshop();
  const { success, error: toastError } = useToast();

  const [assignModalOpen, setAssignModalOpen] = useState(false);
  // null = sem edição local; cai no valor salvo do servidor.
  const [draftVendorId, setDraftVendorId] = useState<number | '' | null>(null);

  const savedVendorId: number | '' = nuvemshopConfig.data?.default_vendedor_id ?? '';
  const defaultVendorId: number | '' = draftVendorId !== null ? draftVendorId : savedVendorId;

  const isLoading = nuvemshopConfig.isLoading || vendedoresQuery.isLoading;
  const isError = nuvemshopConfig.isError || vendedoresQuery.isError;

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>Nuvemshop — configuração avançada</DialogTitle>
        <DialogContent>
          {isLoading ? (
            <Loading />
          ) : isError ? (
            <ErrorState
              onRetry={() => {
                nuvemshopConfig.refetch();
                vendedoresQuery.refetch();
              }}
            />
          ) : (
            <Stack spacing={3} sx={{ mt: 1 }}>
              <Stack spacing={1}>
                <Typography variant="subtitle2" fontWeight={700}>
                  Vendedor padrão da loja
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Novos pedidos importados da Nuvemshop entram automaticamente com este vendedor.
                  O backfill existe só para pedidos antigos que já chegaram sem vendedor.
                </Typography>

                {!nuvemshopConfig.data?.connected ? (
                  <Alert severity="info">
                    Conecte a loja primeiro para salvar um vendedor padrão.
                  </Alert>
                ) : (
                  <>
                    <FormControl fullWidth size="small">
                      <InputLabel id="default-vendor-select-label">Vendedor padrão</InputLabel>
                      <Select
                        labelId="default-vendor-select-label"
                        value={defaultVendorId}
                        label="Vendedor padrão"
                        onChange={(event) => {
                          const value = event.target.value as number | '';
                          setDraftVendorId(value === '' ? '' : Number(value));
                        }}
                      >
                        <MenuItem value="">Nenhum</MenuItem>
                        {(vendedoresQuery.data ?? []).map((vendedor) => (
                          <MenuItem key={vendedor.id} value={vendedor.id}>
                            {vendedor.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                      <AppButton
                        variant="contained"
                        loading={saveDefaultVendor.isPending}
                        onClick={() =>
                          saveDefaultVendor.mutate(defaultVendorId === '' ? null : defaultVendorId, {
                            onSuccess: () => {
                              setDraftVendorId(null);
                              success('Vendedor padrão salvo');
                            },
                            onError: (err) => toastError((err as Error).message),
                          })
                        }
                      >
                        Salvar vendedor padrão
                      </AppButton>
                      <AppButton
                        variant="outlined"
                        disabled={defaultVendorId === ''}
                        loading={saveDefaultVendor.isPending}
                        onClick={() =>
                          saveDefaultVendor.mutate(null, {
                            onSuccess: () => {
                              setDraftVendorId(null);
                              success('Vendedor padrão removido');
                            },
                            onError: (err) => toastError((err as Error).message),
                          })
                        }
                      >
                        Limpar
                      </AppButton>
                      <AppButton variant="outlined" onClick={() => setAssignModalOpen(true)}>
                        Backfill de vendedor
                      </AppButton>
                    </Stack>

                    {nuvemshopConfig.data?.default_vendedor_name && (
                      <Typography variant="caption" color="text.secondary">
                        Atual: {nuvemshopConfig.data.default_vendedor_name}
                      </Typography>
                    )}
                  </>
                )}
              </Stack>

              <Stack spacing={1}>
                <Typography variant="subtitle2" fontWeight={700}>
                  Webhooks
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Recrie os webhooks de pedidos se a loja parar de enviar eventos, ou reprocesse
                  entregas de webhook que falharam.
                </Typography>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                  <AppButton
                    variant="outlined"
                    loading={setupWebhooks.isPending}
                    onClick={() =>
                      setupWebhooks.mutate(undefined, {
                        onSuccess: () => success('Webhooks recriados'),
                        onError: (err) => toastError((err as Error).message),
                      })
                    }
                  >
                    Recriar webhooks
                  </AppButton>
                  <AppButton
                    variant="outlined"
                    loading={processPending.isPending}
                    onClick={() =>
                      processPending.mutate(undefined, {
                        onSuccess: () => success('Pendências processadas'),
                        onError: (err) => toastError((err as Error).message),
                      })
                    }
                  >
                    Processar pendências de webhooks
                  </AppButton>
                </Stack>
                {processPending.isError && (
                  <Alert severity="error">
                    {(processPending.error as Error)?.message || 'Erro ao processar pendências.'}
                  </Alert>
                )}
              </Stack>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <AppButton onClick={onClose}>Fechar</AppButton>
        </DialogActions>
      </Dialog>

      <AssignVendorModal open={assignModalOpen} onClose={() => setAssignModalOpen(false)} />
    </>
  );
}
