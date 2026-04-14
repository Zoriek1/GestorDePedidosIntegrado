/**
 * Step 1 - Dados do Cliente (Inteligente)
 * Autocomplete assíncrono para buscar cliente existente
 * FreeSolo: permite digitar nome novo se não encontrar
 */

import { useState, useCallback, useEffect } from 'react';
import { useFormContext, Controller, useWatch } from 'react-hook-form';
import {
  Box,
  TextField,
  Typography,
  Stack,
  Autocomplete,
  CircularProgress,
  Paper,
  Grid,
  Alert,
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import { PhoneInput } from '../../../../components/form';
import { useDebouncedValue } from '../../../../hooks/useDebouncedValue';
import { useCustomerSearch } from '../../../../api/endpoints/customers';
import { useFontesPedido } from '../../../../api/endpoints/fontes';
import type { Customer } from '../../../../api/endpoints/customers';
import type { PedidoFormData } from '../../schemas';
import { useAuth } from '../../../auth/authStore';
import { useUsers } from '../../../users/services/userApi';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  FormControlLabel,
  Button,
  Checkbox,
  Collapse,
} from '@mui/material';
import { MinimalCheckbox } from '../../../../components/uiverse/MinimalCheckbox/MinimalCheckbox';

// ============================================================================
// Componente
// ============================================================================

export function StepCliente() {
  const {
    control,
    setValue,
    watch,
    formState: { errors },
  } = useFormContext<PedidoFormData>();

  const { getUserRole } = useAuth();
  const isAdmin = getUserRole() === 'admin';
  const { data: usersData } = useUsers();
  const vendedores = (usersData ?? []).filter((u) => u.role === 'vendedor' && u.is_active);

  const origemAnuncio = useWatch({ control, name: 'origem_anuncio' });

  const [inputValue, setInputValue] = useState('');
  const [mesmoQueCliente, setMesmoQueCliente] = useState(false);
  const debouncedQuery = useDebouncedValue(inputValue.trim(), 300);
  
  // Buscar clientes
  const { data: searchData, isFetching } = useCustomerSearch(
    debouncedQuery.length >= 3 ? debouncedQuery : '',
    10
  );
  
  const customers = searchData?.clientes || [];
  const clienteId = watch('cliente_id');
  const hasSelectedCustomer = !!clienteId;
  const clienteNome = watch('cliente');
  const clienteModo = watch('cliente_modo');
  const fonteSelecionadaId = watch('fonte_pedido_id');
  const fonteLocked = typeof fonteSelecionadaId === 'number';

  // Sincronizar input controlado com valor do formulário (evita ghost value)
  useEffect(() => {
    // Usar setTimeout para evitar setState síncrono em effect
    const timer = setTimeout(() => {
      setInputValue(clienteNome || '');
    }, 0);
    return () => clearTimeout(timer);
  }, [clienteNome]);

  // Atualizar destinatário quando cliente mudar e checkbox estiver marcado
  useEffect(() => {
    if (mesmoQueCliente && clienteNome) {
      setValue('destinatario', clienteNome, { shouldValidate: true });
    }
  }, [clienteNome, mesmoQueCliente, setValue]);

  // Buscar fontes de pedido
  const { data: fontesData } = useFontesPedido(true);
  const fontes = fontesData?.fontes || [];

  // Quando selecionar um cliente do autocomplete
  const handleSelectCustomer = useCallback(
    (customer: Customer | null) => {
      if (customer) {
        setValue('cliente', customer.nome, { shouldValidate: true });
        setValue('telefone_cliente', customer.telefone || '', { shouldValidate: true });
        setValue('cliente_id', customer.id);
        setValue('cliente_modo', 'busca', { shouldValidate: true });
      } else {
        // Limpar seleção
        setValue('cliente_id', undefined);
        setValue('cliente_modo', 'novo', { shouldValidate: true });
      }
    },
    [setValue]
  );

  // Quando digitar nome manualmente (sem selecionar)
  const handleInputChange = useCallback(
    (_event: React.SyntheticEvent, newValue: string) => {
      setInputValue(newValue);
      setValue('cliente', newValue, { shouldValidate: true });
      // Se está digitando manualmente, limpar cliente_id
      if (!hasSelectedCustomer || newValue !== watch('cliente')) {
        setValue('cliente_id', undefined);
        setValue('cliente_modo', 'novo', { shouldValidate: true });
      }
    },
    [setValue, hasSelectedCustomer, watch]
  );

  const handleNovoClienteManual = useCallback(() => {
    setValue('cliente', '', { shouldValidate: true });
    setValue('telefone_cliente', '', { shouldValidate: true });
    setValue('cliente_id', undefined);
    setValue('cliente_modo', 'novo', { shouldValidate: true });
    setInputValue('');
    setMesmoQueCliente(false);
  }, [setValue]);

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 3 }}>
        <PersonIcon color="primary" />
        <Typography variant="h6" component="h2">
          Dados do Cliente
        </Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Digite o nome ou telefone para buscar um cliente existente, ou preencha para criar um novo.
      </Typography>

      <Stack spacing={2.5}>
        {/* Nome do Cliente - Autocomplete */}
        <Controller
          name="cliente"
          control={control}
          render={({ field }) => (
            <Autocomplete
              freeSolo
              options={customers}
              getOptionLabel={(option) => 
                typeof option === 'string' ? option : option.nome
              }
              filterOptions={(x) => x} // Desabilitar filtro local (API já filtra)
              inputValue={inputValue || field.value || ''}
              onInputChange={handleInputChange}
              onChange={(_event, newValue) => {
                if (typeof newValue === 'string') {
                  // Digitou manualmente (freeSolo)
                  field.onChange(newValue);
                  setValue('cliente_id', undefined);
                  setValue('cliente_modo', 'novo', { shouldValidate: true });
                } else if (newValue) {
                  // Selecionou da lista
                  handleSelectCustomer(newValue);
                } else {
                  // Limpou
                  field.onChange('');
                  handleSelectCustomer(null);
                  setValue('cliente_modo', 'novo', { shouldValidate: true });
                }
              }}
              loading={isFetching}
              loadingText="Buscando..."
              noOptionsText={
                debouncedQuery.length >= 3 
                  ? "Nenhum cliente encontrado. Digite para criar novo."
                  : "Digite pelo menos 3 caracteres"
              }
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Nome do Cliente"
                  placeholder="Digite para buscar ou criar..."
                  required
                  error={!!errors.cliente}
                  helperText={errors.cliente?.message}
                  autoFocus
                  slotProps={{
                    input: {
                      ...params.InputProps,
                      endAdornment: (
                        <>
                          {isFetching && <CircularProgress size={20} />}
                          {params.InputProps.endAdornment}
                        </>
                      ),
                    },
                  }}
                />
              )}
              renderOption={(props, option) => {
                const { key, ...otherProps } = props;
                return (
                  <Paper
                    component="li"
                    key={key}
                    {...otherProps}
                    elevation={0}
                    sx={{ 
                      py: 1.5,
                      borderBottom: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Stack>
                      <Typography variant="body1" fontWeight="medium">
                        {option.nome}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {option.telefone}
                      </Typography>
                    </Stack>
                  </Paper>
                );
              }}
            />
          )}
        />

        {/* Indicador de cliente selecionado ou novo */}
        {hasSelectedCustomer ? (
          <Alert 
            variant="outlined" 
            severity="success"
            icon={<PersonIcon />}
            action={
              <Button
                size="small"
                variant="text"
                onClick={handleNovoClienteManual}
                sx={{ textTransform: 'none' }}
              >
                Cadastrar novo
              </Button>
            }
            sx={{ mb: 2 }}
          >
            Cliente existente selecionado (ID: {clienteId})
          </Alert>
        ) : inputValue.length >= 2 ? (
          <Alert 
            variant="outlined" 
            severity="info"
            icon={<PersonAddIcon />}
            sx={{ mb: 2 }}
          >
            <Typography variant="body2" component="div">
              Novo cliente será cadastrado automaticamente
              {clienteModo === 'novo' && (
                <Typography variant="caption" display="block" sx={{ mt: 0.5, opacity: 0.8 }}>
                  Preencha nome e telefone para prosseguir.
                </Typography>
              )}
            </Typography>
          </Alert>
        ) : null}

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            {/* Telefone/WhatsApp */}
            <Controller
              name="telefone_cliente"
              control={control}
              render={({ field }) => (
                <PhoneInput
                  {...field}
                  label="Telefone/WhatsApp"
                  fullWidth
                  required
                  disabled={hasSelectedCustomer} // ReadOnly se cliente existente
                  error={!!errors.telefone_cliente}
                  helperText={
                    hasSelectedCustomer
                      ? 'Telefone do cliente selecionado'
                      : errors.telefone_cliente?.message || 'Formato: (00) 00000-0000'
                  }
                />
              )}
            />
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <Controller
              name="codigo_whatsapp"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Código do WhatsApp (Opcional)"
                  placeholder="Ex: A3F9"
                  fullWidth
                  value={field.value ?? ''}
                  error={!!errors.codigo_whatsapp}
                  helperText={errors.codigo_whatsapp?.message || 'Use o código exibido na mensagem do cliente'}
                />
              )}
            />
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            {/* Destinatário com Checkbox "Mesmo que o cliente" */}
            <Box>
              <Controller
                name="destinatario"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Para (Destinatário)"
                    placeholder="Nome do destinatário"
                    fullWidth
                    required
                    error={!!errors.destinatario}
                    helperText={errors.destinatario?.message}
                  />
                )}
              />
              <FormControlLabel
                control={
                  <MinimalCheckbox
                    checked={mesmoQueCliente}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      setMesmoQueCliente(checked);
                      if (checked) {
                        setValue('destinatario', clienteNome || '', { shouldValidate: true });
                      }
                    }}
                    aria-label="Mesmo que o cliente"
                  />
                }
                label="Mesmo que o cliente"
                sx={{ mt: 1 }}
              />
            </Box>
          </Grid>
        </Grid>

        {/* Tipo de Pedido */}
        <Controller
          name="tipo_pedido"
          control={control}
          render={({ field }) => (
            <FormControl fullWidth required error={!!errors.tipo_pedido}>
              <InputLabel>Tipo de Pedido</InputLabel>
              <Select {...field} label="Tipo de Pedido">
                <MenuItem value="Entrega">Entrega</MenuItem>
                <MenuItem value="Retirada">Retirada</MenuItem>
              </Select>
              {errors.tipo_pedido && (
                <FormHelperText>{errors.tipo_pedido.message}</FormHelperText>
              )}
            </FormControl>
          )}
        />

        {/* Fonte do Pedido */}
        <Controller
          name="fonte_pedido_id"
          control={control}
          render={({ field }) => (
            <FormControl fullWidth error={!!errors.fonte_pedido_id}>
              <InputLabel>Fonte do Pedido</InputLabel>
              {fonteLocked && (
                <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
                  Fonte selecionada no início e bloqueada para edição.
                </Typography>
              )}
              <Select
                {...field}
                label="Fonte do Pedido"
                value={field.value || ''}
                onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : undefined)}
                disabled={fonteLocked}
              >
                <MenuItem value="">
                  <em>Não informado</em>
                </MenuItem>
                {fontes.map((fonte) => (
                  <MenuItem key={fonte.id} value={fonte.id}>
                    {fonte.nome}
                  </MenuItem>
                ))}
              </Select>
              {errors.fonte_pedido_id && (
                <FormHelperText>{errors.fonte_pedido_id.message}</FormHelperText>
              )}
            </FormControl>
          )}
        />

        {/* Vendedor Responsável (apenas admin) */}
        {isAdmin && vendedores.length > 0 && (
          <Controller
            name="vendedor_id"
            control={control}
            render={({ field }) => (
              <FormControl fullWidth>
                <InputLabel>Vendedor Responsável (Opcional)</InputLabel>
                <Select
                  {...field}
                  label="Vendedor Responsável (Opcional)"
                  value={field.value ?? ''}
                  onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : undefined)}
                >
                  <MenuItem value="">
                    <em>Não atribuído</em>
                  </MenuItem>
                  {vendedores.map((v) => (
                    <MenuItem key={v.id} value={v.id}>
                      {v.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          />
        )}

        {/* Origem: anúncio Meta Ads */}
        <Controller
          name="origem_anuncio"
          control={control}
          render={({ field }) => (
            <FormControlLabel
              control={
                <Checkbox
                  checked={field.value ?? false}
                  onChange={(e) => {
                    field.onChange(e.target.checked);
                    if (!e.target.checked) setValue('fbclid', '');
                  }}
                />
              }
              label="Pedido vindo de anúncio?"
            />
          )}
        />

        <Collapse in={origemAnuncio}>
          <Controller
            name="fbclid"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Facebook Click ID (fbclid)"
                placeholder="Ex: AbCdEfGhIjKlMnOpQrStUvWxYz"
                fullWidth
                required={origemAnuncio}
                error={!!errors.fbclid}
                helperText={errors.fbclid?.message || 'Cole o fbclid da mensagem do WhatsApp'}
              />
            )}
          />
        </Collapse>
      </Stack>
    </Box>
  );
}

export default StepCliente;
