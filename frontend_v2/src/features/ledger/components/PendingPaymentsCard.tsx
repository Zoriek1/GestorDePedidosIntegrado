import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Divider,
  FormControlLabel,
  Skeleton,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import PendingActionsIcon from '@mui/icons-material/PendingActions';
import PaymentsIcon from '@mui/icons-material/Payments';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ScheduleIcon from '@mui/icons-material/Schedule';
import HistoryIcon from '@mui/icons-material/History';
import { useEffect, useMemo, useState } from 'react';
import { formatBRL } from '../../../lib/format/currency';
import {
  PendingPedidoItem,
  usePendingPayments,
  useSettleUser,
} from '../services/ledgerApi';

interface PendingPaymentsCardProps {
  userId?: number;
  isAdmin?: boolean;
}

type SectionKey = 'atrasado' | 'a_receber';

function formatDate(dateIso: string | null): string {
  if (!dateIso) return 'sem data';
  const d = new Date(`${dateIso}T00:00:00`);
  return d.toLocaleDateString('pt-BR');
}

function formatCompetenciaLabel(competenciaTipo: 'semanal' | 'mensal', value: string): string {
  if (competenciaTipo === 'mensal') {
    const [year, month] = value.split('-');
    if (!year || !month) return value;
    return `${month}/${year}`;
  }
  const match = value.match(/^(\d{4})-W(\d{2})$/);
  if (!match) return value;
  return `Semana ${match[2]}/${match[1]}`;
}

function sumByPedidoIds(pedidos: PendingPedidoItem[], pedidoIds: number[]): number {
  if (!pedidos.length || !pedidoIds.length) return 0;
  const selected = new Set(pedidoIds);
  return pedidos.reduce((acc, item) => (selected.has(item.pedido_id) ? acc + item.amount : acc), 0);
}

function compactFonte(fonte: string | null): string {
  return fonte || 'Sem fonte';
}

export function PendingPaymentsCard({ userId, isAdmin }: PendingPaymentsCardProps) {
  const [competenciaTipo, setCompetenciaTipo] = useState<'semanal' | 'mensal'>('semanal');
  const [competencia, setCompetencia] = useState<string | undefined>(undefined);
  const [showQuitados, setShowQuitados] = useState(false);
  const [selectedAtrasado, setSelectedAtrasado] = useState<number[]>([]);
  const [selectedAReceber, setSelectedAReceber] = useState<number[]>([]);

  const pendingQuery = usePendingPayments({
    user_id: userId,
    competencia_tipo: competenciaTipo,
    competencia,
    include_quitados: showQuitados,
  });
  const settleMutation = useSettleUser();

  const data = pendingQuery.data;
  const atrasoPedidos = data?.atrasado.pedidos ?? [];
  const receberPedidos = data?.a_receber.pedidos ?? [];
  const quitadoPedidos = data?.quitado.pedidos ?? [];

  const atrasoIds = useMemo(() => atrasoPedidos.map((p) => p.pedido_id), [atrasoPedidos]);
  const receberIds = useMemo(() => receberPedidos.map((p) => p.pedido_id), [receberPedidos]);

  useEffect(() => {
    if (!data) return;
    if (!competencia || competencia !== data.competencia) {
      setCompetencia(data.competencia);
    }
  }, [data, competencia]);

  useEffect(() => {
    setSelectedAtrasado(atrasoIds);
  }, [atrasoIds.join(',')]);

  useEffect(() => {
    setSelectedAReceber(receberIds);
  }, [receberIds.join(',')]);

  const handleTogglePedido = (section: SectionKey, pedidoId: number, checked: boolean) => {
    const setter = section === 'atrasado' ? setSelectedAtrasado : setSelectedAReceber;
    setter((prev) => {
      if (checked) return Array.from(new Set([...prev, pedidoId]));
      return prev.filter((id) => id !== pedidoId);
    });
  };

  const handleToggleAll = (section: SectionKey, checked: boolean, ids: number[]) => {
    const setter = section === 'atrasado' ? setSelectedAtrasado : setSelectedAReceber;
    setter(checked ? ids : []);
  };

  const settleSection = (section: SectionKey, selectedIds: number[]) => {
    if (!selectedIds.length || !data) return;
    settleMutation.mutate({
      user_id: userId,
      pedido_ids: selectedIds,
      contexto: {
        section,
        competencia_tipo: competenciaTipo,
        competencia: data.competencia,
      },
    });
  };

  const renderPedidoList = (
    section: SectionKey,
    pedidos: PendingPedidoItem[],
    selectedIds: number[],
  ) => {
    if (!pedidos.length) {
      return (
        <Alert severity="success" sx={{ mt: 1 }}>
          Nenhum pedido nesta seção.
        </Alert>
      );
    }

    const allChecked = selectedIds.length > 0 && selectedIds.length === pedidos.length;
    const partialChecked = selectedIds.length > 0 && selectedIds.length < pedidos.length;

    return (
      <Box mt={1}>
        <FormControlLabel
          control={(
            <Checkbox
              checked={allChecked}
              indeterminate={partialChecked}
              onChange={(e) => handleToggleAll(section, e.target.checked, pedidos.map((p) => p.pedido_id))}
            />
          )}
          label="Selecionar todos"
        />
        <Stack spacing={0.5}>
          {pedidos.map((pedido) => (
            <Box
              key={pedido.ledger_entry_id}
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1.5,
                p: 1,
              }}
            >
              <Box display="flex" alignItems="center" justifyContent="space-between" gap={1}>
                <Box display="flex" alignItems="center" gap={0.5}>
                  <Checkbox
                    checked={selectedIds.includes(pedido.pedido_id)}
                    onChange={(e) => handleTogglePedido(section, pedido.pedido_id, e.target.checked)}
                  />
                  <Box>
                    <Typography variant="body2" fontWeight={600}>
                      #{pedido.pedido_id} · {pedido.cliente || 'Sem cliente'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Vence {formatDate(pedido.due_date)} · {compactFonte(pedido.fonte)}
                    </Typography>
                  </Box>
                </Box>
                <Typography variant="body2" fontWeight={700}>
                  {formatBRL(pedido.amount)}
                </Typography>
              </Box>
            </Box>
          ))}
        </Stack>
      </Box>
    );
  };

  const renderSettleSection = (
    section: SectionKey,
    title: string,
    total: number,
    pedidos: PendingPedidoItem[],
    selectedIds: number[],
  ) => {
    const selectedAmount = sumByPedidoIds(pedidos, selectedIds);
    const canSettle = selectedIds.length > 0 && !settleMutation.isPending;
    const isAtrasado = section === 'atrasado';

    return (
      <Box
        sx={{
          border: '1px solid',
          borderColor: isAtrasado ? 'error.light' : 'warning.light',
          borderRadius: 2,
          p: 1.5,
        }}
      >
        <Box display="flex" alignItems="center" justifyContent="space-between" gap={1}>
          <Box display="flex" alignItems="center" gap={1}>
            {isAtrasado ? <WarningAmberIcon color="error" /> : <ScheduleIcon color="warning" />}
            <Typography variant="subtitle2" fontWeight={700}>
              {title} — {formatBRL(total)}
            </Typography>
            <Chip
              size="small"
              label={pedidos.length}
              color={isAtrasado ? 'error' : 'warning'}
              sx={{ height: 20 }}
            />
          </Box>
          <Button
            variant="contained"
            color="success"
            size="small"
            startIcon={<PaymentsIcon />}
            onClick={() => settleSection(section, selectedIds)}
            disabled={!canSettle}
            sx={{ fontWeight: 700 }}
          >
            Recebi pagamento — {formatBRL(selectedAmount)}
          </Button>
        </Box>
        {renderPedidoList(section, pedidos, selectedIds)}
      </Box>
    );
  };

  return (
    <Card elevation={2} sx={{ borderRadius: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
          <Box display="flex" alignItems="center" gap={1}>
            <PendingActionsIcon color="primary" />
            <Typography variant="subtitle2" color="text.secondary">
              A Receber por Status
            </Typography>
          </Box>
          <FormControlLabel
            control={(
              <Switch
                checked={showQuitados}
                onChange={(e) => setShowQuitados(e.target.checked)}
              />
            )}
            label="Mostrar quitados"
          />
        </Box>

        {pendingQuery.isLoading ? (
          <Box>
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} variant="rectangular" height={56} sx={{ mb: 1, borderRadius: 1 }} />
            ))}
          </Box>
        ) : (
          <Stack spacing={1.5}>
            {renderSettleSection(
              'atrasado',
              'Atrasado',
              data?.atrasado.total ?? 0,
              atrasoPedidos,
              selectedAtrasado,
            )}

            <Box
              sx={{
                border: '1px solid',
                borderColor: 'warning.light',
                borderRadius: 2,
                p: 1.5,
              }}
            >
              <Box display="flex" justifyContent="space-between" alignItems="center" gap={1} mb={1}>
                <Typography variant="body2" fontWeight={600}>
                  Competência
                </Typography>
                <Stack direction="row" gap={1}>
                  <TextField
                    select
                    size="small"
                    value={competenciaTipo}
                    onChange={(e) => {
                      const next = e.target.value as 'semanal' | 'mensal';
                      setCompetenciaTipo(next);
                      setCompetencia(undefined);
                    }}
                    sx={{ minWidth: 120 }}
                    SelectProps={{ native: true }}
                  >
                    <option value="semanal">Semanal</option>
                    <option value="mensal">Mensal</option>
                  </TextField>
                  <TextField
                    select
                    size="small"
                    value={competencia ?? ''}
                    onChange={(e) => setCompetencia(e.target.value)}
                    sx={{ minWidth: 180 }}
                    SelectProps={{ native: true }}
                  >
                    {(data?.competencias_disponiveis ?? []).map((item) => (
                      <option key={item} value={item}>
                        {formatCompetenciaLabel(competenciaTipo, item)}
                      </option>
                    ))}
                  </TextField>
                </Stack>
              </Box>

              {renderSettleSection(
                'a_receber',
                'A Receber',
                data?.a_receber.total ?? 0,
                receberPedidos,
                selectedAReceber,
              )}
            </Box>

            <Divider />

            <Box
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 2,
                p: 1.5,
              }}
            >
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <HistoryIcon fontSize="small" color="action" />
                <Typography variant="subtitle2" fontWeight={700}>
                  Historico / Quitados — {formatBRL(data?.quitado.total ?? 0)}
                </Typography>
                <Chip size="small" label={quitadoPedidos.length} />
              </Box>
              {!showQuitados ? (
                <Alert severity="info">Ative "Mostrar quitados" para carregar o histórico.</Alert>
              ) : quitadoPedidos.length === 0 ? (
                <Alert severity="success">Sem itens quitados para o filtro atual.</Alert>
              ) : (
                <Stack spacing={0.5}>
                  {quitadoPedidos.map((pedido) => (
                    <Box
                      key={pedido.ledger_entry_id}
                      sx={{
                        border: '1px solid',
                        borderColor: 'divider',
                        borderRadius: 1.5,
                        p: 1,
                      }}
                    >
                      <Box display="flex" alignItems="center" justifyContent="space-between">
                        <Box>
                          <Typography variant="body2" fontWeight={600}>
                            #{pedido.pedido_id} · {pedido.cliente || 'Sem cliente'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Quitado · Vence {formatDate(pedido.due_date)}
                          </Typography>
                        </Box>
                        <Typography variant="body2" fontWeight={700}>
                          {formatBRL(pedido.amount)}
                        </Typography>
                      </Box>
                    </Box>
                  ))}
                </Stack>
              )}
            </Box>

            {!isAdmin && (
              <Typography variant="caption" color="text.secondary">
                Atrasados sempre aparecem; competência afeta apenas a seção "A Receber".
              </Typography>
            )}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
