import { useState } from 'react';
import { FormControl, InputLabel, Select, MenuItem, CircularProgress } from '@mui/material';
import { Box, Chip } from '@mui/material';
import { useUpdatePedidoStatus } from '../../../api/endpoints/pedidos';
import { useToast } from '../../../components/system/useToast';
import { getStatusColor, getStatusLabel } from '../useCases/orderMapping';

const STATUS_OPTIONS: Record<'Entrega' | 'Retirada', string[]> = {
  Entrega: ['agendado', 'em_producao', 'pronto_entrega', 'em_rota', 'concluido'],
  Retirada: ['agendado', 'em_producao', 'pronto_retirada', 'concluido'],
};

interface StatusSelectorProps {
  pedidoId: number;
  status: string;
}

export function StatusSelector({ pedidoId, status }: StatusSelectorProps) {
  const [value, setValue] = useState(status);
  const mutation = useUpdatePedidoStatus();
  const { error: showError, success } = useToast();

  const handleChange = async (event: { target: { value: string } }) => {
    const newStatus = event.target.value;
    setValue(newStatus);
    try {
      await mutation.mutateAsync({ id: pedidoId, status: newStatus });
      success('Status atualizado');
    } catch {
      // rollback on error
      setValue(status);
      showError('Erro ao atualizar status');
    }
  };

  const tipo = status === 'pronto_retirada' ? 'Retirada' : 'Entrega';
  const options = tipo === 'Retirada' ? STATUS_OPTIONS.Retirada : STATUS_OPTIONS.Entrega;

  return (
    <FormControl fullWidth size="small">
      <InputLabel>Status</InputLabel>
      <Select
        label="Status"
        value={value}
        onChange={handleChange}
        disabled={mutation.isPending}
        IconComponent={mutation.isPending ? () => <CircularProgress size={18} /> : undefined}
      >
        {options.map((opt) => {
          const label = getStatusLabel(opt);
          const color = getStatusColor(opt);
          return (
            <MenuItem key={opt} value={opt}>
              <Box display="flex" alignItems="center" gap={1}>
                <Chip label={label} size="small" color={color} />
              </Box>
            </MenuItem>
          );
        })}
      </Select>
    </FormControl>
  );
}

export default StatusSelector;

