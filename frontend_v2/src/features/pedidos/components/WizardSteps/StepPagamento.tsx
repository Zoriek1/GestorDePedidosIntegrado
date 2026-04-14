/**
 * Step 4 - Pagamento e Fechamento
 * Dados financeiros e resumo do pedido
 * Resumo lateral/sticky em desktop
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
  Grid,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import PaymentIcon from '@mui/icons-material/Payment';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import dayjs from 'dayjs';
import { parseCurrencyToFloat, formatCurrency, FORMAS_PAGAMENTO, STATUS_PAGAMENTO } from '../../schemas';
import type { PedidoFormData } from '../../schemas';

// ============================================================================
// Componente
// ============================================================================

export function StepPagamento() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

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
  const horario = useWatch({ control, name: 'horario' });
  const tipoPedido = useWatch({ control, name: 'tipo_pedido' });
  const cidade = useWatch({ control, name: 'cidade' });
  const statusPagamento = useWatch({ control, name: 'status_pagamento' });

  // Calcula o valor líquido (valor do pedido menos frete)
  const valorFloat = parseCurrencyToFloat(valorProduto) || 0;
  const taxaFloat = parseCurrencyToFloat(taxaEntrega) || 0;
  const valorLiquido = valorFloat - taxaFloat;

  // Componente de Resumo
  const ResumoContent = (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        bgcolor: 'grey.50',
        borderColor: 'primary.main',
        borderWidth: 2,
        position: isMobile ? 'static' : 'sticky',
        top: isMobile ? 'auto' : 100,
      }}
    >
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <ReceiptLongIcon color="primary" />
        <Typography variant="subtitle1" fontWeight="bold">
          Resumo do Pedido
        </Typography>
      </Stack>
      
      <Stack spacing={1}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" color="text.secondary">
            Cliente:
          </Typography>
          <Typography variant="body2" fontWeight="medium">
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
            Tipo:
          </Typography>
          <Typography variant="body2">
            {tipoPedido}
          </Typography>
        </Box>

        {cidade && (
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              Cidade:
            </Typography>
            <Typography variant="body2">
              {cidade}
            </Typography>
          </Box>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" color="text.secondary">
            Produto:
          </Typography>
          <Typography variant="body2" sx={{ maxWidth: '60%', textAlign: 'right' }}>
            {produto ? (produto.length > 40 ? `${produto.slice(0, 40)}...` : produto) : '-'}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" color="text.secondary">
            Data/Hora:
          </Typography>
          <Typography variant="body2">
            {diaEntrega ? dayjs(diaEntrega).format('DD/MM/YYYY') : '-'} {horario ? `às ${horario}` : ''}
          </Typography>
        </Box>

        <Divider sx={{ my: 1 }} />

        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" color="text.secondary">
            Valor do Produto:
          </Typography>
          <Typography variant="body2">
            {valorFloat > 0 ? formatCurrency(valorFloat) : '-'}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" color="text.secondary">
            Taxa de Entrega:
          </Typography>
          <Typography variant="body2">
            {taxaFloat > 0 ? formatCurrency(taxaFloat) : 'Grátis'}
          </Typography>
        </Box>

        <Divider sx={{ my: 1 }} />

        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="subtitle1" fontWeight="bold" color="primary.main">
            Valor Líquido:
          </Typography>
          <Typography variant="subtitle1" fontWeight="bold" color="primary.main">
            {formatCurrency(valorLiquido)}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Pagamento:
          </Typography>
          <Typography 
            variant="body2" 
            fontWeight="bold"
            color={statusPagamento === 'Pago' ? 'success.main' : 'warning.main'}
          >
            {statusPagamento || 'Pendente'}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );

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

      <Grid container spacing={3}>
        {/* Formulário de Pagamento */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Stack spacing={3}>
            {/* Mensagem do Cartão */}
            <Controller
              name="mensagem"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Carta / Mensagem"
                  placeholder="Mensagem para o cartão"
                  multiline
                  rows={4}
                  fullWidth
                  error={!!errors.mensagem}
                  helperText={
                    errors.mensagem?.message ||
                    `${field.value?.length || 0}/1000 caracteres`
                  }
                  inputProps={{ maxLength: 1000 }}
                />
              )}
            />

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
          </Stack>
        </Grid>

        {/* Resumo do Pedido (Lateral em Desktop) */}
        <Grid size={{ xs: 12, md: 5 }}>
          {ResumoContent}
        </Grid>
      </Grid>
    </Box>
  );
}

export default StepPagamento;

