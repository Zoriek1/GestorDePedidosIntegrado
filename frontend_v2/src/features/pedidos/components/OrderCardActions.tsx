import { Stack, Button, IconButton, Tooltip } from '@mui/material';
import { Visibility, Edit, Print, Calculate, Delete } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../../../components/system/useToast';
import { useCalcularDistanciaPedido, useCalcularTaxaEntrega, useDeletePedido } from '../../../api/endpoints/pedidos';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { useConfirm } from '../../../components/system/useConfirm';
import { useAuth } from '../../auth/authStore';
import { usePedidoPrintService } from '../services/PedidoPrintService';

interface OrderCardActionsProps {
  pedido: Pedido;
}

export function OrderCardActions({ pedido }: OrderCardActionsProps) {
  const navigate = useNavigate();
  const { success, error: showError } = useToast();
  const calcDistancia = useCalcularDistanciaPedido();
  const calcTaxa = useCalcularTaxaEntrega();
  const deletePedido = useDeletePedido();
  const confirm = useConfirm();
  const { getCredentials } = useAuth();
  const printService = usePedidoPrintService();

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

  const handleCalcularEntrega = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await calcDistancia.mutateAsync({ id: pedido.id, forceRecalc: true });
      await calcTaxa.mutateAsync({ id: pedido.id });
      success('Entrega recalculada (distância e taxa)');
    } catch (err: any) {
      showError(err?.message || 'Erro ao calcular entrega');
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
    } catch (err: any) {
      showError(err?.message || 'Erro ao deletar pedido');
    }
  };

  return (
    <Stack spacing={2}>
      {/* Primeira linha: Ações de visualização e edição */}
      <Stack 
        direction="row" 
        spacing={{ xs: 1.5, sm: 1 }} 
        flexWrap="wrap"
        justifyContent={{ xs: 'center', sm: 'flex-start' }}
        sx={{ gap: { xs: 1, sm: 1 } }}
      >
        <Tooltip title="Ver detalhes">
          <IconButton 
            size="small" 
            onClick={handleView} 
            color="primary"
            sx={{ 
              minWidth: { xs: 44, sm: 40 },
              minHeight: { xs: 44, sm: 40 },
            }}
          >
            <Visibility fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Editar pedido">
          <IconButton 
            size="small" 
            onClick={handleEdit} 
            color="primary"
            sx={{ 
              minWidth: { xs: 44, sm: 40 },
              minHeight: { xs: 44, sm: 40 },
            }}
          >
            <Edit fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Imprimir pedido">
          <IconButton 
            size="small" 
            onClick={handlePrint} 
            color="primary"
            sx={{ 
              minWidth: { xs: 44, sm: 40 },
              minHeight: { xs: 44, sm: 40 },
            }}
          >
            <Print fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
      
      {/* Segunda linha: Ações críticas */}
      <Stack 
        direction={{ xs: 'column', sm: 'row' }} 
        spacing={{ xs: 1.5, sm: 1 }} 
        flexWrap="wrap"
        justifyContent={{ xs: 'center', sm: 'flex-start' }}
        alignItems={{ xs: 'stretch', sm: 'center' }}
        sx={{ gap: { xs: 1, sm: 1 } }}
      >
        <Tooltip title="Recalcular distância e taxa de entrega">
          <span>
            <Button
              size="small"
              variant="contained"
              startIcon={<Calculate />}
              onClick={handleCalcularEntrega}
              disabled={isLoadingEntrega}
              sx={{ 
                width: { xs: '100%', sm: 160 },
                minHeight: { xs: 44, sm: 36 },
              }}
            >
              {isLoadingEntrega ? 'Calculando...' : 'Calcular entrega'}
            </Button>
          </span>
        </Tooltip>
        <Tooltip title="Deletar pedido permanentemente">
          <span>
            <IconButton
              size="small"
              onClick={handleDelete}
              disabled={isDeleting}
              color="error"
              sx={{ 
                minWidth: { xs: 44, sm: 40 },
                minHeight: { xs: 44, sm: 40 },
              }}
            >
              <Delete fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      </Stack>
    </Stack>
  );
}

export default OrderCardActions;

