/**
 * Step 4 - Pagamento e Fechamento
 * Dados financeiros e resumo do pedido
 */

import { useFormContext, Controller, useWatch } from 'react-hook-form';
import {
  Box,
  TextField,
  Typography,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
  Divider,
  FormHelperText,
} from '@mui/material';
import PaymentIcon from '@mui/icons-material/Payment';
import { parseCurrencyToFloat, formatCurrency, FORMAS_PAGAMENTO, STATUS_PAGAMENTO } from '../../schemas';
import type { PedidoFormData } from '../../schemas';

export function Step4Pagamento() {
  const {
    control,
    formState: { errors },
  } = useFormContext<PedidoFormData>();

  // Watch para cálculo do total em tempo real
  const valorProduto = useWatch({ control, name: 'valor' });
  const taxaEntrega = useWatch({ control, name: 'taxa_entrega' });
  const cliente = useWatch({ control, name: 'cliente' });
  const destinatario = useWatch({ control, name: 'destinatario' });
  const produto = useWatch({ control, name: 'produto' });
  const diaEntrega = useWatch({ control, name: 'dia_entrega' });

  // valor já é o total cobrado (inclui entrega). taxa_entrega é apenas informativo.
  const valorFloat = parseCurrencyToFloat(valorProduto) || 0;
  const taxaFloat = parseCurrencyToFloat(taxaEntrega) || 0;

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 3 }}>
        <PaymentIcon color="primary" />
        <Typography variant="h6" component="h2">
          Pagamento e Finalização
        </Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Informe os dados de pagamento e revise o resumo do pedido.
      </Typography>

      <Stack spacing={3}>
        {/* Taxa de Entrega removida - é calculada automaticamente pelo backend quando o endereço é preenchido */}

        {/* Forma de Pagamento */}
        <Controller
          name="pagamento"
          control={control}
          render={({ field }) => (
            <FormControl fullWidth error={!!errors.pagamento}>
              <InputLabel>Forma de Pagamento</InputLabel>
              <Select {...field} label="Forma de Pagamento">
                <MenuItem value="">
                  <em>Não informado</em>
                </MenuItem>
                {FORMAS_PAGAMENTO.map((forma) => (
                  <MenuItem key={forma} value={forma}>
                    {forma}
                  </MenuItem>
                ))}
              </Select>
              {errors.pagamento && (
                <FormHelperText>{errors.pagamento.message}</FormHelperText>
              )}
            </FormControl>
          )}
        />

        {/* Status do Pagamento */}
        <Controller
          name="status_pagamento"
          control={control}
          render={({ field }) => (
            <FormControl fullWidth required error={!!errors.status_pagamento}>
              <InputLabel>Status do Pagamento</InputLabel>
              <Select {...field} label="Status do Pagamento" required>
                {STATUS_PAGAMENTO.map((status) => (
                  <MenuItem key={status} value={status}>
                    {status}
                  </MenuItem>
                ))}
              </Select>
              {errors.status_pagamento && (
                <FormHelperText>{errors.status_pagamento.message}</FormHelperText>
              )}
            </FormControl>
          )}
        />

        {/* Observações Gerais */}
        <Controller
          name="observacoes"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="Observações Gerais"
              placeholder="Observações adicionais sobre o pedido..."
              multiline
              rows={2}
              fullWidth
              error={!!errors.observacoes}
              helperText={errors.observacoes?.message}
            />
          )}
        />

        {/* Resumo do Pedido */}
        <Paper
          variant="outlined"
          sx={{
            p: 2,
            bgcolor: 'grey.50',
            borderColor: 'primary.main',
            borderWidth: 2,
          }}
        >
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Resumo do Pedido
          </Typography>
          
          <Stack spacing={1}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Cliente:
              </Typography>
              <Typography variant="body2">
                {cliente || '-'}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Destinatário:
              </Typography>
              <Typography variant="body2">
                {destinatario || '-'}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Produto:
              </Typography>
              <Typography variant="body2" sx={{ maxWidth: '60%', textAlign: 'right' }}>
                {produto ? (produto.length > 50 ? `${produto.slice(0, 50)}...` : produto) : '-'}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Data de Entrega:
              </Typography>
              <Typography variant="body2">
                {diaEntrega || '-'}
              </Typography>
            </Box>

            <Divider sx={{ my: 1 }} />

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="subtitle1" fontWeight="bold" color="primary.main">
                TOTAL:
              </Typography>
              <Typography variant="subtitle1" fontWeight="bold" color="primary.main">
                {valorFloat > 0 ? formatCurrency(valorFloat) : '-'}
              </Typography>
            </Box>

            {taxaFloat > 0 && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">
                  Taxa de Entrega (operacional):
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {formatCurrency(taxaFloat)}
                </Typography>
              </Box>
            )}
          </Stack>
        </Paper>
      </Stack>
    </Box>
  );
}

export default Step4Pagamento;

