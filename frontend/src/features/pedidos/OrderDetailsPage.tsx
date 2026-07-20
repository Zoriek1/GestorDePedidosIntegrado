import { useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Divider,
  Button,
  Chip,
} from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { pedidoDisplayNumber, usePedido } from '../../api/endpoints/pedidos';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { formatBRL } from '../../lib/format/currency';
import { useToast } from '../../components/system/useToast';
import { useDeletePedido } from '../../api/endpoints/pedidos';
import { useConfirm } from '../../components/system/useConfirm';
import { useAuth } from '../auth/authStore';
import { usePedidoPrintService } from './services/PedidoPrintService';
import { getStatusColor, getStatusLabel } from './useCases/orderMapping';
import { buildEncaminharMensagem } from './components/OrderCardHelpers';
import { copyToClipboard } from '../../lib/utils/clipboard';
import { formatOrderSourceLabel } from './utils/sourceLabel';
import { useUsers } from '../users/services/userApi';
import { BlingIntegrationCard } from './components/BlingIntegrationCard';
import { AddressSuggestionsCard } from './components/AddressSuggestionsCard';

type StatusPagamentoColor = 'success' | 'warning' | 'default' | 'error';

const getStatusPagamentoColor = (status?: string | null): StatusPagamentoColor => {
  const s = (status || '').toLowerCase();
  if (s === 'pago') return 'success';
  if (s === 'parcial') return 'warning';
  if (s === 'cancelado') return 'error';
  return 'default';
};

export default function OrderDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const pedidoId = useMemo(() => Number(id), [id]);

  const { data, isLoading, error, refetch } = usePedido(pedidoId);
  const { success, error: showError } = useToast();
  const deletePedido = useDeletePedido();
  const confirm = useConfirm();
  const { getCredentials, getUserRole, getUser, isJwtUser } = useAuth();
  const printService = usePedidoPrintService();
  const { data: users } = useUsers(getUserRole() === 'admin');

  const pedido = data?.pedido;
  const currentUser = getUser();
  const sellerNameById = useMemo<Record<number, string>>(() => {
    const map: Record<number, string> = {};
    (users || []).forEach((user) => {
      map[user.id] = user.name;
    });
    if (currentUser?.id && currentUser?.name) {
      map[currentUser.id] = currentUser.name;
    }
    return map;
  }, [users, currentUser]);

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

    if (!isJwtUser()) {
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
    }

    try {
      await deletePedido.mutateAsync(pedido.id);
      success('Pedido deletado');
      navigate('/');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao deletar pedido';
      showError(errorMessage);
    }
  };

  const handlePrint = async () => {
    try {
      await printService.print(pedido.id);
      success('Impressão iniciada');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao imprimir';
      showError(errorMessage);
    }
  };

  const handleEncaminhar = async () => {
    const texto = buildEncaminharMensagem(pedido);
    const copied = await copyToClipboard(texto);
    if (copied) {
      success('Encaminhamento copiado!');
    } else {
      showError('Erro ao copiar encaminhamento');
    }
  };

  const statusLabel = getStatusLabel(pedido.status);
  const statusColor = getStatusColor(pedido.status);
  const valorTotal = pedido.valor ? formatBRL(pedido.valor) : 'R$ 0,00';
  const entregaData = pedido.dia_entrega ? dayjs(pedido.dia_entrega).format('DD/MM/YYYY') : '-';
  const entregaHora = pedido.horario || '';
  const isRetirada = (pedido.tipo_pedido || '').toLowerCase() === 'retirada';
  const isMesmaPessoa =
    (pedido.cliente || '').trim().toLowerCase() ===
    (pedido.destinatario || '').trim().toLowerCase();

  const sourceLabel = formatOrderSourceLabel({
    sourceName: pedido.fonte_pedido_nome,
    legacySource: pedido.fonte_pedido,
    vendedorId: pedido.vendedor_id,
    vendedorName: pedido.vendedor_id ? sellerNameById[pedido.vendedor_id] : undefined,
  });

  const statusPagtoColor = getStatusPagamentoColor(pedido.status_pagamento);
  const enderecoCompleto = pedido.endereco
    ? pedido.endereco
    : [pedido.rua, pedido.numero].filter(Boolean).join(', ') || null;

  const heroItem = (label: string, value: React.ReactNode, emphasis = false) => (
    <Stack spacing={0.5} sx={{ minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {label}
      </Typography>
      <Typography
        variant={emphasis ? 'h5' : 'body1'}
        fontWeight={emphasis ? 700 : 500}
        sx={{ wordBreak: 'break-word' }}
      >
        {value}
      </Typography>
    </Stack>
  );

  const inlineRow = (label: string, value?: string | number | null) => {
    if (value === undefined || value === null || value === '') return null;
    return (
      <Stack direction="row" spacing={1} alignItems="baseline" flexWrap="wrap">
        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, minWidth: 110 }}>
          {label}
        </Typography>
        <Typography variant="body1" fontWeight={500} sx={{ wordBreak: 'break-word' }}>
          {value}
        </Typography>
      </Stack>
    );
  };

  const sectionTitle = (text: string) => (
    <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 1.2, fontWeight: 700 }}>
      {text}
    </Typography>
  );

  return (
    <Box>
      {/* Action bar */}
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
            Pedido #{pedidoDisplayNumber(pedido)}
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Chip label={statusLabel} color={statusColor} />
            {pedido.tipo_pedido && <Chip label={pedido.tipo_pedido} variant="outlined" />}
            {(pedido.fonte_pedido_nome || pedido.fonte_pedido) && (
              <Chip label={`Fonte: ${sourceLabel}`} variant="outlined" />
            )}
          </Stack>
        </Stack>
        <Stack direction="row" spacing={1} flexWrap="wrap" justifyContent="flex-end">
          <Button variant="outlined" onClick={() => navigate(-1)}>
            Voltar
          </Button>
          <Button variant="outlined" onClick={() => navigate(`/pedidos/${pedido.id}/editar`)}>
            Editar
          </Button>
          <Button variant="outlined" onClick={handleEncaminhar}>
            Encaminhar
          </Button>
          <Button variant="contained" color="primary" onClick={handlePrint}>
            Imprimir
          </Button>
          <Button variant="outlined" color="error" onClick={handleDelete}>
            Deletar
          </Button>
        </Stack>
      </Stack>

      {/* Hero card — informação prioritária */}
      <Paper
        sx={{
          p: { xs: 2.5, md: 3 },
          mb: 2,
          background: (theme) =>
            `linear-gradient(135deg, ${theme.palette.primary.light}1A, ${theme.palette.background.paper})`,
          borderLeft: (theme) => `4px solid ${theme.palette.primary.main}`,
        }}
      >
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={{ xs: 2, md: 4 }}
          divider={<Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', md: 'block' } }} />}
          alignItems={{ xs: 'flex-start', md: 'center' }}
        >
          {heroItem('Cliente', pedido.cliente || '-', true)}
          {heroItem(
            isRetirada ? 'Retirada' : 'Entrega',
            <>
              {entregaData}
              {entregaHora && (
                <Typography component="span" variant="body1" color="text.secondary" sx={{ ml: 1 }}>
                  {entregaHora}
                </Typography>
              )}
            </>,
          )}
          {heroItem('Valor', valorTotal, true)}
          {heroItem('Pagamento', (
            <Chip
              label={pedido.status_pagamento || 'Pendente'}
              color={statusPagtoColor}
              size="small"
              sx={{ fontWeight: 700 }}
            />
          ))}
        </Stack>
      </Paper>

      {/* Mensagem do cartão — destaque */}
      {pedido.mensagem && (
        <Paper
          sx={{
            p: { xs: 2.5, md: 3 },
            mb: 2,
            border: '2px dashed',
            borderColor: 'warning.light',
            backgroundColor: '#fff8e1',
          }}
        >
          {sectionTitle('Mensagem do cartão')}
          <Typography
            variant="h6"
            sx={{
              mt: 1,
              fontStyle: 'italic',
              fontWeight: 500,
              whiteSpace: 'pre-wrap',
              lineHeight: 1.5,
            }}
          >
            “{pedido.mensagem}”
          </Typography>
        </Paper>
      )}

      {/* Destinatário (se diferente do cliente) */}
      {!isMesmaPessoa && pedido.destinatario && (
        <Paper sx={{ p: 2.5, mb: 2 }}>
          {sectionTitle('Destinatário')}
          <Stack spacing={1} mt={1}>
            {inlineRow('Nome', pedido.destinatario)}
            {inlineRow('Telefone', pedido.telefone_cliente)}
          </Stack>
        </Paper>
      )}

      {/* Produto */}
      <Paper sx={{ p: 2.5, mb: 2 }}>
        {sectionTitle('Produto')}
        <Stack spacing={1} mt={1}>
          {inlineRow('Descrição', pedido.produto)}
          {inlineRow('Flores / Cor', pedido.flores_cor)}
          {inlineRow('Quantidade', pedido.quantidade)}
        </Stack>
      </Paper>

      {/* Sugestões de correção de endereço do cliente (pendentes) */}
      {!isRetirada && <AddressSuggestionsCard pedidoId={pedido.id} />}

      {/* Logística */}
      <Paper sx={{ p: 2.5, mb: 2 }}>
        {sectionTitle(isRetirada ? 'Retirada' : 'Endereço de entrega')}
        <Stack spacing={1} mt={1}>
          {isRetirada ? (
            <Typography variant="body1" fontWeight={600}>
              Retirada na loja em {entregaData}
              {entregaHora && ` · ${entregaHora}`}
            </Typography>
          ) : (
            <>
              {enderecoCompleto && (
                <Typography variant="body1" fontWeight={600}>
                  {enderecoCompleto}
                </Typography>
              )}
              <Stack direction="row" spacing={3} flexWrap="wrap" useFlexGap>
                {pedido.bairro && inlineRow('Bairro', pedido.bairro)}
                {pedido.cidade && inlineRow('Cidade', pedido.cidade)}
                {pedido.cep && inlineRow('CEP', pedido.cep)}
                {pedido.distancia_km !== undefined &&
                  pedido.distancia_km !== null &&
                  inlineRow('Distância', `${pedido.distancia_km.toFixed(2)} km`)}
                {pedido.taxa_entrega !== undefined &&
                  pedido.taxa_entrega !== null &&
                  inlineRow('Taxa', formatBRL(pedido.taxa_entrega))}
              </Stack>
              {pedido.obs_entrega && (
                <Box
                  sx={{
                    mt: 1,
                    p: 1.5,
                    bgcolor: '#e3f2fd',
                    borderLeft: '3px solid',
                    borderColor: 'info.main',
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase' }}>
                    Observação de entrega
                  </Typography>
                  <Typography variant="body1" fontWeight={500} sx={{ whiteSpace: 'pre-wrap' }}>
                    {pedido.obs_entrega}
                  </Typography>
                </Box>
              )}
            </>
          )}
        </Stack>
      </Paper>

      {/* Pagamento */}
      <Paper sx={{ p: 2.5, mb: 2 }}>
        {sectionTitle('Pagamento')}
        <Stack spacing={1} mt={1}>
          {inlineRow('Forma', pedido.pagamento)}
          {pedido.status_pagamento === 'Parcial' && (
            <>
              {inlineRow('Entrada', pedido.valor_entrada != null ? formatBRL(pedido.valor_entrada) : null)}
              {inlineRow('Forma entrada', pedido.forma_pagamento_entrada)}
              {inlineRow('Saldo', pedido.valor_restante != null ? formatBRL(pedido.valor_restante) : null)}
              {inlineRow('Forma saldo', pedido.forma_pagamento_restante)}
            </>
          )}
          <Stack direction="row" spacing={1} alignItems="baseline" flexWrap="wrap">
            <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, minWidth: 110 }}>
              Status
            </Typography>
            <Chip
              label={pedido.status_pagamento || 'Pendente'}
              color={statusPagtoColor}
              size="small"
              sx={{ fontWeight: 700 }}
            />
          </Stack>
          {pedido.observacoes && (
            <Box
              sx={{
                mt: 1,
                p: 1.5,
                bgcolor: 'grey.100',
                borderRadius: 1,
              }}
            >
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase' }}>
                Observações
              </Typography>
              <Typography variant="body1" fontWeight={500} sx={{ whiteSpace: 'pre-wrap' }}>
                {pedido.observacoes}
              </Typography>
            </Box>
          )}
        </Stack>
      </Paper>

      {/* Metadados — rodapé discreto */}
      <BlingIntegrationCard pedidoId={pedido.id} />

      <Divider sx={{ my: 2 }} />
      <Stack
        direction="row"
        spacing={2}
        flexWrap="wrap"
        useFlexGap
        sx={{ pb: 2 }}
      >
        {pedido.created_at && (
          <Typography variant="caption" color="text.secondary">
            Criado em {dayjs(pedido.created_at).format('DD/MM/YYYY HH:mm')}
          </Typography>
        )}
        {pedido.updated_at && (
          <Typography variant="caption" color="text.secondary">
            Atualizado em {dayjs(pedido.updated_at).format('DD/MM/YYYY HH:mm')}
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary">
          Impresso: {pedido.impresso ? 'Sim' : 'Não'}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Oculto: {pedido.oculto ? 'Sim' : 'Não'}
        </Typography>
      </Stack>
    </Box>
  );
}
