import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  Typography,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  IconButton,
  Alert,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import { AppButton } from '../../components/common/AppButton';
import { useListVendedores, useAssignVendorNuvemshop } from '../../api/endpoints/nuvemshop';
import { useToast } from '../../components/system/useToast';

interface AssignVendorModalProps {
  open: boolean;
  onClose: () => void;
}

export function AssignVendorModal({ open, onClose }: AssignVendorModalProps) {
  const { data: vendedores, isLoading: loadingVendedores } = useListVendedores();
  const assign = useAssignVendorNuvemshop();
  const { success, error: toastError } = useToast();
  const [vendedorId, setVendedorId] = useState<number | ''>('');

  const handleConfirm = () => {
    if (!vendedorId) return;
    assign.mutate(vendedorId, {
      onSuccess: (data) => {
        const count = (data as { atribuidos: number }).atribuidos;
        success(`${count} pedido(s) receberam vendedor via backfill`);
        setVendedorId('');
        onClose();
      },
      onError: (err) => toastError((err as Error).message),
    });
  };

  const handleClose = () => {
    setVendedorId('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" spacing={1}>
          <PersonAddIcon fontSize="small" />
          <Typography variant="h6" fontWeight={700} sx={{ flexGrow: 1 }}>
            Backfill de vendedor nos pedidos do site
          </Typography>
          <IconButton size="small" onClick={handleClose}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Stack>
      </DialogTitle>

      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Esta acao atribui o vendedor apenas aos pedidos ja importados da Nuvemshop que ainda
            nao tem vendedor. Ela nao salva o vendedor padrao da loja para os proximos pedidos.
          </Typography>

          <FormControl fullWidth>
            <InputLabel id="vendedor-select-label">Vendedor</InputLabel>
            <Select
              labelId="vendedor-select-label"
              value={vendedorId}
              label="Vendedor"
              onChange={(e) => setVendedorId(e.target.value as number)}
              disabled={loadingVendedores}
            >
              {(vendedores ?? []).map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {assign.isError && <Alert severity="error">{(assign.error as Error)?.message}</Alert>}
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <AppButton variant="outlined" onClick={handleClose} disabled={assign.isPending}>
          Cancelar
        </AppButton>
        <AppButton
          variant="contained"
          onClick={handleConfirm}
          loading={assign.isPending}
          disabled={!vendedorId}
        >
          Fazer backfill
        </AppButton>
      </DialogActions>
    </Dialog>
  );
}
