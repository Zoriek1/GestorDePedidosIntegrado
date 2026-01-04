/**
 * Step 2 - Dados da Entrega (Inteligente)
 * CEP com auto-preenchimento via ViaCEP
 * Campos de endereço readOnly por padrão com opção de editar
 * Seleção de horário via modal
 */

import { useState, useCallback } from 'react';
import { useFormContext, Controller, useWatch } from 'react-hook-form';
import {
  Box,
  TextField,
  Typography,
  Stack,
  Grid,
  IconButton,
  Tooltip,
  Alert,
  Button,
} from '@mui/material';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import EditIcon from '@mui/icons-material/Edit';
import LockIcon from '@mui/icons-material/Lock';
import { CepInput } from '../../../../components/form';
import { useCepLookup } from '../../useCases/cepLookup';
import type { PedidoFormData } from '../../schemas';

// ============================================================================
// Componente
// ============================================================================

export function StepEntrega() {
  const {
    control,
    setValue,
    watch,
    formState: { errors },
  } = useFormContext<PedidoFormData>();

  // Watch para estados condicionais
  const tipoPedido = useWatch({ control, name: 'tipo_pedido' });
  const isEntrega = tipoPedido === 'Entrega';

  // Estado para controlar edição de endereço
  const [isAddressLocked, setIsAddressLocked] = useState(true);

  // CEP Lookup
  const { lookupCep, isLoading: isCepLoading, error: cepError } = useCepLookup();

  // Handler para quando CEP é completado
  const handleCepComplete = useCallback(async (cep: string) => {
    const result = await lookupCep(cep);
    
    if (result) {
      // Preencher campos automaticamente
      setValue('rua', result.rua, { shouldValidate: true });
      setValue('bairro', result.bairro, { shouldValidate: true });
      setValue('cidade', result.cidade, { shouldValidate: true });
      // Bloquear edição após auto-preenchimento
      setIsAddressLocked(true);
    }
  }, [lookupCep, setValue]);

  // Toggle para editar endereço
  const handleToggleAddressLock = () => {
    setIsAddressLocked((prev) => !prev);
  };

  // Se for Retirada, não mostrar nada
  if (!isEntrega) {
    return (
      <Box>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 3 }}>
          <LocalShippingIcon color="primary" />
          <Typography variant="h6" component="h2">
            Logística de Entrega
          </Typography>
        </Stack>
        <Typography variant="body2" color="text.secondary">
          Este passo não é necessário para pedidos de retirada.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 3 }}>
        <LocalShippingIcon color="primary" />
        <Typography variant="h6" component="h2">
          Logística de Entrega
        </Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Informe onde o pedido será entregue. Digite o CEP para preencher o endereço automaticamente.
      </Typography>

      <Stack spacing={3}>
        {/* Campos de Endereço - Apenas para Entrega */}
        <Box>
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="subtitle2" color="text.secondary">
                Endereço de Entrega
              </Typography>
              <Tooltip title={isAddressLocked ? 'Clique para editar manualmente' : 'Endereço editável'}>
                <IconButton size="small" onClick={handleToggleAddressLock}>
                  {isAddressLocked ? <LockIcon fontSize="small" /> : <EditIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
            </Box>

            {/* CEP com busca automática */}
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Controller
                  name="cep"
                  control={control}
                  render={({ field }) => (
                    <CepInput
                      {...field}
                      label="CEP"
                      fullWidth
                      isLoading={isCepLoading}
                      onComplete={handleCepComplete}
                      error={!!errors.cep || !!cepError}
                      helperText={cepError || errors.cep?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 8 }}>
                <Controller
                  name="rua"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Rua/Logradouro"
                      placeholder="Preenchido automaticamente pelo CEP"
                      fullWidth
                      required={isEntrega}
                      disabled={isAddressLocked}
                      error={!!errors.rua}
                      helperText={errors.rua?.message}
                      slotProps={{
                        input: {
                          readOnly: isAddressLocked,
                        },
                      }}
                      sx={{
                        bgcolor: isAddressLocked ? 'grey.100' : 'inherit',
                      }}
                    />
                  )}
                />
              </Grid>
            </Grid>

            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Controller
                  name="numero"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Número"
                      placeholder="123"
                      fullWidth
                      required={isEntrega}
                      error={!!errors.numero}
                      helperText={errors.numero?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 4 }}>
                <Controller
                  name="complemento"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Complemento"
                      placeholder="Apto, Bloco..."
                      fullWidth
                      error={!!errors.complemento}
                      helperText={errors.complemento?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 5 }}>
                <Controller
                  name="bairro"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Bairro"
                      fullWidth
                      disabled={isAddressLocked}
                      error={!!errors.bairro}
                      helperText={errors.bairro?.message}
                      slotProps={{
                        input: {
                          readOnly: isAddressLocked,
                        },
                      }}
                      sx={{
                        bgcolor: isAddressLocked ? 'grey.100' : 'inherit',
                      }}
                    />
                  )}
                />
              </Grid>
            </Grid>

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="cidade"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Cidade"
                      fullWidth
                      required={isEntrega}
                      disabled={isAddressLocked}
                      error={!!errors.cidade}
                      helperText={errors.cidade?.message}
                      slotProps={{
                        input: {
                          readOnly: isAddressLocked,
                        },
                      }}
                      sx={{
                        bgcolor: isAddressLocked ? 'grey.100' : 'inherit',
                      }}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="obs_entrega"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Ponto de Referência"
                      placeholder="Ex: Casa amarela, portão preto"
                      fullWidth
                      error={!!errors.obs_entrega}
                      helperText={errors.obs_entrega?.message}
                    />
                  )}
                />
              </Grid>
            </Grid>

            {/* Endereço Completo */}
            <Controller
              name="endereco"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Endereço Completo"
                  placeholder="Será gerado automaticamente ou preencha manualmente"
                  multiline
                  rows={2}
                  fullWidth
                  error={!!errors.endereco}
                  helperText={errors.endereco?.message}
                />
              )}
            />

            {/* Botão Gerar Automático */}
            <Button
              variant="outlined"
              onClick={() => {
                const rua = watch('rua') || '';
                const numero = watch('numero') || '';
                const bairro = watch('bairro') || '';
                const cidade = watch('cidade') || '';
                const cep = watch('cep') || '';

                const partes = [];
                if (rua) {
                  if (numero && numero !== '0' && numero.toUpperCase() !== 'S/N' && numero.toUpperCase() !== 'SN') {
                    partes.push(`${rua}, ${numero}`);
                  } else {
                    partes.push(rua);
                  }
                }
                if (bairro) partes.push(bairro);
                if (cidade) partes.push(cidade);
                if (cep) partes.push(`CEP: ${cep}`);

                const enderecoCompleto = partes.join(', ');
                setValue('endereco', enderecoCompleto, { shouldValidate: true });
              }}
              sx={{ alignSelf: 'flex-start' }}
            >
              Gerar Endereço Automático
            </Button>

            {/* Dica sobre edição */}
            {isAddressLocked && (
              <Alert severity="info" sx={{ mt: 1 }}>
                Os campos Rua, Bairro e Cidade foram preenchidos pelo CEP. 
                Clique no <LockIcon fontSize="small" sx={{ verticalAlign: 'middle' }} /> para editar manualmente se necessário.
              </Alert>
            )}
          </Stack>
        </Box>
      </Stack>
    </Box>
  );
}

export default StepEntrega;

