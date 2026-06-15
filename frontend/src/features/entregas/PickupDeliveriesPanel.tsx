import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Paper, Button, Typography, Stack, Alert, CircularProgress } from '@mui/material';
import LocalShipping from '@mui/icons-material/LocalShipping';
import ArrowBack from '@mui/icons-material/ArrowBack';
import { useEntregasDisponiveis, useAtribuirEntregasLote } from './services/entregasApi';
import { useToast } from '../../components/system/useToast';
import { OrderCard } from '../pedidos/components/OrderCard';
import type { Pedido } from '../../api/endpoints/pedidos';

const moneyBRL = (n?: number) =>
  typeof n === 'number'
    ? n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : '—';

interface Props {
  /** Volta para a visão de rota sem atribuir nada. */
  onClose: () => void;
}

/**
 * Painel inline para o entregador "pegar entregas": cada entrega disponível é um OrderCard
 * com checkbox no próprio card, evitando errar o pedido. Substitui o antigo
 * AssignDeliveryDialog (listagem à parte). #8
 */
export function PickupDeliveriesPanel({ onClose }: Props) {
  const { data, isLoading, isError } = useEntregasDisponiveis();
  const atribuir = useAtribuirEntregasLote();
  const toast = useToast();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const pedidos = useMemo(() => data?.pedidos ?? [], [data?.pedidos]);
  const total = useMemo(
    () =>
      pedidos
        .filter((p) => selected.has(p.id))
        .reduce((sum, p) => sum + (p.taxa_entrega || 0), 0),
    [pedidos, selected]
  );

  const toggle = (pedido: Pedido) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(pedido.id)) next.delete(pedido.id);
      else next.add(pedido.id);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (selected.size === 0) return;
    try {
      const res = await atribuir.mutateAsync(Array.from(selected));
      const ok = res.atribuidos.length;
      const ig = res.ignorados.length;
      toast.success(`${ok} entrega(s) atribuída(s)${ig ? ` (${ig} ignorada(s))` : ''}`);
      setSelected(new Set());
      navigate('/entregador/mapa');
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Falha ao atribuir entregas');
    }
  };

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} mb={2}>
        <Button startIcon={<ArrowBack />} onClick={onClose} size="small">
          Voltar
        </Button>
        <LocalShipping fontSize="small" color="action" />
        <Typography variant="h6" component="h2">
          Pegar entregas
        </Typography>
      </Stack>

      {isLoading && (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      )}
      {isError && <Alert severity="error">Falha ao carregar entregas disponíveis</Alert>}
      {!isLoading && !isError && pedidos.length === 0 && (
        <Typography color="text.secondary" sx={{ py: 4 }} textAlign="center">
          Nenhuma entrega disponível no momento.
        </Typography>
      )}

      <Stack spacing={1.5} sx={{ pb: 12 }}>
        {pedidos.map((p) => (
          <OrderCard
            key={p.id}
            pedido={p}
            selectable
            selected={selected.has(p.id)}
            onToggleSelect={toggle}
            selectionMode="pickup"
          />
        ))}
      </Stack>

      {pedidos.length > 0 && (
        <Paper
          elevation={8}
          sx={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            p: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
            zIndex: (t) => t.zIndex.appBar,
          }}
        >
          <Typography variant="body2" color="text.secondary">
            {selected.size} selecionada(s) · Total: {moneyBRL(total)}
          </Typography>
          <Button
            variant="contained"
            startIcon={<LocalShipping />}
            onClick={handleSubmit}
            disabled={selected.size === 0 || atribuir.isPending}
          >
            {atribuir.isPending ? 'Confirmando...' : 'Confirmar'}
          </Button>
        </Paper>
      )}
    </Box>
  );
}

export default PickupDeliveriesPanel;
