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
} from '@mui/material';
import {
  Person,
  PersonAdd,
  Phone,
  LocalShipping,
  Store,
  Calculate,
} from '@mui/icons-material';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { formatDateBR } from '../../../lib/format/date';
import { formatBRL } from '../../../lib/format/currency';
import { getStatusColor, getStatusLabel } from '../useCases/orderMapping';
import { OrderCardActions } from './OrderCardActions';
import { StatusSelector } from './StatusSelector';
import { 
  isPedidoAtrasado, 
  formatPhone, 
  getEnderecoCompleto,
  formatCreatedAt,
} from './OrderCardHelpers';
import { useCalcularDistanciaPedido, useCalcularTaxaEntrega } from '../../../api/endpoints/pedidos';
import { useToast } from '../../../components/system/useToast';

interface OrderCardProps {
  pedido: Pedido;
  onClick?: () => void;
  selectable?: boolean;
  selected?: boolean;
  onToggleSelect?: (pedido: Pedido) => void;
}

export function OrderCard({ pedido, onClick, selectable = false, selected = false, onToggleSelect }: OrderCardProps) {
  const statusColor = getStatusColor(pedido.status);
  const statusLabel = getStatusLabel(pedido.status);
  const isAtrasado = isPedidoAtrasado(pedido);
  const enderecoCompleto = getEnderecoCompleto(pedido);
  const calcDistancia = useCalcularDistanciaPedido();
  const calcTaxa = useCalcularTaxaEntrega();
  const { success, error: showError } = useToast();

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
            <Box>
              {selectable && (
                <Tooltip title={pedido.tipo_pedido === 'Entrega' ? 'Selecionar para rota' : 'Apenas entregas podem ser roteirizadas'}>
                  <span>
                    <Checkbox
                      size="small"
                      checked={selected}
                      disabled={pedido.tipo_pedido !== 'Entrega'}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (pedido.tipo_pedido === 'Entrega') {
                          onToggleSelect?.(pedido);
                        }
                      }}
                    />
                  </span>
                </Tooltip>
              )}
            </Box>
          </Stack>
          
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1} flexWrap="wrap">
            <Typography variant="body2" color="text.secondary">
              {formatDateBR(pedido.dia_entrega)} às {pedido.horario}
            </Typography>
            {pedido.fonte_pedido_nome && (
              <Chip 
                label={pedido.fonte_pedido_nome} 
                size="small" 
                variant="outlined"
              />
            )}
          </Stack>
        </Box>

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

        {/* 8. Barra de Ações */}
        <OrderCardActions pedido={pedido} />
      </CardContent>
    </Card>
  );
}
