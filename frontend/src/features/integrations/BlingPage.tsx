import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { ExternalLink, RefreshCw, Save } from 'lucide-react';
import {
  useBlingConfig,
  useBlingInstall,
  useBlingStatus,
  useSaveBlingMapping,
  useSyncBlingConfig,
} from '../../api/endpoints/bling';
import type { BlingPaymentMapping } from '../../api/endpoints/bling';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../components/system/useToast';

type MappingDraft = {
  bling_payment_method_id: number | '';
  bling_financial_account_id: number | '';
  bling_category_id: number | '';
  active: boolean;
};

function draftFromMapping(mapping: BlingPaymentMapping): MappingDraft {
  return {
    bling_payment_method_id: mapping.bling_payment_method_id ?? '',
    bling_financial_account_id: mapping.bling_financial_account_id ?? '',
    bling_category_id: mapping.bling_category_id ?? '',
    active: mapping.active,
  };
}

function toApiValue(value: number | '') {
  return value === '' ? null : value;
}

function parseSelectValue(value: unknown): number | '' {
  const text = String(value);
  return text === '' ? '' : Number(text);
}

export default function BlingPage() {
  const statusQuery = useBlingStatus();
  const configQuery = useBlingConfig();
  const install = useBlingInstall();
  const syncConfig = useSyncBlingConfig();
  const saveMapping = useSaveBlingMapping();
  const { success, error: showError } = useToast();
  const [drafts, setDrafts] = useState<Record<number, MappingDraft>>({});
  const [searchParams, setSearchParams] = useSearchParams();

  const mappings = useMemo(() => configQuery.data?.mappings ?? [], [configQuery.data?.mappings]);

  useEffect(() => {
    if (!mappings.length) return;
    setDrafts((prev) => {
      const next = { ...prev };
      mappings.forEach((mapping) => {
        if (!next[mapping.id]) next[mapping.id] = draftFromMapping(mapping);
      });
      return next;
    });
  }, [mappings]);

  useEffect(() => {
    if (searchParams.get('bling') !== 'connected') return;
    success('Bling conectado');
    setSearchParams((prev) => {
      prev.delete('bling');
      return prev;
    }, { replace: true });
  }, [searchParams, setSearchParams, success]);

  if (statusQuery.isLoading || configQuery.isLoading) return <Loading />;
  if (statusQuery.isError || configQuery.isError) {
    return (
      <ErrorState
        message={
          statusQuery.error?.message ||
          configQuery.error?.message ||
          'Erro ao carregar integracao Bling'
        }
        onRetry={() => {
          statusQuery.refetch();
          configQuery.refetch();
        }}
      />
    );
  }

  const status = statusQuery.data;
  const config = configQuery.data;

  const updateDraft = <K extends keyof MappingDraft>(
    mappingId: number,
    key: K,
    value: MappingDraft[K],
  ) => {
    setDrafts((prev) => ({
      ...prev,
      [mappingId]: {
        ...(prev[mappingId] ?? {
          bling_payment_method_id: '',
          bling_financial_account_id: '',
          bling_category_id: '',
          active: true,
        }),
        [key]: value,
      },
    }));
  };

  const handleInstall = async () => {
    try {
      const url = await install.mutateAsync();
      window.location.href = url;
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao iniciar OAuth Bling');
    }
  };

  const handleSync = async () => {
    try {
      await syncConfig.mutateAsync();
      success('Cadastros financeiros sincronizados');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao sincronizar Bling');
    }
  };

  const handleSave = async (mapping: BlingPaymentMapping) => {
    const draft = drafts[mapping.id] ?? draftFromMapping(mapping);
    try {
      await saveMapping.mutateAsync({
        id: mapping.id,
        bling_payment_method_id: toApiValue(draft.bling_payment_method_id),
        bling_financial_account_id: toApiValue(draft.bling_financial_account_id),
        bling_category_id: toApiValue(draft.bling_category_id),
        active: draft.active,
      });
      success('Mapeamento salvo');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao salvar mapeamento');
    }
  };

  return (
    <Box>
      <Stack spacing={2} sx={{ mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>
          Integracao Bling
        </Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ xs: 'flex-start', sm: 'center' }}>
          <Chip label={status?.enabled ? 'Habilitada' : 'Desabilitada'} color={status?.enabled ? 'success' : 'default'} />
          <Chip label={status?.connected ? 'Conectada' : 'Nao conectada'} color={status?.connected ? 'success' : 'warning'} />
          {status?.counts?.outbox_pending ? (
            <Chip label={`${status.counts.outbox_pending} pendente(s)`} color="info" />
          ) : null}
        </Stack>

        {!status?.enabled && (
          <Alert severity="info">
            BLING_ENABLED esta desativado. O envio fica bloqueado ate habilitar o ambiente.
          </Alert>
        )}

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Button
            variant="outlined"
            startIcon={<ExternalLink size={16} />}
            onClick={handleInstall}
            disabled={install.isPending}
          >
            Conectar / reconectar
          </Button>
          <Button
            variant="contained"
            startIcon={<RefreshCw size={16} />}
            onClick={handleSync}
            disabled={syncConfig.isPending || !status?.connected}
          >
            Sincronizar cadastros
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              statusQuery.refetch();
              configQuery.refetch();
            }}
          >
            Atualizar
          </Button>
        </Stack>
      </Stack>

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Box>
              <Typography variant="subtitle1" fontWeight={700}>
                Mapeamento financeiro
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Forma Gestor para forma Bling, portador e categoria usados nas parcelas e baixas.
              </Typography>
            </Box>

            <Box sx={{ overflowX: 'auto' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Forma Gestor</TableCell>
                    <TableCell>Forma Bling</TableCell>
                    <TableCell>Portador</TableCell>
                    <TableCell>Categoria</TableCell>
                    <TableCell align="right">Acao</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mappings.map((mapping) => {
                    const draft = drafts[mapping.id] ?? draftFromMapping(mapping);
                    return (
                      <TableRow key={mapping.id}>
                        <TableCell sx={{ fontWeight: 700 }}>{mapping.gestor_payment_label}</TableCell>
                        <TableCell sx={{ minWidth: 220 }}>
                          <FormControl fullWidth size="small">
                            <InputLabel>Forma Bling</InputLabel>
                            <Select
                              label="Forma Bling"
                              value={draft.bling_payment_method_id}
                              onChange={(event) =>
                                updateDraft(
                                  mapping.id,
                                  'bling_payment_method_id',
                                  parseSelectValue(event.target.value),
                                )
                              }
                            >
                              <MenuItem value="">Nao mapeado</MenuItem>
                              {(config?.payment_methods ?? []).map((option) => (
                                <MenuItem key={option.id} value={option.id}>
                                  {option.nome}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </TableCell>
                        <TableCell sx={{ minWidth: 220 }}>
                          <FormControl fullWidth size="small">
                            <InputLabel>Portador</InputLabel>
                            <Select
                              label="Portador"
                              value={draft.bling_financial_account_id}
                              onChange={(event) =>
                                updateDraft(
                                  mapping.id,
                                  'bling_financial_account_id',
                                  parseSelectValue(event.target.value),
                                )
                              }
                            >
                              <MenuItem value="">Nao mapeado</MenuItem>
                              {(config?.financial_accounts ?? []).map((option) => (
                                <MenuItem key={option.id} value={option.id}>
                                  {option.nome}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </TableCell>
                        <TableCell sx={{ minWidth: 220 }}>
                          <FormControl fullWidth size="small">
                            <InputLabel>Categoria</InputLabel>
                            <Select
                              label="Categoria"
                              value={draft.bling_category_id}
                              onChange={(event) =>
                                updateDraft(
                                  mapping.id,
                                  'bling_category_id',
                                  parseSelectValue(event.target.value),
                                )
                              }
                            >
                              <MenuItem value="">Nao mapeado</MenuItem>
                              {(config?.categories ?? []).map((option) => (
                                <MenuItem key={option.id} value={option.id}>
                                  {option.nome}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </TableCell>
                        <TableCell align="right">
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<Save size={16} />}
                            onClick={() => handleSave(mapping)}
                            disabled={saveMapping.isPending}
                          >
                            Salvar
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {!mappings.length && (
                    <TableRow>
                      <TableCell colSpan={5}>
                        <Typography variant="body2" color="text.secondary">
                          Nenhuma forma padrao criada ainda. Sincronize os cadastros para iniciar.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
