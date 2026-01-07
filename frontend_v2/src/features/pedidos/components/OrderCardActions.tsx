import { Stack, Button, IconButton, Tooltip } from '@mui/material';
import { Visibility, Edit, Print, Calculate, Delete } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../../../components/system/useToast';
import { useCalcularDistanciaPedido, useCalcularTaxaEntrega, useDeletePedido } from '../../../api/endpoints/pedidos';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { useConfirm } from '../../../components/system/useConfirm';
import { useAuth } from '../../auth/authStore';
import { usePedidoPrintService } from '../services/PedidoPrintService';

function hasPermission(role: string | null, permission: string): boolean {
  if (!role) return false;
  if (role === 'admin') return true;
  if (role === 'atendente') {
    return ['pedidos:create', 'pedidos:update', 'pedidos:view'].includes(permission);
  }
  if (role === 'entregador') {
    return ['pedidos:view', 'pedidos:update_status'].includes(permission);
  }
  return false;
}

interface OrderCardActionsProps {
  pedido: Pedido;
  showRecalcButtons?: boolean;
  compact?: boolean;
}

export function OrderCardActions({ pedido, showRecalcButtons = false, compact = false }: OrderCardActionsProps) {
  const navigate = useNavigate();
  const { success, error: showError } = useToast();
  const calcDistancia = useCalcularDistanciaPedido();
  const calcTaxa = useCalcularTaxaEntrega();
  const deletePedido = useDeletePedido();
  const confirm = useConfirm();
  const { getCredentials, getUserRole } = useAuth();
  const printService = usePedidoPrintService();
  
  const userRole = getUserRole();
  const canEdit = hasPermission(userRole, 'pedidos:update');
  const canDelete = userRole === 'admin';

  const isLoadingEntrega = calcDistancia.isPending || calcTaxa.isPending;
  const isDeleting = deletePedido.isPending;

  const handleView = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/pedidos/${pedido.id}`);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/pedidos/${pedido.id}/editar`);
  };

  const handlePrint = (e: React.MouseEvent) => {
    e.stopPropagation();
    printService
      .print(pedido.id)
      .then(() => success('Impressão iniciada'))
      .catch((err) => showError(err?.message || 'Erro ao imprimir'));
  };

  const handleCalcularDistancia = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await calcDistancia.mutateAsync({ id: pedido.id, forceRecalc: true });
      success('Distância recalculada');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao calcular distância';
      showError(errorMessage);
    }
  };

  const handleCalcularTaxa = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await calcTaxa.mutateAsync({ id: pedido.id });
      success('Taxa recalculada');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao calcular taxa';
      showError(errorMessage);
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const confirmed = await confirm({
      title: 'Deletar pedido',
      description: 'Esta ação é permanente. Confirme para prosseguir.',
      confirmColor: 'error',
      confirmText: 'Deletar',
    });
    if (!confirmed) return;

    const creds = getCredentials();
    const input = window.prompt('Digite sua senha para confirmar a exclusão:');
    if (!input) {
      showError('Exclusão cancelada: senha não informada');
      return;
    }
    if (!creds || input !== creds.password) {
      showError('Senha incorreta');
      return;
    }

    try {
      await deletePedido.mutateAsync(pedido.id);
      success('Pedido deletado');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao deletar pedido';
      showError(errorMessage);
    }
  };

  // Modo compacto: apenas botões de recalcular (para caixa de entrega)
  if (compact && showRecalcButtons) {
    return (
      <Stack direction="row" spacing={1}>
        <Tooltip title="Recalcular distância">
          <IconButton
            size="small"
            onClick={handleCalcularDistancia}
            disabled={isLoadingEntrega}
            color="primary"
          >
            <Calculate fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Recalcular taxa">
          <IconButton
            size="small"
            onClick={handleCalcularTaxa}
            disabled={isLoadingEntrega}
            color="primary"
          >
            <Calculate fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
    );
  }

  // Modo normal: barra de ações completa
  return (
    <Stack spacing={2}>
      {/* Botões principais: Imprimir, Ver, Editar */}
      <Stack 
        direction={{ xs: 'column', sm: 'row' }} 
        spacing={1.5}
        flexWrap="wrap"
      >
        <Button
          variant="contained"
          color="primary"
          startIcon={<Print />}
          onClick={handlePrint}
          fullWidth={false}
          sx={{ 
            minWidth: { xs: '100%', sm: 120 },
            flex: { xs: '1 1 100%', sm: '0 1 auto' },
          }}
        >
          Imprimir
        </Button>
        <Button
          variant="contained"
          color="primary"
          startIcon={<Visibility />}
          onClick={handleView}
          fullWidth={false}
          sx={{ 
            minWidth: { xs: '100%', sm: 120 },
            flex: { xs: '1 1 100%', sm: '0 1 auto' },
          }}
        >
          Ver
        </Button>
        {canEdit && (
          <Button
            variant="contained"
            color="primary"
            startIcon={<Edit />}
            onClick={handleEdit}
            fullWidth={false}
            sx={{ 
              minWidth: { xs: '100%', sm: 120 },
              flex: { xs: '1 1 100%', sm: '0 1 auto' },
            }}
          >
            Editar
          </Button>
        )}
      </Stack>

      {/* Botão secundário/perigoso: Deletar */}
      {canDelete && (
        <Button
          variant="outlined"
          color="error"
          startIcon={<Delete />}
          onClick={handleDelete}
          disabled={isDeleting}
          fullWidth
        >
          {isDeleting ? 'Deletando...' : 'Deletar'}
        </Button>
      )}
    </Stack>
  );
}

export default OrderCardActions;
