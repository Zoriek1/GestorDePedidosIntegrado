/**
 * Step Entrega — Logística de Entrega (Inteligente)
 * - CEP com auto-preenchimento via ViaCEP + busca reversa por endereço
 * - Tipo de local (Casa / Prédio / Comercial) com campos condicionais
 * - Cartão de Entrega (preview ao vivo da visão do entregador)
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
  MenuItem,
  ToggleButton,
  ToggleButtonGroup,
  Collapse,
  CircularProgress,
  Link,
  List,
  ListItemButton,
  ListItemText,
} from '@mui/material';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import EditIcon from '@mui/icons-material/Edit';
import LockIcon from '@mui/icons-material/Lock';
import SearchIcon from '@mui/icons-material/Search';
import HomeOutlinedIcon from '@mui/icons-material/HomeOutlined';
import ApartmentOutlinedIcon from '@mui/icons-material/ApartmentOutlined';
import StorefrontOutlinedIcon from '@mui/icons-material/StorefrontOutlined';
import { CepInput } from '../../../../components/form';
import { useCepLookup, searchCepByAddress, type AddressSearchItem } from '../../useCases/cepLookup';
import { useClienteEnderecos } from '../../../../api/endpoints/customers';
import type { PedidoFormData } from '../../schemas';
import { DeliveryInfoCard } from '../DeliveryInfoCard';
import { formatPhone } from '../OrderCardHelpers';

// ============================================================================
// Busca de CEP por endereço (ViaCEP reverso via proxy backend)
// ============================================================================

function BuscaCepPorEndereco({
  cidadeAtual,
  onPick,
}: {
  cidadeAtual: string;
  onPick: (item: AddressSearchItem) => void;
}) {
  const [open, setOpen] = useState(false);
  const [uf, setUf] = useState('GO');
  const [cidade, setCidade] = useState(cidadeAtual || 'Goiânia');
  const [rua, setRua] = useState('');
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');
  const [resultados, setResultados] = useState<AddressSearchItem[] | null>(null);

  const buscar = useCallback(async () => {
    setErro('');
    setResultados(null);
    if (uf.length !== 2 || cidade.trim().length < 3 || rua.trim().length < 3) {
      setErro('Informe UF (2 letras), cidade e parte da rua (mín. 3 letras).');
      return;
    }
    setLoading(true);
    try {
      const res = await searchCepByAddress(uf, cidade, rua);
      if (res.length === 0) setErro('Nenhum endereço encontrado.');
      else setResultados(res);
    } catch {
      setErro('Falha na consulta. Verifique a conexão.');
    } finally {
      setLoading(false);
    }
  }, [uf, cidade, rua]);

  return (
    <Box>
      <Link
        component="button"
        type="button"
        underline="hover"
        onClick={() => setOpen((v) => !v)}
        sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, fontSize: 13 }}
      >
        <SearchIcon sx={{ fontSize: 15 }} />
        {open ? 'Fechar busca por endereço' : 'Não sei o CEP — buscar pelo endereço'}
      </Link>
      <Collapse in={open}>
        <Box sx={{ mt: 1, p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 1.5, bgcolor: 'action.hover' }}>
          <Grid container spacing={1.5}>
            <Grid size={{ xs: 4, sm: 2 }}>
              <TextField
                label="UF"
                size="small"
                fullWidth
                value={uf}
                onChange={(e) => setUf(e.target.value.toUpperCase().slice(0, 2))}
                inputProps={{ maxLength: 2, style: { textTransform: 'uppercase' } }}
              />
            </Grid>
            <Grid size={{ xs: 8, sm: 5 }}>
              <TextField label="Cidade" size="small" fullWidth value={cidade} onChange={(e) => setCidade(e.target.value)} />
            </Grid>
            <Grid size={{ xs: 12, sm: 5 }}>
              <TextField
                label="Rua"
                size="small"
                fullWidth
                value={rua}
                onChange={(e) => setRua(e.target.value)}
                placeholder="Ex.: Avenida 85"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    buscar();
                  }
                }}
              />
            </Grid>
          </Grid>
          <Button
            variant="contained"
            size="small"
            onClick={buscar}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={14} color="inherit" /> : <SearchIcon />}
            sx={{ mt: 1.5 }}
          >
            Buscar
          </Button>
          {erro && (
            <Typography variant="caption" color="error" sx={{ display: 'block', mt: 1 }}>
              {erro}
            </Typography>
          )}
          {resultados && (
            <List dense sx={{ mt: 1, maxHeight: 220, overflow: 'auto' }}>
              {resultados.map((item, i) => (
                <ListItemButton
                  key={`${item.cep}-${i}`}
                  onClick={() => {
                    onPick(item);
                    setOpen(false);
                    setResultados(null);
                    setRua('');
                  }}
                  sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1, mb: 0.5 }}
                >
                  <ListItemText
                    primary={item.rua || '(sem logradouro)'}
                    secondary={`${item.bairro} · ${item.cidade}/${item.uf} — CEP ${item.cep}`}
                  />
                </ListItemButton>
              ))}
            </List>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}

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

  const tipoPedido = useWatch({ control, name: 'tipo_pedido' });
  const isEntrega = tipoPedido === 'Entrega';
  const tipoLocal = useWatch({ control, name: 'tipo_local' }) || 'casa';

  // Campos observados para o preview ao vivo do Cartão de Entrega.
  const previewFields = useWatch({
    control,
    name: [
      'destinatario',
      'rua',
      'numero',
      'complemento',
      'bairro',
      'cidade',
      'nome_local',
      'apartamento',
      'bloco',
      'torre',
      'andar',
      'obs_entrega',
      'horario',
      'telefone_cliente',
    ],
  });
  const [
    pvDestinatario,
    pvRua,
    pvNumero,
    pvComplemento,
    pvBairro,
    pvCidade,
    pvNomeLocal,
    pvApto,
    pvBloco,
    pvTorre,
    pvAndar,
    pvObs,
    pvHorario,
    pvTelefone,
  ] = previewFields;

  const enderecoPreview = [
    [pvRua, pvNumero].filter(Boolean).join(', '),
    pvComplemento,
    [pvBairro, pvCidade].filter(Boolean).join(' · '),
  ]
    .filter(Boolean)
    .join(' — ');

  const [isAddressLocked, setIsAddressLocked] = useState(true);

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
  };

  const { lookupCep, isLoading: isCepLoading, error: cepError } = useCepLookup();

  const handleCepComplete = useCallback(
    async (cep: string) => {
      const result = await lookupCep(cep);
      if (result) {
        setValue('rua', result.rua, { shouldValidate: true });
        setValue('bairro', result.bairro, { shouldValidate: true });
        setValue('cidade', result.cidade, { shouldValidate: true });
        setIsAddressLocked(true);
      }
    },
    [lookupCep, setValue]
  );

  const handlePickEndereco = useCallback(
    (item: AddressSearchItem) => {
      setValue('cep', item.cep.replace('-', ''), { shouldValidate: true });
      setValue('rua', item.rua, { shouldValidate: true });
      setValue('bairro', item.bairro, { shouldValidate: true });
      setValue('cidade', item.cidade, { shouldValidate: true });
      setIsAddressLocked(true);
    },
    [setValue]
  );

  const handleToggleAddressLock = () => setIsAddressLocked((prev) => !prev);

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

      <Stack spacing={2.5}>
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

        {/* CEP + Rua */}
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
                  slotProps={{ input: { readOnly: isAddressLocked } }}
                  sx={{ bgcolor: isAddressLocked ? 'grey.100' : 'inherit' }}
                />
              )}
            />
          </Grid>
        </Grid>

        {/* Busca de CEP por endereço */}
        <BuscaCepPorEndereco cidadeAtual={watch('cidade') || ''} onPick={handlePickEndereco} />

        {/* Número + Bairro + Cidade */}
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
                  slotProps={{ input: { readOnly: isAddressLocked } }}
                  sx={{ bgcolor: isAddressLocked ? 'grey.100' : 'inherit' }}
                />
              )}
            />
          </Grid>
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
                  slotProps={{ input: { readOnly: isAddressLocked } }}
                  sx={{ bgcolor: isAddressLocked ? 'grey.100' : 'inherit' }}
                />
              )}
            />
          </Grid>
        </Grid>

        <Controller
          name="obs_entrega"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="Ponto de Referência"
              placeholder="Ex: Casa amarela, portão preto, ao lado da farmácia"
              fullWidth
              error={!!errors.obs_entrega}
              helperText={errors.obs_entrega?.message}
            />
          )}
        />

        {/* Tipo de local */}
        <Box>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            Tipo de local
          </Typography>
          <Controller
            name="tipo_local"
            control={control}
            render={({ field }) => (
              <ToggleButtonGroup
                exclusive
                fullWidth
                color="primary"
                value={field.value || 'casa'}
                onChange={(_e, value) => {
                  if (value) field.onChange(value);
                }}
              >
                <ToggleButton value="casa">
                  <HomeOutlinedIcon sx={{ mr: 0.75, fontSize: 20 }} /> Casa
                </ToggleButton>
                <ToggleButton value="predio">
                  <ApartmentOutlinedIcon sx={{ mr: 0.75, fontSize: 20 }} /> Prédio
                </ToggleButton>
                <ToggleButton value="comercial">
                  <StorefrontOutlinedIcon sx={{ mr: 0.75, fontSize: 20 }} /> Comercial
                </ToggleButton>
              </ToggleButtonGroup>
            )}
          />
        </Box>

        {/* Casa: Quadra + Lote + Complemento */}
        <Collapse in={tipoLocal === 'casa'} unmountOnExit>
          <Stack spacing={2}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 4 }}>
                <Controller
                  name="quadra"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} label="Quadra" placeholder="Ex: 5" fullWidth />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 4 }}>
                <Controller
                  name="lote"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} label="Lote" placeholder="Ex: 12" fullWidth />
                  )}
                />
              </Grid>
            </Grid>
            <Controller
              name="complemento"
              control={control}
              render={({ field }) => (
                <TextField {...field} label="Complemento" placeholder="Ex: Fundos, casa 2" fullWidth />
              )}
            />
          </Stack>
        </Collapse>

        {/* Prédio: nome + AP/Bloco/Torre/Andar */}
        <Collapse in={tipoLocal === 'predio'} unmountOnExit>
          <Stack spacing={2}>
            <Controller
              name="nome_local"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Nome do prédio / condomínio"
                  placeholder="Ex.: Edifício Jardim das Flores"
                  fullWidth
                  required
                  error={!!errors.nome_local}
                  helperText={errors.nome_local?.message}
                />
              )}
            />
            <Grid container spacing={2}>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Controller
                  name="apartamento"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Apartamento"
                      fullWidth
                      required
                      error={!!errors.apartamento}
                      helperText={errors.apartamento?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Controller
                  name="bloco"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Bloco" fullWidth />}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Controller
                  name="torre"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Torre" fullWidth />}
                />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Controller
                  name="andar"
                  control={control}
                  render={({ field }) => <TextField {...field} label="Andar" fullWidth />}
                />
              </Grid>
            </Grid>
          </Stack>
        </Collapse>

        {/* Comercial: nome do estabelecimento */}
        <Collapse in={tipoLocal === 'comercial'} unmountOnExit>
          <Controller
            name="nome_local"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Nome do estabelecimento"
                placeholder="Ex.: Colégio Planeta Vestibulares"
                fullWidth
                required
                error={!!errors.nome_local}
                helperText={errors.nome_local?.message}
              />
            )}
          />
        </Collapse>

        {/* Endereço completo */}
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

        <Button
          variant="outlined"
          onClick={() => {
            const rua = watch('rua') || '';
            const numero = watch('numero') || '';
            const isCasa = (watch('tipo_local') || 'casa') === 'casa';
            const isPredio = watch('tipo_local') === 'predio';
            const quadra = watch('quadra') || '';
            const lote = watch('lote') || '';
            const nomeLocal = watch('nome_local') || '';
            const apartamento = watch('apartamento') || '';
            const bloco = watch('bloco') || '';
            const torre = watch('torre') || '';
            const andar = watch('andar') || '';
            const bairro = watch('bairro') || '';
            const cidade = watch('cidade') || '';
            const cep = watch('cep') || '';

            const partes: string[] = [];
            if (rua) {
              if (numero && numero !== '0' && numero.toUpperCase() !== 'S/N' && numero.toUpperCase() !== 'SN') {
                partes.push(`${rua}, ${numero}`);
              } else {
                partes.push(rua);
              }
            }
            if (isCasa && quadra) partes.push(`Qd ${quadra}`);
            if (isCasa && lote) partes.push(`Lt ${lote}`);
            if (nomeLocal) partes.push(nomeLocal);
            if (isPredio && apartamento) partes.push(`AP ${apartamento}`);
            if (isPredio && bloco) partes.push(`Bloco ${bloco}`);
            if (isPredio && torre) partes.push(`Torre ${torre}`);
            if (isPredio && andar) partes.push(`${andar}º andar`);
            if (bairro) partes.push(bairro);
            if (cidade) partes.push(cidade);
            if (cep) partes.push(`CEP: ${cep}`);

            setValue('endereco', partes.join(', '), { shouldValidate: true });
          }}
          sx={{ alignSelf: 'flex-start' }}
        >
          Gerar Endereço Automático
        </Button>

        {isAddressLocked && (
          <Alert severity="info" sx={{ mt: 1 }}>
            Os campos Rua, Bairro e Cidade foram preenchidos pelo CEP. Clique no{' '}
            <LockIcon fontSize="small" sx={{ verticalAlign: 'middle' }} /> para editar manualmente se necessário.
          </Alert>
        )}

        {/* Cartão de Entrega — preview ao vivo da visão do entregador */}
        <Box>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            Cartão de Entrega (prévia)
          </Typography>
          <DeliveryInfoCard
            destinatario={pvDestinatario}
            endereco={enderecoPreview}
            tipoLocal={tipoLocal}
            nomeLocal={pvNomeLocal}
            apartamento={pvApto}
            bloco={pvBloco}
            torre={pvTorre}
            andar={pvAndar}
            referencia={pvObs}
            horario={pvHorario}
            telefone={pvTelefone ? formatPhone(pvTelefone) : undefined}
          />
        </Box>
      </Stack>
    </Box>
  );
}

export default StepEntrega;
