/**
 * Step 2 - Dados da Entrega (Inteligente)
 * CEP com auto-preenchimento via ViaCEP
 * Campos de endereço readOnly por padrão com opção de editar
 * Seleção de horário via modal
 */

import { useState, useCallback, type MouseEvent } from 'react';
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
  MenuItem,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import EditIcon from '@mui/icons-material/Edit';
import LockIcon from '@mui/icons-material/Lock';
import { CepInput } from '../../../../components/form';
import { useCepLookup } from '../../useCases/cepLookup';
import { useClienteEnderecos } from '../../../../api/endpoints/customers';
import { UFS_BRASIL, type PedidoFormData } from '../../schemas';

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
  const tipoLocal = useWatch({ control, name: 'tipo_local' }) || 'casa';

  // Estado para controlar edição de endereço
  const [isAddressLocked, setIsAddressLocked] = useState(true);

  // Endereços salvos do cliente (#17): para clientes existentes, oferece um seletor que
  // preenche os campos automaticamente, em vez de digitar tudo de novo.
  const clienteId = useWatch({ control, name: 'cliente_id' });
  const { data: enderecosData } = useClienteEnderecos(isEntrega ? clienteId : null);
  const enderecosSalvos = enderecosData?.enderecos ?? [];
  const [selectedEnderecoId, setSelectedEnderecoId] = useState<number | ''>('');

  const handleSelectEndereco = (id: number) => {
    const e = enderecosSalvos.find((x) => x.id === id);
    if (!e) return;
    setSelectedEnderecoId(id);
    setValue('cep', e.cep, { shouldValidate: true });
    setValue('rua', e.rua, { shouldValidate: true });
    setValue('numero', e.numero, { shouldValidate: true });
    setValue('complemento', e.complemento, { shouldValidate: true });
    setValue('bairro', e.bairro, { shouldValidate: true });
    setValue('cidade', e.cidade, { shouldValidate: true });
    setValue('uf', e.estado, { shouldValidate: true });
  };

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
      setValue('uf', result.uf, { shouldValidate: true });
      // Bloquear edição após auto-preenchimento
      setIsAddressLocked(true);
    }
  }, [lookupCep, setValue]);

  // Toggle para editar endereço
  const handleToggleAddressLock = () => {
    setIsAddressLocked((prev) => !prev);
  };

  const handleTipoLocalChange = (_event: MouseEvent<HTMLElement>, value: PedidoFormData['tipo_local'] | null) => {
    if (!value) return;
    setValue('tipo_local', value, { shouldValidate: true });
    if (value === 'casa') {
      setValue('nome_local', '');
      setValue('apto', '');
      setValue('bloco', '');
      setValue('torre', '');
      setValue('andar', '');
    } else {
      setValue('quadra', '');
      setValue('lote', '');
    }
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

            {/* Endereços salvos do cliente (#17) */}
            {enderecosSalvos.length > 0 && (
              <TextField
                select
                size="small"
                fullWidth
                label="Endereços salvos do cliente"
                value={selectedEnderecoId}
                onChange={(e) => handleSelectEndereco(Number(e.target.value))}
                helperText="Selecione um endereço salvo para preencher automaticamente"
              >
                {enderecosSalvos.map((e) => (
                  <MenuItem key={e.id} value={e.id}>
                    {e.apelido ? `${e.apelido} — ` : ''}
                    {e.endereco_completo || `${e.rua}, ${e.numero} - ${e.bairro}`}
                  </MenuItem>
                ))}
              </TextField>
            )}

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
                      required={isEntrega}
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
                      placeholder="S/N se vazio"
                      fullWidth
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
                      required={isEntrega}
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
              <Grid size={{ xs: 12, sm: 5 }}>
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
              <Grid size={{ xs: 12, sm: 2 }}>
                <Controller
                  name="uf"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="UF"
                      fullWidth
                      disabled={isAddressLocked}
                      error={!!errors.uf}
                      helperText={errors.uf?.message}
                    >
                      {UFS_BRASIL.map((uf) => <MenuItem key={uf} value={uf}>{uf}</MenuItem>)}
                    </TextField>
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 5 }}>
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

            <Box>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                Tipo de local
              </Typography>
              <ToggleButtonGroup
                exclusive
                size="small"
                value={tipoLocal}
                onChange={handleTipoLocalChange}
                sx={{ flexWrap: 'wrap' }}
              >
                <ToggleButton value="casa">Casa</ToggleButton>
                <ToggleButton value="predio">Predio</ToggleButton>
                <ToggleButton value="comercial">Comercial</ToggleButton>
              </ToggleButtonGroup>
            </Box>

            {tipoLocal === 'predio' && (
              <>
                <Controller
                  name="nome_local"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Nome do predio / condominio"
                      placeholder="Ex: Edificio Jardim das Flores"
                      fullWidth
                      error={!!errors.nome_local}
                      helperText={errors.nome_local?.message}
                    />
                  )}
                />
                <Grid container spacing={2}>
                  <Grid size={{ xs: 6, sm: 3 }}>
                    <Controller name="apto" control={control} render={({ field }) => (
                      <TextField {...field} label="Apartamento" fullWidth error={!!errors.apto} helperText={errors.apto?.message} />
                    )} />
                  </Grid>
                  <Grid size={{ xs: 6, sm: 3 }}>
                    <Controller name="bloco" control={control} render={({ field }) => (
                      <TextField {...field} label="Bloco" fullWidth error={!!errors.bloco} helperText={errors.bloco?.message} />
                    )} />
                  </Grid>
                  <Grid size={{ xs: 6, sm: 3 }}>
                    <Controller name="torre" control={control} render={({ field }) => (
                      <TextField {...field} label="Torre" fullWidth error={!!errors.torre} helperText={errors.torre?.message} />
                    )} />
                  </Grid>
                  <Grid size={{ xs: 6, sm: 3 }}>
                    <Controller name="andar" control={control} render={({ field }) => (
                      <TextField {...field} label="Andar" fullWidth error={!!errors.andar} helperText={errors.andar?.message} />
                    )} />
                  </Grid>
                </Grid>
              </>
            )}

            {tipoLocal === 'comercial' && (
              <Controller
                name="nome_local"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Nome do estabelecimento"
                    placeholder="Ex: Colegio Planeta"
                    fullWidth
                    error={!!errors.nome_local}
                    helperText={errors.nome_local?.message}
                  />
                )}
              />
            )}

            {tipoLocal === 'casa' && (
              <Grid container spacing={2}>
                <Grid size={{ xs: 6, sm: 4 }}>
                  <Controller
                    name="quadra"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Quadra"
                        placeholder="Ex: 5"
                        fullWidth
                        error={!!errors.quadra}
                        helperText={errors.quadra?.message}
                      />
                    )}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 4 }}>
                  <Controller
                    name="lote"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Lote"
                        placeholder="Ex: 12"
                        fullWidth
                        error={!!errors.lote}
                        helperText={errors.lote?.message}
                      />
                    )}
                  />
                </Grid>
              </Grid>
            )}

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
                const tipoLocalAtual = watch('tipo_local') || 'casa';
                const nomeLocal = watch('nome_local')?.trim() || '';
                const apto = watch('apto')?.trim() || '';
                const quadra = watch('quadra') || '';
                const lote = watch('lote') || '';
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
                if (tipoLocalAtual === 'casa' && quadra) partes.push(`Qd ${quadra}`);
                if (tipoLocalAtual === 'casa' && lote) partes.push(`Lt ${lote}`);
                if (bairro) partes.push(bairro);
                if (cidade) partes.push(cidade);
                if (cep) partes.push(`CEP: ${cep}`);

                const enderecoBase = partes.join(', ');
                let prefixoLocal = '';
                if (tipoLocalAtual === 'predio') {
                  prefixoLocal = [nomeLocal || 'Prédio', apto ? `AP ${apto}` : null].filter(Boolean).join(' ');
                }
                if (tipoLocalAtual === 'comercial') {
                  prefixoLocal = nomeLocal || 'Comércio';
                }

                const enderecoCompleto = [prefixoLocal, enderecoBase].filter(Boolean).join(' - ');
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
