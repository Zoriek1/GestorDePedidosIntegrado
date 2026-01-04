import { useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Stack,
  Divider,
  Button,
  Chip,
  Avatar,
} from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { usePedido } from '../../api/endpoints/pedidos';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { formatBRL } from '../../lib/format/currency';
import { useToast } from '../../components/system/useToast';
import { useDeletePedido } from '../../api/endpoints/pedidos';
import { useConfirm } from '../../components/system/useConfirm';
import { useAuth } from '../auth/authStore';
import { usePedidoPrintService } from './services/PedidoPrintService';
import { getStatusColor, getStatusLabel } from './useCases/orderMapping';
import PersonIcon from '@mui/icons-material/Person';
import Inventory2Icon from '@mui/icons-material/Inventory2';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import PaidIcon from '@mui/icons-material/Paid';

export default function OrderDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const pedidoId = useMemo(() => Number(id), [id]);

  const { data, isLoading, error, refetch } = usePedido(pedidoId);
  const { success, error: showError } = useToast();
  const deletePedido = useDeletePedido();
  const confirm = useConfirm();
  const { getCredentials } = useAuth();
  const printService = usePedidoPrintService();

  const pedido = data?.pedido;

  const renderRow = (label: string, value?: string | number | null) => {
    if (value === undefined || value === null || value === '') return null;
    return (
      <Box>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="body1">{value}</Typography>
      </Box>
    );
  };

  if (isLoading) return <Loading />;
  if (error) return <ErrorState message={error.message || 'Erro ao carregar pedido'} onRetry={() => refetch()} />;
  if (!pedido) return <ErrorState message="Pedido não encontrado" onRetry={() => refetch()} />;

  const handleDelete = async () => {
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
      navigate('/');
    } catch (err: any) {
      showError(err?.message || 'Erro ao deletar pedido');
    }
  };

  const handlePrint = async () => {
    try {
      await printService.print(pedido.id);
      success('Impressão iniciada');
    } catch (err: any) {
      showError(err?.message || 'Erro ao imprimir');
    }
  };

  const statusLabel = getStatusLabel(pedido.status);
  const statusColor = getStatusColor(pedido.status);
  const valorTotal = pedido.valor ? formatBRL(pedido.valor) : 'R$ 0,00';
  const entregaData = pedido.dia_entrega ? dayjs(pedido.dia_entrega).format('DD/MM/YYYY') : '-';
  const entregaHora = pedido.horario || '-';

  return (
    <Box>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        mb={2}
        spacing={2}
        flexWrap="wrap"
      >
        <Stack spacing={1}>
          <Typography variant="h4" component="h1">
            Pedido #{pedido.id}
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Chip label={statusLabel} color={statusColor} />
            {pedido.tipo_pedido && <Chip label={pedido.tipo_pedido} variant="outlined" />}
            {pedido.fonte_pedido_nome && <Chip label={`Fonte: ${pedido.fonte_pedido_nome}`} variant="outlined" />}
          </Stack>
        </Stack>
        <Stack direction="row" spacing={1} flexWrap="wrap" justifyContent="flex-end">
          <Button variant="outlined" onClick={() => navigate(-1)}>
            Voltar
          </Button>
          <Button variant="outlined" onClick={() => navigate(`/pedidos/${pedido.id}/editar`)}>
            Editar
          </Button>
          <Button variant="contained" color="primary" onClick={handlePrint}>
            Imprimir
          </Button>
          <Button variant="outlined" color="error" onClick={handleDelete}>
            Deletar
          </Button>
        </Stack>
      </Stack>

      {/* Resumo rápido */}
      <Paper
        sx={{
          p: 3,
          mb: 3,
          display: 'flex',
          flexWrap: 'wrap',
          gap: 3,
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Stack spacing={0.5}>
          <Typography variant="body2" color="text.secondary">
            Valor Total
          </Typography>
          <Typography variant="h5" fontWeight="bold">
            {valorTotal}
          </Typography>
        </Stack>
        <Stack spacing={0.5}>
          <Typography variant="body2" color="text.secondary">
            Entrega
          </Typography>
          <Typography variant="body1">
            {entregaData} {entregaHora && `• ${entregaHora}`}
          </Typography>
        </Stack>
        <Stack spacing={0.5}>
          <Typography variant="body2" color="text.secondary">
            Tipo
          </Typography>
          <Typography variant="body1">{pedido.tipo_pedido || '-'}</Typography>
        </Stack>
      </Paper>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Stack direction="row" alignItems="center" spacing={1} mb={1}>
              <Avatar sx={{ bgcolor: 'primary.light', color: 'primary.main', width: 32, height: 32 }}>
                <PersonIcon fontSize="small" />
              </Avatar>
              <Typography variant="h6">Cliente</Typography>
            </Stack>
            <Divider sx={{ mb: 2 }} />
            <Stack spacing={1.5}>
              {renderRow('Nome', pedido.cliente)}
              {renderRow('Telefone', pedido.telefone_cliente)}
              {renderRow('Destinatário', pedido.destinatario)}
              {renderRow('Fonte do Pedido', pedido.fonte_pedido_nome || pedido.fonte_pedido)}
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Stack direction="row" alignItems="center" spacing={1} mb={1}>
              <Avatar sx={{ bgcolor: 'warning.light', color: 'warning.main', width: 32, height: 32 }}>
                <Inventory2Icon fontSize="small" />
              </Avatar>
              <Typography variant="h6">Produto</Typography>
            </Stack>
            <Divider sx={{ mb: 2 }} />
            <Stack spacing={1.5}>
              {renderRow('Descrição', pedido.produto)}
              {renderRow('Flores / Cor', pedido.flores_cor)}
              {renderRow('Mensagem', pedido.mensagem)}
              {renderRow('Quantidade', pedido.quantidade)}
              {renderRow('Valor', valorTotal)}
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Stack direction="row" alignItems="center" spacing={1} mb={1}>
              <Avatar sx={{ bgcolor: 'info.light', color: 'info.main', width: 32, height: 32 }}>
                <LocalShippingIcon fontSize="small" />
              </Avatar>
              <Typography variant="h6">Logística</Typography>
            </Stack>
            <Divider sx={{ mb: 2 }} />
            <Stack spacing={1.5}>
              {renderRow('Tipo', pedido.tipo_pedido)}
              {renderRow('Data', entregaData)}
              {renderRow('Horário', pedido.horario)}
              {renderRow('CEP', pedido.cep)}
              {renderRow('Endereço', pedido.endereco)}
              {renderRow('Bairro', pedido.bairro)}
              {renderRow('Cidade', pedido.cidade)}
              {renderRow('Observações de Entrega', pedido.obs_entrega)}
              {renderRow(
                'Taxa de Entrega',
                pedido.taxa_entrega !== undefined ? formatBRL(pedido.taxa_entrega) : undefined,
              )}
              {renderRow(
                'Distância',
                pedido.distancia_km !== undefined && pedido.distancia_km !== null
                  ? `${pedido.distancia_km.toFixed(2)} km`
                  : undefined,
              )}
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Stack direction="row" alignItems="center" spacing={1} mb={1}>
              <Avatar sx={{ bgcolor: 'success.light', color: 'success.main', width: 32, height: 32 }}>
                <PaidIcon fontSize="small" />
              </Avatar>
              <Typography variant="h6">Financeiro</Typography>
            </Stack>
            <Divider sx={{ mb: 2 }} />
            <Stack spacing={1.5}>
              {renderRow('Pagamento', pedido.pagamento)}
              {renderRow('Status Pagamento', pedido.status_pagamento)}
              {renderRow('Observações', pedido.observacoes)}
              {renderRow('Criado em', pedido.created_at ? dayjs(pedido.created_at).format('DD/MM/YYYY HH:mm') : undefined)}
              {renderRow(
                'Atualizado em',
                pedido.updated_at ? dayjs(pedido.updated_at).format('DD/MM/YYYY HH:mm') : undefined,
              )}
              {renderRow('Impresso', pedido.impresso ? 'Sim' : 'Não')}
              {renderRow('Oculto', pedido.oculto ? 'Sim' : 'Não')}
            </Stack>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
