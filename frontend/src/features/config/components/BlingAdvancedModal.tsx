import { useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  ListSubheader,
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
import { RefreshCw, Save } from 'lucide-react';
import {
  useBlingConfig,
  useBlingStatus,
  useSaveBlingMapping,
  useSyncBlingConfig,
} from '../../../api/endpoints/bling';
import type { BlingOption, BlingPaymentMapping } from '../../../api/endpoints/bling';
import { Loading } from '../../../components/common/Loading';
import { ErrorState } from '../../../components/common/ErrorState';
import { useToast } from '../../../components/system/useToast';

interface Props {
  open: boolean;
  onClose: () => void;
}

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

function sortByName(options: BlingOption[]) {
  return [...options].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
}

function findOption(options: BlingOption[] | undefined, id: number | '') {
  if (id === '') return null;
  return (options ?? []).find((option) => option.id === id) ?? null;
}

function optionLabel(option: BlingOption) {
  return option.ativo ? option.nome : `${option.nome} (inativo)`;
}

function groupedOptionItems(options: BlingOption[] | undefined, emptyLabel: string) {
  const activeOptions = sortByName((options ?? []).filter((option) => option.ativo));
  const inactiveOptions = sortByName((options ?? []).filter((option) => !option.ativo));
  const hasBothStatuses = activeOptions.length > 0 && inactiveOptions.length > 0;

  return [
    <MenuItem key="empty" value="">
      {emptyLabel}
    </MenuItem>,
    ...(hasBothStatuses
      ? [
          <ListSubheader key="active-header" disableSticky>
            Ativos
          </ListSubheader>,
        ]
      : []),
    ...activeOptions.map((option) => (
      <MenuItem key={option.id} value={option.id}>
        {option.nome}
      </MenuItem>
    )),
    ...(inactiveOptions.length
      ? [
          <ListSubheader key="inactive-header" disableSticky>
            Inativos
          </ListSubheader>,
          ...inactiveOptions.map((option) => (
            <MenuItem key={option.id} value={option.id} sx={{ color: 'text.secondary' }}>
              {optionLabel(option)}
            </MenuItem>
          )),
        ]
      : []),
  ];
}

/**
 * Configuração avançada do Bling: mapeamento financeiro por forma de pagamento.
 *
 * Conectar/desconectar ficam no OAuthCard; aqui fica o que depende dos cadastros
 * sincronizados do Bling (formas, portadores e categorias).
 */
export function BlingAdvancedModal({ open, onClose }: Props) {
  const statusQuery = useBlingStatus();
  const configQuery = useBlingConfig();
  const syncConfig = useSyncBlingConfig();
  const saveMapping = useSaveBlingMapping();
  const { success, error: showError } = useToast();
  const [drafts, setDrafts] = useState<Record<number, MappingDraft>>({});

  const mappings = useMemo(() => configQuery.data?.mappings ?? [], [configQuery.data?.mappings]);

  const status = statusQuery.data;
  const config = configQuery.data;

  // O draft de cada linha e derivado sob demanda no render/save via
  // `drafts[id] ?? draftFromMapping(mapping)`, entao nao pre-populamos drafts
  // num effect (evita setState em effect e renders em cascata).
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

  const isLoading = statusQuery.isLoading || configQuery.isLoading;
  const isError = statusQuery.isError || configQuery.isError;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>Bling — mapeamento financeiro</DialogTitle>
      <DialogContent>
        {isLoading ? (
          <Loading />
        ) : isError ? (
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
        ) : (
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1}
              alignItems={{ xs: 'flex-start', sm: 'center' }}
            >
              <Chip
                label={status?.enabled ? 'Habilitada' : 'Desabilitada'}
                color={status?.enabled ? 'success' : 'default'}
                size="small"
              />
              <Chip
                label={status?.connected ? 'Conectada' : 'Nao conectada'}
                color={status?.connected ? 'success' : 'warning'}
                size="small"
              />
              {status?.counts?.outbox_pending ? (
                <Chip label={`${status.counts.outbox_pending} pendente(s)`} color="info" size="small" />
              ) : null}
              <Button
                variant="contained"
                size="small"
                startIcon={<RefreshCw size={16} />}
                onClick={handleSync}
                disabled={syncConfig.isPending || !status?.connected}
              >
                Sincronizar cadastros
              </Button>
            </Stack>

            {!status?.enabled && (
              <Alert severity="info">
                BLING_ENABLED esta desativado. O envio fica bloqueado ate habilitar o ambiente.
              </Alert>
            )}

            <Typography variant="body2" color="text.secondary">
              Forma Gestor para forma Bling, portador e categoria usados nas parcelas e baixas.
            </Typography>

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
                    const selectedPaymentMethod = findOption(
                      config?.payment_methods,
                      draft.bling_payment_method_id,
                    );
                    const selectedFinancialAccount = findOption(
                      config?.financial_accounts,
                      draft.bling_financial_account_id,
                    );
                    const selectedCategory = findOption(config?.categories, draft.bling_category_id);
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
                              {groupedOptionItems(config?.payment_methods, 'Nao mapeado')}
                            </Select>
                          </FormControl>
                          {selectedPaymentMethod && !selectedPaymentMethod.ativo && (
                            <Chip label="Forma inativa" size="small" sx={{ mt: 1 }} />
                          )}
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
                              {groupedOptionItems(config?.financial_accounts, 'Nao mapeado')}
                            </Select>
                          </FormControl>
                          {selectedFinancialAccount && !selectedFinancialAccount.ativo && (
                            <Chip label="Portador inativo" size="small" sx={{ mt: 1 }} />
                          )}
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
                              {groupedOptionItems(config?.categories, 'Nao mapeado')}
                            </Select>
                          </FormControl>
                          {selectedCategory && !selectedCategory.ativo && (
                            <Chip label="Categoria inativa" size="small" sx={{ mt: 1 }} />
                          )}
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
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fechar</Button>
      </DialogActions>
    </Dialog>
  );
}
