/**
 * Customers Advanced Filters Component
 * Filtros avançados: quantidade de pedidos, LTV, data último pedido
 */

import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Stack,
  Collapse,
  IconButton,
} from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs, { Dayjs } from 'dayjs';

export interface CustomersAdvancedFiltersProps {
  minPedidos?: number;
  maxPedidos?: number;
  minLTV?: number;
  maxLTV?: number;
  ultimoPedidoApos?: string;
  ultimoPedidoAntes?: string;
  onChange: (filters: {
    minPedidos?: number;
    maxPedidos?: number;
    minLTV?: number;
    maxLTV?: number;
    ultimoPedidoApos?: string;
    ultimoPedidoAntes?: string;
  }) => void;
}

export function CustomersAdvancedFilters({
  minPedidos,
  maxPedidos,
  minLTV,
  maxLTV,
  ultimoPedidoApos,
  ultimoPedidoAntes,
  onChange,
}: CustomersAdvancedFiltersProps) {
  const [expanded, setExpanded] = useState(false);
  const [localMinPedidos, setLocalMinPedidos] = useState<string>(minPedidos?.toString() || '');
  const [localMaxPedidos, setLocalMaxPedidos] = useState<string>(maxPedidos?.toString() || '');
  const [localMinLTV, setLocalMinLTV] = useState<string>(minLTV?.toString() || '');
  const [localMaxLTV, setLocalMaxLTV] = useState<string>(maxLTV?.toString() || '');
  const [localUltimoApos, setLocalUltimoApos] = useState<Dayjs | null>(
    ultimoPedidoApos ? dayjs(ultimoPedidoApos) : null
  );
  const [localUltimoAntes, setLocalUltimoAntes] = useState<Dayjs | null>(
    ultimoPedidoAntes ? dayjs(ultimoPedidoAntes) : null
  );

  const handleApply = () => {
    onChange({
      minPedidos: localMinPedidos ? parseInt(localMinPedidos, 10) : undefined,
      maxPedidos: localMaxPedidos ? parseInt(localMaxPedidos, 10) : undefined,
      minLTV: localMinLTV ? parseFloat(localMinLTV) : undefined,
      maxLTV: localMaxLTV ? parseFloat(localMaxLTV) : undefined,
      ultimoPedidoApos: localUltimoApos ? localUltimoApos.format('YYYY-MM-DD') : undefined,
      ultimoPedidoAntes: localUltimoAntes ? localUltimoAntes.format('YYYY-MM-DD') : undefined,
    });
  };

  const handleClear = () => {
    setLocalMinPedidos('');
    setLocalMaxPedidos('');
    setLocalMinLTV('');
    setLocalMaxLTV('');
    setLocalUltimoApos(null);
    setLocalUltimoAntes(null);
    onChange({});
  };

  const hasFilters = minPedidos || maxPedidos || minLTV || maxLTV || ultimoPedidoApos || ultimoPedidoAntes;

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: expanded ? 2 : 0 }}>
        <Typography variant="subtitle2" fontWeight="bold">
          Filtros Avançados
          {hasFilters && (
            <Typography component="span" variant="caption" color="primary" sx={{ ml: 1 }}>
              (ativos)
            </Typography>
          )}
        </Typography>
        <IconButton size="small" onClick={() => setExpanded(!expanded)}>
          {expanded ? <ExpandLess /> : <ExpandMore />}
        </IconButton>
      </Box>

      <Collapse in={expanded}>
        <Stack spacing={2}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Quantidade de Pedidos
            </Typography>
            <Stack direction="row" spacing={1}>
              <TextField
                size="small"
                label="Mínimo"
                type="number"
                value={localMinPedidos}
                onChange={(e) => setLocalMinPedidos(e.target.value)}
                fullWidth
              />
              <TextField
                size="small"
                label="Máximo"
                type="number"
                value={localMaxPedidos}
                onChange={(e) => setLocalMaxPedidos(e.target.value)}
                fullWidth
              />
            </Stack>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              LTV (Lifetime Value) - R$
            </Typography>
            <Stack direction="row" spacing={1}>
              <TextField
                size="small"
                label="Mínimo"
                type="number"
                value={localMinLTV}
                onChange={(e) => setLocalMinLTV(e.target.value)}
                fullWidth
                inputProps={{ step: 0.01 }}
              />
              <TextField
                size="small"
                label="Máximo"
                type="number"
                value={localMaxLTV}
                onChange={(e) => setLocalMaxLTV(e.target.value)}
                fullWidth
                inputProps={{ step: 0.01 }}
              />
            </Stack>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Data do Último Pedido
            </Typography>
            <Stack direction="row" spacing={1}>
              <DatePicker
                label="Após"
                value={localUltimoApos}
                onChange={(newValue) => setLocalUltimoApos(newValue)}
                slotProps={{ textField: { size: 'small', fullWidth: true } }}
              />
              <DatePicker
                label="Antes"
                value={localUltimoAntes}
                onChange={(newValue) => setLocalUltimoAntes(newValue)}
                slotProps={{ textField: { size: 'small', fullWidth: true } }}
              />
            </Stack>
          </Box>

          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button size="small" variant="outlined" onClick={handleClear}>
              Limpar
            </Button>
            <Button size="small" variant="contained" onClick={handleApply}>
              Aplicar Filtros
            </Button>
          </Stack>
        </Stack>
      </Collapse>
    </Paper>
  );
}
