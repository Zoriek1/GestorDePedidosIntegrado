import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
  TextField,
  Divider,
  Alert,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
} from '@mui/material';
import { AppButton } from '../../components/common/AppButton';
import { ErrorState } from '../../components/common/ErrorState';
import { Loading } from '../../components/common/Loading';
import { useToast } from '../../components/system/useToast';
import {
  usePendingSchedules,
  useDefineSchedule,
  useProcessPendingNuvemshop,
  useNuvemshopInstall,
  useSetupNuvemshopWebhooks,
  useNuvemshopConfig,
  useListVendedores,
  useSaveDefaultVendorNuvemshop,
} from '../../api/endpoints/nuvemshop';
import { AssignVendorModal } from './AssignVendorModal';

interface DraftState {
  [pedidoId: number]: {
    dia_entrega: string;
    horario: string;
  };
}

export default function NuvemshopPage() {
  const { data, isLoading, isError, refetch } = usePendingSchedules();
  const nuvemshopConfig = useNuvemshopConfig();
  const vendedoresQuery = useListVendedores();
  const defineSchedule = useDefineSchedule();
  const processPending = useProcessPendingNuvemshop();
  const install = useNuvemshopInstall();
  const setupWebhooks = useSetupNuvemshopWebhooks();
  const saveDefaultVendor = useSaveDefaultVendorNuvemshop();
  const { error: toastError, success } = useToast();

  const [drafts, setDrafts] = useState<DraftState>({});
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  // null = sem edição local; cai no valor salvo do servidor.
  const [draftVendorId, setDraftVendorId] = useState<number | '' | null>(null);
  const savedVendorId: number | '' = nuvemshopConfig.data?.default_vendedor_id ?? '';
  const defaultVendorId: number | '' = draftVendorId !== null ? draftVendorId : savedVendorId;

  const pendingItems = useMemo(() => data?.pedidos ?? [], [data]);

  useEffect(() => {
    if (searchParams.get('nuvemshop') === 'connected') {
      success('Loja Nuvemshop conectada. Webhooks configurados.');
      setSearchParams((prev) => {
        prev.delete('nuvemshop');
        return prev;
      }, { replace: true });
    }
  }, [searchParams, setSearchParams, success]);

  const handleDraftChange = (pedidoId: number, field: 'dia_entrega' | 'horario', value: string) => {
    setDrafts((prev) => ({
      ...prev,
      [pedidoId]: {
        dia_entrega: prev[pedidoId]?.dia_entrega || '',
        horario: prev[pedidoId]?.horario || '',
        [field]: value,
      },
    }));
  };

  if (isLoading || nuvemshopConfig.isLoading || vendedoresQuery.isLoading) {
    return <Loading />;
  }

  if (isError || nuvemshopConfig.isError || vendedoresQuery.isError) {
    return (
      <ErrorState
        onRetry={() => {
          refetch();
          nuvemshopConfig.refetch();
          vendedoresQuery.refetch();
        }}
      />
    );
  }

  return (
    <Box>
      <Stack spacing={2} sx={{ mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>
          Integracao Nuvemshop
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Pedidos importados sem data de entrega confirmada (HuaApps). Ajuste a data e confirme.
        </Typography>

        <Stack direction={{ xs: 'column', sm: 'row' }} flexWrap="wrap" spacing={2}>
          <AppButton
            variant="outlined"
            loading={install.isPending}
            onClick={() =>
              install.mutate(undefined, {
                onSuccess: (url) => { window.location.href = url; },
                onError: (err) => toastError((err as Error).message),
              })
            }
          >
            Conectar / reconectar loja
          </AppButton>
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
            variant="contained"
            loading={processPending.isPending}
            onClick={() =>
              processPending.mutate(undefined, {
                onSuccess: () => success('Pendências processadas'),
                onError: (err) => toastError((err as Error).message),
              })
            }
          >
            Processar pendencias de webhooks
          </AppButton>
          <AppButton variant="outlined" onClick={() => refetch()}>
            Atualizar lista
          </AppButton>
          <AppButton variant="outlined" onClick={() => setAssignModalOpen(true)}>
            Backfill de vendedor
          </AppButton>
        </Stack>
        {processPending.isError && (
          <Alert severity="error">
            {(processPending.error as Error)?.message || 'Erro ao processar pendencias.'}
          </Alert>
        )}

        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2}>
              <Stack spacing={0.5}>
                <Typography variant="subtitle1" fontWeight={700}>
                  Vendedor padrao da loja
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Novos pedidos importados da Nuvemshop entram automaticamente com este vendedor.
                  O botao de backfill continua existindo so para pedidos antigos que ja chegaram sem
                  vendedor.
                </Typography>
              </Stack>

              {!nuvemshopConfig.data?.connected ? (
                <Alert severity="info">
                  Conecte a loja primeiro para salvar um vendedor padrao.
                </Alert>
              ) : (
                <>
                  <FormControl fullWidth>
                    <InputLabel id="default-vendor-select-label">Vendedor padrao</InputLabel>
                    <Select
                      labelId="default-vendor-select-label"
                      value={defaultVendorId}
                      label="Vendedor padrao"
                      onChange={(event) => {
                        const value = event.target.value;
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

                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                    <AppButton
                      variant="contained"
                      loading={saveDefaultVendor.isPending}
                      onClick={() =>
                        saveDefaultVendor.mutate(defaultVendorId === '' ? null : defaultVendorId, {
                          onSuccess: () => {
                            setDraftVendorId(null);
                            success('Vendedor padrao salvo');
                          },
                          onError: (err) => toastError((err as Error).message),
                        })
                      }
                    >
                      Salvar vendedor padrao
                    </AppButton>
                    <AppButton
                      variant="outlined"
                      disabled={defaultVendorId === ''}
                      loading={saveDefaultVendor.isPending}
                      onClick={() =>
                        saveDefaultVendor.mutate(null, {
                          onSuccess: () => {
                            setDraftVendorId(null);
                            success('Vendedor padrao removido');
                          },
                          onError: (err) => toastError((err as Error).message),
                        })
                      }
                    >
                      Limpar
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
          </CardContent>
        </Card>
      </Stack>

      <AssignVendorModal open={assignModalOpen} onClose={() => setAssignModalOpen(false)} />

      {pendingItems.length === 0 ? (
        <Alert severity="success">Nenhuma pendencia de agendamento encontrada.</Alert>
      ) : (
        <Stack spacing={2}>
          {pendingItems.map((item) => {
            const draft = drafts[item.pedido_id] || {
              dia_entrega: item.dia_entrega || '',
              horario: item.horario || '',
            };

            return (
              <Card key={item.pedido_id} variant="outlined">
                <CardContent>
                  <Stack spacing={2}>
                    <Stack spacing={0.5}>
                      <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap">
                        <Typography variant="subtitle1" fontWeight={700}>
                          Pedido #{item.pedido_id} - {item.cliente}
                        </Typography>
                        {item.status_pagamento && (
                          <Chip
                            label={item.status_pagamento}
                            size="small"
                            color={item.status_pagamento === 'Pago' ? 'success' : 'warning'}
                            variant="outlined"
                          />
                        )}
                        {item.valor && (
                          <Typography variant="subtitle2" color="primary" fontWeight={600}>
                            {item.valor}
                          </Typography>
                        )}
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        Destinatario: {item.destinatario || '(nao informado)'}
                      </Typography>
                      {item.produto && (
                        <Typography variant="body2" color="text.secondary">
                          Produto: {item.produto}
                        </Typography>
                      )}
                      {item.endereco && (
                        <Typography variant="body2" color="text.secondary">
                          Endereco: {item.endereco}
                        </Typography>
                      )}
                      {item.observacoes && (
                        <Typography variant="caption" color="text.secondary">
                          {item.observacoes}
                        </Typography>
                      )}
                    </Stack>

                    <Divider />

                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                      <TextField
                        label="Dia de entrega"
                        type="date"
                        value={draft.dia_entrega}
                        onChange={(event) =>
                          handleDraftChange(item.pedido_id, 'dia_entrega', event.target.value)
                        }
                        InputLabelProps={{ shrink: true }}
                        fullWidth
                      />
                      <TextField
                        label="Horario"
                        placeholder="08:00 - 18:00"
                        value={draft.horario}
                        onChange={(event) =>
                          handleDraftChange(item.pedido_id, 'horario', event.target.value)
                        }
                        fullWidth
                      />
                    </Stack>

                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                      <AppButton
                        variant="contained"
                        loading={defineSchedule.isPending}
                        onClick={() =>
                          defineSchedule.mutate(
                            {
                              pedido_id: item.pedido_id,
                              dia_entrega: draft.dia_entrega,
                              horario: draft.horario || undefined,
                            },
                            {
                              onSuccess: () => success('Agendamento confirmado'),
                              onError: (err) => toastError((err as Error).message),
                            }
                          )
                        }
                        disabled={!draft.dia_entrega}
                      >
                        Confirmar agendamento
                      </AppButton>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      )}
    </Box>
  );
}
