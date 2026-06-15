/**
 * Order Card component - Operacional Layout
 * Exibe informações completas do pedido de forma operacional
 */

import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Chip, 
  Divider, 
  Stack, 
  Checkbox, 
  Tooltip,
  Paper,
  Button,
  IconButton,
  Menu,
  MenuItem,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  Person,
  PersonAdd,
  Phone,
  LocalShipping,
  Store,
  Calculate,
  MoreVert,
  WhatsApp,
  ContentCopy,
  PlayArrow,
  LocalShipping as LocalShippingIcon,
  CheckCircle,
  RadioButtonUnchecked,
  Place,
  Undo,
  Home,
  Apartment,
} from '@mui/icons-material';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { formatDateBR } from '../../../lib/format/date';
import { formatBRL } from '../../../lib/format/currency';
import { getStatusColor, getStatusLabel, getPaymentStatusColor, getPaymentStatusLabel } from '../useCases/orderMapping';
import { StatusSelector } from './StatusSelector';
import {
  isPedidoAtrasado,
  formatPhone,
  getEnderecoCompleto,
  buildEncaminharMensagem,
  getTipoLocalLabel,
  getDetalheLocal,
} from './OrderCardHelpers';
import { useCalcularDistanciaPedido, useCalcularTaxaEntrega, useUpdatePedido, useToggleCartaoImpresso, useTrackLink } from '../../../api/endpoints/pedidos';
import { useToast } from '../../../components/system/useToast';
import { CopyOnClick } from '../../../components/common/CopyOnClick';
import { copyToClipboard } from '../../../lib/utils/clipboard';
import { useAuth } from '../../auth/authStore';
import { usePedidoPrintService } from '../services/PedidoPrintService';
import { useConfirm } from '../../../components/system/useConfirm';
import { useDeletePedido } from '../../../api/endpoints/pedidos';
import dayjs from 'dayjs';
import { formatOrderSourceLabel } from '../utils/sourceLabel';
import { useFinalizarEntrega, useAtribuirEntregadorPedido } from '../../entregas/services/entregasApi';
import { canFinalizarEntrega, isEntregador } from '../../auth/roleHelpers';

export type SelectionMode = 'route' | 'print' | 'pickup';

interface OrderCardProps {
  pedido: Pedido;
  sellerNameById?: Record<number, string>;
  onClick?: () => void;
  selectable?: boolean;
  selected?: boolean;
  onToggleSelect?: (pedido: Pedido) => void;
  selectionMode?: SelectionMode;
  /** Variante enxuta (usada no Kanban): só o essencial, sem ações pesadas. */
  compact?: boolean;
  /** Variante operacional do entregador (VIS-02): foco em entrega + ações do fluxo. */
  operacional?: boolean;
}

export function OrderCard({
  pedido,
  sellerNameById,
  onClick,
  selectable = false,
  selected = false,
  onToggleSelect,
  selectionMode = 'route',
  compact = false,
  operacional = false,
}: OrderCardProps) {
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const statusColor = getStatusColor(pedido.status);
  const statusLabel = getStatusLabel(pedido.status);
  const isAtrasado = isPedidoAtrasado(pedido);
  const enderecoCompleto = getEnderecoCompleto(pedido);
  const calcDistancia = useCalcularDistanciaPedido();
  const calcTaxa = useCalcularTaxaEntrega();
  const updatePedido = useUpdatePedido();
  const deletePedido = useDeletePedido();
  const toggleCartaoImpresso = useToggleCartaoImpresso();
  const trackLink = useTrackLink();
  const { success, error: showError } = useToast();
  const { getUserRole, getUser } = useAuth();
  const printService = usePedidoPrintService();
  const confirm = useConfirm();

  const userRole = getUserRole();
  const canEdit = userRole === 'admin' || userRole === 'atendente' || userRole === 'vendedor';
  // Admin sempre; vendedor apenas se for dono (o backend reforça)
  const currentUser = getUser();
  const canDelete =
    userRole === 'admin' ||
    (userRole === 'vendedor' &&
      !!pedido.vendedor_id &&
      currentUser?.id === pedido.vendedor_id);

  // Ações do fluxo de entrega (EST-01 / EST-02), usadas na variante operacional.
  const finalizarEntrega = useFinalizarEntrega();
  const atribuirEntregador = useAtribuirEntregadorPedido();
  const canFinalizar = canFinalizarEntrega(currentUser, pedido);
  const canRetirarDaRota =
    isEntregador(userRole) &&
    !!pedido.entregador_id &&
    currentUser?.id === pedido.entregador_id &&
    (pedido.status || '').toLowerCase() !== 'concluido';

  const handleFinalizarEntrega = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await finalizarEntrega.mutateAsync(pedido.id);
      success('Entrega confirmada');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao confirmar entrega');
    }
  };

  const handleRetirarDaRota = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await atribuirEntregador.mutateAsync({ pedidoId: pedido.id, entregadorId: null });
      success('Pedido retirado da rota');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao retirar da rota');
    }
  };

  const paymentStatus = getPaymentStatusLabel(pedido.status_pagamento);
  const paymentStatusColor = getPaymentStatusColor(pedido.status_pagamento);
  const sourceLabel = formatOrderSourceLabel({
    sourceName: pedido.fonte_pedido_nome,
    legacySource: pedido.fonte_pedido,
    vendedorId: pedido.vendedor_id,
    vendedorName: pedido.vendedor_id ? sellerNameById?.[pedido.vendedor_id] : undefined,
  });

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

  const handleMenuOpen = (e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation();
    setMenuAnchor(e.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleCopyMensagem = async () => {
    handleMenuClose();
    if (pedido.mensagem) {
      const copied = await copyToClipboard(pedido.mensagem);
      if (copied) {
        success('Mensagem copiada!');
      } else {
        showError('Erro ao copiar mensagem');
      }
    }
  };

  const handleCopyEncaminhar = async () => {
    handleMenuClose();
    const texto = buildEncaminharMensagem(pedido);
    const copied = await copyToClipboard(texto);
    if (copied) {
      success('Encaminhamento copiado!');
    } else {
      showError('Erro ao copiar encaminhamento');
    }
  };

  const handleView = () => {
    handleMenuClose();
    navigate(`/pedidos/${pedido.id}`);
  };

  const handleEdit = () => {
    handleMenuClose();
    navigate(`/pedidos/${pedido.id}/editar`);
  };

  const handlePrint = async () => {
    handleMenuClose();
    try {
      await printService.print(pedido.id);
      success('Impressão iniciada');
    } catch (err) {
      showError(err?.message || 'Erro ao imprimir');
    }
  };

  const handleToggleCartaoImpresso = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await toggleCartaoImpresso.mutateAsync({ id: pedido.id });
      success(pedido.cartao_impresso ? 'Cartão desmarcado' : 'Cartão marcado como impresso');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao atualizar cartão';
      showError(errorMessage);
    }
  };

  const handleMarcarComoPago = async () => {
    handleMenuClose();
    try {
      await updatePedido.mutateAsync({
        id: pedido.id,
        status_pagamento: 'Pago',
      });
      success('Pagamento marcado como pago');
    } catch (err) {
      showError(err?.message || 'Erro ao atualizar pagamento');
    }
  };

  const handleDelete = async () => {
    handleMenuClose();
    const confirmed = await confirm({
      title: 'Deletar pedido',
      description: 'Esta ação é permanente. Confirme para prosseguir.',
      confirmColor: 'error',
      confirmText: 'Deletar',
    });
    if (!confirmed) return;

    try {
      await deletePedido.mutateAsync(pedido.id);
      success('Pedido deletado');
    } catch (err) {
      showError(err?.message || 'Erro ao deletar pedido');
    }
  };

  const handleCobrar = (e: React.MouseEvent) => {
    e.stopPropagation();
    const telefone = pedido.telefone_cliente.replace(/\D/g, '');
    // Formatar telefone: se tem 11 dígitos (celular BR), adiciona 55; se tem 10 (fixo), adiciona 55
    let telefoneFormatado = telefone;
    if (telefone.length === 11 || telefone.length === 10) {
      telefoneFormatado = `55${telefone}`;
    } else if (telefone.length > 11) {
      // Já tem código do país
      telefoneFormatado = telefone;
    }
    
    const nome = pedido.destinatario || pedido.cliente;
    const dataEntrega = dayjs(pedido.dia_entrega).format('DD/MM');
    const horarioEntrega = pedido.horario;
    const total = pedido.valor ? formatBRL(pedido.valor) : 'R$ 0,00';
    
    const mensagem = `Olá, ${nome}. Seu pedido #${pedido.id} (entrega ${dataEntrega} ${horarioEntrega}) está com pagamento ${paymentStatus}. Total: ${total}.`;
    
    // Adicionar link/chave Pix se existir (aqui você pode adicionar lógica para buscar isso)
    // Por enquanto, deixamos sem
    
    const url = `https://wa.me/${telefoneFormatado}?text=${encodeURIComponent(mensagem)}`;
    window.open(url, '_blank');
  };

  const handleEnviarAcompanhamento = async () => {
    handleMenuClose();
    const telefone = (pedido.telefone_cliente || '').replace(/\D/g, '');
    const telefoneFormatado =
      telefone.length === 10 || telefone.length === 11 ? `55${telefone}` : telefone;
    if (!telefoneFormatado) {
      showError('Pedido sem telefone do cliente');
      return;
    }
    try {
      const trackUrl = await trackLink.mutateAsync(pedido.id);
      // A mensagem vai pro telefone do CLIENTE (quem comprou), então o nome é o
      // do cliente — não o do destinatário da entrega.
      const nome = pedido.cliente || '';
      const mensagem =
        `Olá${nome ? `, ${nome}` : ''}! Aqui está o link para acompanhar o seu pedido na Plante uma Flor: ${trackUrl}`;
      window.open(
        `https://wa.me/${telefoneFormatado}?text=${encodeURIComponent(mensagem)}`,
        '_blank'
      );
    } catch (err) {
      showError(err?.message || 'Erro ao gerar link de acompanhamento');
    }
  };

  // Copia a mensagem de acompanhamento (com o link) para a área de transferência,
  // sem forçar a abertura do WhatsApp. Não exige telefone do cliente.
  const handleCopiarAcompanhamento = async () => {
    handleMenuClose();
    try {
      const trackUrl = await trackLink.mutateAsync(pedido.id);
      const nome = pedido.cliente || '';
      const mensagem =
        `Olá${nome ? `, ${nome}` : ''}! Aqui está o link para acompanhar o seu pedido na Plante uma Flor: ${trackUrl}`;
      const copied = await copyToClipboard(mensagem);
      if (copied) {
        success('Mensagem de acompanhamento copiada!');
      } else {
        showError('Erro ao copiar acompanhamento');
      }
    } catch (err) {
      showError(err?.message || 'Erro ao gerar link de acompanhamento');
    }
  };

  const handleCalcularTaxaCTA = (e: React.MouseEvent) => {
    e.stopPropagation();
    handleCalcularTaxa(e);
  };

  const handleIniciarProducao = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await updatePedido.mutateAsync({
        id: pedido.id,
        status: pedido.status === 'agendado' ? 'em_producao' : 'em_rota',
      });
      success(pedido.status === 'agendado' ? 'Produção iniciada' : 'Pedido saiu para entrega');
    } catch (err) {
      showError(err?.message || 'Erro ao atualizar status');
    }
  };

  // Chips de pendência (máx 3)
  const pendenciaChips: Array<{ label: string; color: 'error' | 'warning' | 'info' }> = [];
  
  if (isAtrasado) {
    pendenciaChips.push({ label: 'Atrasado', color: 'error' });
  }
  
  if (pendenciaChips.length < 3 && paymentStatus === 'Pendente') {
    pendenciaChips.push({ label: 'Pagamento pendente', color: 'warning' });
  }
  
  if (pendenciaChips.length < 3 && pedido.tipo_pedido === 'Entrega' && !pedido.taxa_entrega) {
    pendenciaChips.push({ label: 'Sem taxa', color: 'info' });
  }
  
  if (pendenciaChips.length < 3 && pedido.tipo_pedido === 'Entrega' && !pedido.distancia_km) {
    pendenciaChips.push({ label: 'Sem distância', color: 'info' });
  }
  
  if (pendenciaChips.length < 3 && pedido.tipo_pedido === 'Entrega' && (!pedido.rua || !pedido.cidade)) {
    pendenciaChips.push({ label: 'Endereço incompleto', color: 'warning' });
  }

  // CTA contextual
  const getContextualCTA = () => {
    if (paymentStatus === 'Pendente') {
      return {
        label: 'Cobrar',
        icon: <WhatsApp />,
        onClick: handleCobrar,
        color: 'success' as const,
      };
    }
    
    if (pedido.tipo_pedido === 'Entrega' && (!pedido.taxa_entrega || !pedido.distancia_km)) {
      return {
        label: 'Calcular taxa',
        icon: <Calculate />,
        onClick: handleCalcularTaxaCTA,
        color: 'primary' as const,
      };
    }
    
    if (paymentStatus === 'Pago' && (pedido.status === 'agendado' || pedido.status === 'pronto_entrega')) {
      return {
        label: pedido.status === 'agendado' ? 'Iniciar produção' : 'Saiu p/ entrega',
        icon: pedido.status === 'agendado' ? <PlayArrow /> : <LocalShippingIcon />,
        onClick: handleIniciarProducao,
        color: 'primary' as const,
      };
    }
    
    return null;
  };

  const contextualCTA = getContextualCTA();

  // Variante compacta (tile ~quadrado p/ grid 2-col no mobile + Kanban): denso, fonte
  // pequena, mensagem truncada. Toca para abrir os detalhes (sem menu/ações). #6 #10
  if (compact) {
    const mensagemPreview = (pedido.mensagem || '').trim();
    return (
      <Card
        variant="outlined"
        onClick={() => navigate(`/pedidos/${pedido.id}`)}
        sx={{
          cursor: 'pointer',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          borderColor: isAtrasado ? 'error.light' : undefined,
          '&:hover': { boxShadow: 3 },
        }}
      >
        <CardContent
          sx={{
            p: 1,
            '&:last-child': { pb: 1 },
            display: 'flex',
            flexDirection: 'column',
            gap: 0.4,
            flex: 1,
            minWidth: 0,
          }}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={0.5}>
            <Chip
              label={statusLabel}
              color={statusColor}
              size="small"
              sx={{ height: 17, '& .MuiChip-label': { px: 0.5, fontSize: '0.58rem' } }}
            />
            <Typography sx={{ fontSize: '0.58rem', color: 'text.secondary' }}>#{pedido.id}</Typography>
          </Stack>

          <Typography sx={{ fontSize: '0.72rem', fontWeight: 700, lineHeight: 1.2 }} noWrap>
            {pedido.destinatario || pedido.cliente || 'Sem nome'}
          </Typography>

          {pedido.produto && (
            <Typography
              sx={{
                fontSize: '1.05rem',
                fontWeight: 800,
                color: 'text.primary',
                lineHeight: 1.2,
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {pedido.produto}
            </Typography>
          )}

          {mensagemPreview && (
            <Typography
              sx={{
                fontSize: '0.62rem',
                fontStyle: 'italic',
                color: 'text.secondary',
                lineHeight: 1.25,
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              “{mensagemPreview}”
            </Typography>
          )}

          <Box sx={{ flex: 1 }} />

          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={0.5}>
            <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }} noWrap>
              {pedido.dia_entrega ? dayjs(pedido.dia_entrega).format('DD/MM') : '—'}
              {pedido.horario ? ` ${pedido.horario}` : ''}
            </Typography>
            {pedido.valor && (
              <Typography sx={{ fontSize: '0.66rem', fontWeight: 700 }} noWrap>
                R$ {pedido.valor}
              </Typography>
            )}
          </Stack>

          {isAtrasado && (
            <Chip
              label="Atrasado"
              color="error"
              size="small"
              sx={{
                height: 15,
                alignSelf: 'flex-start',
                '& .MuiChip-label': { px: 0.5, fontSize: '0.54rem' },
              }}
            />
          )}
        </CardContent>
      </Card>
    );
  }

  // Variante operacional do entregador (VIS-02): hierarquia voltada à entrega —
  // localidade (bairro/cidade) + horário em destaque, produto legível, ambos os
  // nomes, e só as ações do fluxo (confirmar entrega / retirar da rota).
  if (operacional) {
    const horarioLabel = pedido.slot_inicio || pedido.horario || '—';
    const localidade = [pedido.bairro, pedido.cidade].filter(Boolean).join(', ');
    return (
      <Card
        variant="outlined"
        onClick={() => navigate(`/pedidos/${pedido.id}`)}
        sx={{
          cursor: 'pointer',
          borderColor: isAtrasado ? 'error.light' : undefined,
          '&:hover': { boxShadow: 3 },
        }}
      >
        <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
          {/* Topo: localidade (bairro/cidade) + horário em destaque (VIS-01) */}
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
            <Typography sx={{ fontWeight: 700, fontSize: '1rem', lineHeight: 1.25, minWidth: 0 }}>
              {localidade || 'Local não informado'}
            </Typography>
            <Chip
              label={horarioLabel}
              color={pedido.is_expressa ? 'error' : 'primary'}
              size="small"
              sx={{ fontWeight: 700 }}
            />
          </Stack>

          {/* Endereço completo (peso normal) */}
          <Box display="flex" alignItems="flex-start" gap={0.5} mt={0.5}>
            <Place fontSize="small" color="action" sx={{ mt: '2px' }} />
            <Typography variant="body2" color="text.secondary">
              {enderecoCompleto}
            </Typography>
          </Box>

          {/* Local de entrega em destaque (tipo + nome + detalhe do prédio) */}
          {(() => {
            const tipo = pedido.tipo_local || 'casa';
            const detalhe = getDetalheLocal(pedido);
            const TipoIcon = tipo === 'predio' ? Apartment : tipo === 'comercial' ? Store : Home;
            const mostraNome = tipo !== 'casa' && !!pedido.nome_local;
            if (!mostraNome && !detalhe) return null;
            return (
              <Box mt={0.75}>
                <Stack direction="row" alignItems="center" spacing={0.75} flexWrap="wrap">
                  <Chip
                    size="small"
                    color="primary"
                    icon={<TipoIcon sx={{ fontSize: 14 }} />}
                    label={getTipoLocalLabel(tipo)}
                    sx={{ fontWeight: 700, height: 20, '& .MuiChip-label': { px: 0.75 } }}
                  />
                  {mostraNome && (
                    <Typography variant="body2" sx={{ fontWeight: 700, color: 'primary.main' }}>
                      {pedido.nome_local}
                    </Typography>
                  )}
                </Stack>
                {detalhe && (
                  <Box
                    sx={{
                      display: 'inline-block',
                      mt: 0.5,
                      px: 1,
                      py: 0.25,
                      borderRadius: 1,
                      bgcolor: 'action.selected',
                      fontWeight: 700,
                      fontSize: '0.8rem',
                    }}
                  >
                    {detalhe}
                  </Box>
                )}
              </Box>
            );
          })()}

          {/* Produto (destaque para montagem/conferência) */}
          <Typography sx={{ fontWeight: 800, fontSize: '1.35rem', lineHeight: 1.2, mt: 1 }}>
            {pedido.produto}
          </Typography>

          {/* Nomes: destinatário em destaque, remetente em peso menor */}
          <Box mt={0.5}>
            <Typography variant="body2">
              <strong>Para:</strong> {pedido.destinatario || '—'}
            </Typography>
            {pedido.cliente && (
              <Typography variant="caption" color="text.secondary" display="block">
                De: {pedido.cliente}
              </Typography>
            )}
          </Box>

          {/* Status + ações do entregador (EST-01 / EST-02) */}
          <Stack direction="row" spacing={1} alignItems="center" mt={1.5} flexWrap="wrap">
            <Chip label={statusLabel} color={statusColor} size="small" />
            <Box flex={1} />
            {canRetirarDaRota && (
              <Button
                size="small"
                variant="outlined"
                color="inherit"
                startIcon={<Undo />}
                onClick={handleRetirarDaRota}
                disabled={atribuirEntregador.isPending}
              >
                Retirar da rota
              </Button>
            )}
            {canFinalizar && (
              <Button
                size="small"
                variant="contained"
                color="success"
                startIcon={<CheckCircle />}
                onClick={handleFinalizarEntrega}
                disabled={finalizarEntrega.isPending}
              >
                Confirmar entrega
              </Button>
            )}
          </Stack>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? { boxShadow: 4 } : {},
        transition: 'box-shadow 0.2s',
      }}
      onClick={onClick}
    >
      {/* No mobile, o card normal fica só um pouco menor (menos padding + título h6). */}
      <CardContent sx={isMobile ? { p: 1.5, '&:last-child': { pb: 1.5 } } : undefined}>
        {/* 1. Cabeçalho (Identidade + Estados) */}
        <Box mb={isMobile ? 1.5 : 2}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1} mb={1}>
            <Box flex={1}>
              <Typography variant={isMobile ? 'h6' : 'h5'} component="div" fontWeight="bold" gutterBottom>
                Pedido #{pedido.id}
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                {pedido.impresso && (
                  <Chip 
                    label="Impresso" 
                    color="success" 
                    size="small"
                  />
                )}
                {isAtrasado && (
                  <Chip 
                    label="Atrasado" 
                    color="error" 
                    size="small"
                  />
                )}
                <Chip
                  label={statusLabel}
                  color={statusColor}
                  size="small"
                />
              </Stack>
            </Box>
            <Box display="flex" alignItems="center" gap={1}>
              {selectable && (() => {
                const isRouteMode = selectionMode === 'route';
                const blockedForRoute = isRouteMode && pedido.tipo_pedido !== 'Entrega';
                const tooltip =
                  selectionMode === 'pickup'
                    ? 'Selecionar para pegar entrega'
                    : isRouteMode
                      ? pedido.tipo_pedido === 'Entrega'
                        ? 'Selecionar para rota'
                        : 'Apenas entregas podem ser roteirizadas'
                      : 'Selecionar para imprimir em lote';
                return (
                  <Tooltip title={tooltip}>
                    <span>
                      <Checkbox
                        size="small"
                        checked={selected}
                        disabled={blockedForRoute}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!blockedForRoute) {
                            onToggleSelect?.(pedido);
                          }
                        }}
                      />
                    </span>
                  </Tooltip>
                );
              })()}
              <IconButton
                size="small"
                onClick={handleMenuOpen}
                sx={{ ml: 'auto' }}
              >
                <MoreVert />
              </IconButton>
              <Menu
                anchorEl={menuAnchor}
                open={Boolean(menuAnchor)}
                onClose={handleMenuClose}
                onClick={(e) => e.stopPropagation()}
              >
                <MenuItem onClick={handleCopyMensagem} disabled={!pedido.mensagem}>
                  Copiar mensagem
                </MenuItem>
                <MenuItem onClick={handleCopyEncaminhar}>
                  Encaminhar (copiar)
                </MenuItem>
                <MenuItem
                  onClick={handleEnviarAcompanhamento}
                  disabled={!pedido.telefone_cliente || trackLink.isPending}
                >
                  <WhatsApp fontSize="small" sx={{ mr: 1 }} />
                  Enviar acompanhamento
                </MenuItem>
                <MenuItem onClick={handleCopiarAcompanhamento} disabled={trackLink.isPending}>
                  <ContentCopy fontSize="small" sx={{ mr: 1 }} />
                  Copiar acompanhamento
                </MenuItem>
                <MenuItem onClick={handleView}>Ver</MenuItem>
                {canEdit && <MenuItem onClick={handleEdit}>Editar</MenuItem>}
                <MenuItem onClick={handlePrint}>Imprimir</MenuItem>
                {paymentStatus === 'Pendente' && (
                  <MenuItem onClick={handleMarcarComoPago}>
                    Marcar como pago
                  </MenuItem>
                )}
                {canDelete && (
                  <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
                    Deletar
                  </MenuItem>
                )}
              </Menu>
            </Box>
          </Stack>
          
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1} flexWrap="wrap">
            {pedido.slot_inicio ? (
              <Stack direction="row" alignItems="baseline" spacing={1}>
                <Typography
                  variant="body1"
                  component="span"
                  fontWeight="bold"
                  color={pedido.is_expressa ? 'error.main' : 'text.primary'}
                >
                  {formatDateBR(pedido.dia_entrega)} às {pedido.slot_inicio}
                </Typography>
                {pedido.slot_deadline && (
                  <Typography variant="caption" color="text.secondary">
                    até {pedido.slot_deadline}
                  </Typography>
                )}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                {formatDateBR(pedido.dia_entrega)} às {pedido.horario}
              </Typography>
            )}
            {(pedido.fonte_pedido_nome || pedido.fonte_pedido) && (
              <Chip
                label={sourceLabel}
                size="small"
                variant="outlined"
              />
            )}
          </Stack>
        </Box>

        {/* Badge de Pagamento (OBRIGATÓRIO) */}
        <Box mb={2}>
          <Chip
            label={paymentStatus}
            color={paymentStatusColor}
            size="medium"
            sx={{ 
              fontSize: '0.875rem',
              fontWeight: 'bold',
              height: '32px',
            }}
          />
        </Box>

        {/* Chips de Pendência (máx 3) */}
        {pendenciaChips.length > 0 && (
          <Stack direction="row" spacing={1} mb={2} flexWrap="wrap">
            {pendenciaChips.map((chip, index) => (
              <Chip
                key={index}
                label={chip.label}
                color={chip.color}
                size="small"
              />
            ))}
          </Stack>
        )}

        <Divider sx={{ my: 2 }} />

        {/* 2. Identificação das Pessoas */}
        <Stack spacing={1} mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <Person fontSize="small" color="action" />
            <Typography variant="body2">
              <strong>De:</strong> {pedido.cliente}
            </Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <PersonAdd fontSize="small" color="action" />
            <Typography variant="body2">
              <strong>Para:</strong> {pedido.destinatario}
            </Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Phone fontSize="small" color="action" />
            <Typography variant="body2">
              <strong>Telefone:</strong> {formatPhone(pedido.telefone_cliente)}
            </Typography>
          </Box>
        </Stack>

        <Divider sx={{ my: 2 }} />

        {/* 3. Item/Resumo do Pedido */}
        <Box mb={2}>
          <Typography sx={{ fontSize: isMobile ? '1.25rem' : '1.4rem', fontWeight: 800, lineHeight: 1.2 }}>
            {pedido.produto}
          </Typography>
        </Box>

        {/* Mensagem/Cartinha Clicável */}
        <Box mb={2}>
          {pedido.mensagem ? (
            <>
              <CopyOnClick textToCopy={pedido.mensagem}>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    p: 1,
                    borderRadius: 1,
                  }}
                >
                  {pedido.mensagem}
                </Typography>
              </CopyOnClick>
              <Box mt={1} display="flex" alignItems="center" justifyContent="flex-end">
                <Tooltip
                  title={
                    pedido.cartao_impresso
                      ? 'Cartão já impresso — clique para desmarcar'
                      : 'Marcar cartão como impresso'
                  }
                >
                  <Button
                    size="small"
                    variant={pedido.cartao_impresso ? 'contained' : 'outlined'}
                    color={pedido.cartao_impresso ? 'success' : 'primary'}
                    startIcon={
                      pedido.cartao_impresso ? <CheckCircle /> : <RadioButtonUnchecked />
                    }
                    onClick={handleToggleCartaoImpresso}
                    disabled={toggleCartaoImpresso.isPending}
                    sx={{ textTransform: 'none' }}
                  >
                    {pedido.cartao_impresso ? 'Cartão impresso' : 'Marcar cartão impresso'}
                  </Button>
                </Tooltip>
              </Box>
            </>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Sem mensagem
            </Typography>
          )}
        </Box>

        {/* 4. Tipo de Logística */}
        <Box mb={2} display="flex" alignItems="center" gap={1}>
          {pedido.tipo_pedido === 'Entrega' ? (
            <>
              <LocalShipping fontSize="small" color="primary" />
              <Typography variant="body2" color="primary">
                <strong>Entrega</strong>
              </Typography>
            </>
          ) : (
            <>
              <Store fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                <strong>Retirada</strong>
              </Typography>
            </>
          )}
        </Box>

        {/* 5. Caixa "Entrega" (Detalhes Operacionais) */}
        {pedido.tipo_pedido === 'Entrega' && (
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 2, 
              mb: 2, 
              bgcolor: 'background.default',
            }}
          >
            <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
              Entrega
            </Typography>
            {/* VIS-01: bairro/cidade em negrito para leitura de relance */}
            {(pedido.bairro || pedido.cidade) && (
              <Typography variant="body2" fontWeight="bold" mb={0.5}>
                {[pedido.bairro, pedido.cidade].filter(Boolean).join(', ')}
              </Typography>
            )}
            <Typography variant="body2" color="text.secondary" mb={1}>
              {enderecoCompleto}
            </Typography>
            {/* Local em destaque: tipo + nome + detalhe do prédio */}
            {(() => {
              const tipo = pedido.tipo_local || 'casa';
              const detalhe = getDetalheLocal(pedido);
              const TipoIcon = tipo === 'predio' ? Apartment : tipo === 'comercial' ? Store : Home;
              const mostraNome = tipo !== 'casa' && !!pedido.nome_local;
              if (!mostraNome && !detalhe) return null;
              return (
                <Stack direction="row" alignItems="center" spacing={0.75} flexWrap="wrap" mb={2}>
                  <Chip
                    size="small"
                    color="primary"
                    icon={<TipoIcon sx={{ fontSize: 14 }} />}
                    label={getTipoLocalLabel(tipo)}
                    sx={{ fontWeight: 700, height: 20, '& .MuiChip-label': { px: 0.75 } }}
                  />
                  {mostraNome && (
                    <Typography variant="body2" sx={{ fontWeight: 700, color: 'primary.main' }}>
                      {pedido.nome_local}
                    </Typography>
                  )}
                  {detalhe && (
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      · {detalhe}
                    </Typography>
                  )}
                </Stack>
              );
            })()}
            <Stack spacing={1.5}>
              <Box display="flex" alignItems="center" justifyContent="space-between" gap={1}>
                <Typography variant="body2">
                  <strong>Distância:</strong> {pedido.distancia_km ? `${pedido.distancia_km.toFixed(1)} km` : 'Não calculada'}
                </Typography>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<Calculate />}
                  onClick={handleCalcularDistancia}
                  disabled={calcDistancia.isPending}
                  sx={{ minWidth: 'auto', whiteSpace: 'nowrap' }}
                >
                  {calcDistancia.isPending ? '...' : 'Recalcular'}
                </Button>
              </Box>
              <Box display="flex" alignItems="center" justifyContent="space-between" gap={1}>
                <Typography variant="body2">
                  <strong>Taxa de entrega:</strong> {pedido.taxa_entrega ? formatBRL(pedido.taxa_entrega) : 'Não calculada'}
                </Typography>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<Calculate />}
                  onClick={handleCalcularTaxa}
                  disabled={calcTaxa.isPending}
                  sx={{ minWidth: 'auto', whiteSpace: 'nowrap' }}
                >
                  {calcTaxa.isPending ? '...' : 'Recalcular'}
                </Button>
              </Box>
            </Stack>
          </Paper>
        )}

        {/* 6. Resumo Financeiro */}
        {pedido.valor && (
          <Box mb={2}>
            <Typography variant="h6" fontWeight="bold" color="primary">
              {formatBRL(pedido.valor)}
            </Typography>
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        {/* 7. Controle de Status */}
        <Box mb={2}>
          <StatusSelector pedidoId={pedido.id} status={pedido.status} />
        </Box>

        {/* CTA Contextual */}
        {contextualCTA && (
          <Box mb={2}>
            <Button
              variant="contained"
              color={contextualCTA.color}
              startIcon={contextualCTA.icon}
              onClick={contextualCTA.onClick}
              fullWidth
            >
              {contextualCTA.label}
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
