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
  PlayArrow,
  LocalShipping as LocalShippingIcon,
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
} from './OrderCardHelpers';
import { useCalcularDistanciaPedido, useCalcularTaxaEntrega, useUpdatePedido } from '../../../api/endpoints/pedidos';
import { useToast } from '../../../components/system/useToast';
import { CopyOnClick } from '../../../components/common/CopyOnClick';
import { copyToClipboard } from '../../../lib/utils/clipboard';
import { useAuth } from '../../auth/authStore';
import { usePedidoPrintService } from '../services/PedidoPrintService';
import { useConfirm } from '../../../components/system/useConfirm';
import { useDeletePedido } from '../../../api/endpoints/pedidos';
import dayjs from 'dayjs';
import { formatOrderSourceLabel } from '../utils/sourceLabel';

export type SelectionMode = 'route' | 'print';

interface OrderCardProps {
  pedido: Pedido;
  sellerNameById?: Record<number, string>;
  onClick?: () => void;
  selectable?: boolean;
  selected?: boolean;
  onToggleSelect?: (pedido: Pedido) => void;
  selectionMode?: SelectionMode;
}

export function OrderCard({
  pedido,
  sellerNameById,
  onClick,
  selectable = false,
  selected = false,
  onToggleSelect,
  selectionMode = 'route',
}: OrderCardProps) {
  const navigate = useNavigate();
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const statusColor = getStatusColor(pedido.status);
  const statusLabel = getStatusLabel(pedido.status);
  const isAtrasado = isPedidoAtrasado(pedido);
  const enderecoCompleto = getEnderecoCompleto(pedido);
  const calcDistancia = useCalcularDistanciaPedido();
  const calcTaxa = useCalcularTaxaEntrega();
  const updatePedido = useUpdatePedido();
  const deletePedido = useDeletePedido();
  const { success, error: showError } = useToast();
  const { getUserRole, getCredentials, isJwtUser } = useAuth();
  const printService = usePedidoPrintService();
  const confirm = useConfirm();

  const userRole = getUserRole();
  const canEdit = userRole === 'admin' || userRole === 'atendente' || userRole === 'vendedor';
  const canDelete = userRole === 'admin';

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

  return (
    <Card
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? { boxShadow: 4 } : {},
        transition: 'box-shadow 0.2s',
      }}
      onClick={onClick}
    >
      <CardContent>
        {/* 1. Cabeçalho (Identidade + Estados) */}
        <Box mb={2}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1} mb={1}>
            <Box flex={1}>
              <Typography variant="h5" component="div" fontWeight="bold" gutterBottom>
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
                const tooltip = isRouteMode
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
            <Typography variant="body2" color="text.secondary">
              {formatDateBR(pedido.dia_entrega)} às {pedido.horario}
            </Typography>
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
          <Typography variant="body1" fontWeight="medium">
            {pedido.produto}
          </Typography>
        </Box>

        {/* Mensagem/Cartinha Clicável */}
        <Box mb={2}>
          {pedido.mensagem ? (
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
            <Typography variant="body2" color="text.secondary" mb={2}>
              {enderecoCompleto}
            </Typography>
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
