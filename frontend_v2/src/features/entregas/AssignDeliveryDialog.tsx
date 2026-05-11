import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Checkbox,
  Typography,
  Box,
  Stack,
  Chip,
  Alert,
} from '@mui/material';
import LocalShipping from '@mui/icons-material/LocalShipping';
import { useEntregasDisponiveis, useAtribuirEntregasLote } from './services/entregasApi';
import { useToast } from '../../components/system/useToast';
import { Loading } from '../../components/common/Loading';

interface Props {
  open: boolean;
  onClose: () => void;
}

const moneyBRL = (n?: number) =>
  typeof n === 'number'
    ? n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : '—';

export function AssignDeliveryDialog({ open, onClose }: Props) {
  const { data, isLoading, isError } = useEntregasDisponiveis({ enabled: open });
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

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
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
      onClose();
      navigate('/entregador/mapa');
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Falha ao atribuir entregas');
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" spacing={1}>
          <LocalShipping />
          <Typography variant="h6" component="span">
            Pegar entregas
          </Typography>
        </Stack>
      </DialogTitle>
      <DialogContent dividers>
        {isLoading && <Loading />}
        {isError && <Alert severity="error">Falha ao carregar entregas disponíveis</Alert>}
        {!isLoading && pedidos.length === 0 && (
          <Typography color="text.secondary" sx={{ py: 2 }} textAlign="center">
            Nenhuma entrega disponível no momento.
          </Typography>
        )}
        {pedidos.length > 0 && (
          <List dense disablePadding>
            {pedidos.map((p) => {
              const checked = selected.has(p.id);
              return (
                <ListItemButton key={p.id} onClick={() => toggle(p.id)} dense>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <Checkbox edge="start" checked={checked} tabIndex={-1} disableRipple />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" fontWeight={600}>
                          #{p.id} — {p.destinatario || p.cliente}
                        </Typography>
                        <Chip
                          size="small"
                          label={moneyBRL(p.taxa_entrega)}
                          color="success"
                          variant="outlined"
                        />
                      </Stack>
                    }
                    secondary={
                      <Box component="span" sx={{ display: 'block' }}>
                        <Typography component="span" variant="caption" color="text.secondary">
                          {p.dia_entrega} {p.horario && `· ${p.horario}`}
                        </Typography>
                        <br />
                        <Typography component="span" variant="caption" color="text.secondary">
                          {p.endereco || `${p.rua || ''} ${p.numero || ''}, ${p.bairro || ''}`}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItemButton>
              );
            })}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Box sx={{ flex: 1, pl: 1 }}>
          <Typography variant="caption" color="text.secondary">
            {selected.size} selecionada(s) · Total: {moneyBRL(total)}
          </Typography>
        </Box>
        <Button onClick={onClose} disabled={atribuir.isPending}>
          Cancelar
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={selected.size === 0 || atribuir.isPending}
        >
          Atribuir
        </Button>
      </DialogActions>
    </Dialog>
  );
}
