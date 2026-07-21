import { useEffect, useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { CheckCircle, MapPin, XCircle } from 'lucide-react';
import { usePatchField, useValidateField } from '../hooks/useConfig';
import { useConfirm } from '../../../components/system/useConfirm';
import { useCepLookup } from '../../pedidos/useCases/cepLookup';
import { CepInput } from '../../../components/form';
import type { ChannelDef } from '../constants';
import type { IntegrationSettingsConfig } from '../services/configService';

interface Props {
  open: boolean;
  channel: ChannelDef;
  config: IntegrationSettingsConfig;
  onClose: () => void;
}

type FieldStatus = 'idle' | 'saving' | 'saved' | 'validating' | 'valid' | 'invalid' | 'error';
type FieldState = Record<string, { status: FieldStatus; error?: string; value: unknown }>;

export function IntegrationModal({ open, channel, config, onClose }: Props) {
  const patchField = usePatchField();
  const validateField = useValidateField();
  const confirm = useConfirm();
  const { lookupCep, isLoading: isCepLoading, result: cepResult } = useCepLookup();

  const [fields, setFields] = useState<FieldState>({});
  const [cepResolved, setCepResolved] = useState<{ cidade: string; uf: string } | null>(null);

  useEffect(() => {
    if (!open || !channel.fields) return;
    const initial: FieldState = {};
    for (const f of channel.fields) {
      let val = config[f.key as keyof IntegrationSettingsConfig];
      if (f.type === 'password') val = '';
      initial[f.key] = { status: 'idle', value: val ?? '' };
    }
    setFields(initial);
    setCepResolved(null);
  }, [open, channel, config]);

  const handleSave = async (fieldKey: string) => {
    const fieldDef = channel.fields!.find(f => f.key === fieldKey)!;
    let value = fields[fieldKey]?.value;

    if (fieldDef.type === 'password' && value === '') return;
    if (fieldDef.type === 'boolean') value = Boolean(value);
    if (fieldKey === 'loja_cep' && typeof value === 'string' && value && !value.includes('-')) {
      value = `${value.slice(0, 5)}-${value.slice(5)}`;
    }

    setFields(prev => ({ ...prev, [fieldKey]: { ...prev[fieldKey], status: 'saving' } }));
    try {
      await patchField.mutateAsync({ channel: channel.id, field: fieldKey, value: value || null });
      setFields(prev => ({ ...prev, [fieldKey]: { ...prev[fieldKey], status: 'saved' } }));
    } catch (err) {
      setFields(prev => ({
        ...prev,
        [fieldKey]: { ...prev[fieldKey], status: 'error', error: (err as Error).message },
      }));
    }
  };

  const handleValidate = async (fieldKey: string) => {
    const fieldDef = channel.fields!.find(f => f.key === fieldKey)!;
    let value = fields[fieldKey]?.value;
    if (fieldDef.type === 'password' && value === '') value = undefined;
    if (fieldDef.type === 'boolean') return;

    setFields(prev => ({ ...prev, [fieldKey]: { ...prev[fieldKey], status: 'validating' } }));
    try {
      const result = await validateField.mutateAsync({
        channel: channel.id,
        field: fieldKey,
        value: value as string,
      });
      setFields(prev => ({
        ...prev,
        [fieldKey]: {
          ...prev[fieldKey],
          status: result.ok ? 'valid' : 'invalid',
          error: result.error ?? undefined,
        },
      }));
    } catch (err) {
      setFields(prev => ({
        ...prev,
        [fieldKey]: { ...prev[fieldKey], status: 'error', error: (err as Error).message },
      }));
    }
  };

  const handleSaveAll = async () => {
    const promises = channel.fields!.map(f => handleSave(f.key));
    await Promise.allSettled(promises);
    onClose();
  };

  const handleRemoveSecret = async (fieldKey: string) => {
    const confirmed = await confirm({
      title: 'Remover credencial',
      description: 'A integração deixará de funcionar até uma nova credencial ser salva.',
      confirmText: 'Remover credencial',
      confirmColor: 'error',
    });
    if (confirmed) {
      try {
        await patchField.mutateAsync({ channel: channel.id, field: fieldKey, value: null });
        setFields(prev => ({ ...prev, [fieldKey]: { ...prev[fieldKey], value: '', status: 'saved' } }));
      } catch (err) {
        setFields(prev => ({
          ...prev,
          [fieldKey]: { ...prev[fieldKey], status: 'error', error: (err as Error).message },
        }));
      }
    }
  };

  const handleCepComplete = async (cep: string) => {
    if (!open || channel.id !== 'dados_operacionais') return;
    const digits = cep.replace(/\D/g, '');
    if (digits.length !== 8) return;
    const result = await lookupCep(cep);
    if (result && result.cidade && result.uf) {
      setCepResolved({ cidade: result.cidade, uf: result.uf });
    } else {
      setCepResolved(null);
    }
  };

  const handleUseAddress = () => {
    if (!cepResult) return;
    const parts = [cepResult.rua, cepResult.bairro, cepResult.cidade, cepResult.uf].filter(Boolean);
    const composed = parts.join(', ');
    if (composed) {
      setFields(prev => ({
        ...prev,
        endereco_floricultura: { ...prev.endereco_floricultura!, value: composed },
      }));
    }
  };

  const statusIcon = (status: FieldStatus) => {
    if (status === 'saved' || status === 'valid') return <CheckCircle color="success" fontSize="small" />;
    if (status === 'invalid' || status === 'error') return <XCircle color="error" fontSize="small" />;
    if (status === 'saving' || status === 'validating') return <CircularProgress size={16} />;
    return null;
  };

  if (!channel.fields) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{channel.label}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {channel.fields.map(fieldDef => {
            const state = fields[fieldDef.key];
            if (!state) return null;
            const hasSavedSecret =
              fieldDef.type === 'password' &&
              Boolean(config[`has_${fieldDef.key}` as keyof IntegrationSettingsConfig]);

            return (
              <Box key={fieldDef.key}>
                {fieldDef.type !== 'boolean' && (
                  <Typography variant="caption" color="text.secondary">
                    {fieldDef.label}
                  </Typography>
                )}
                <Stack direction="row" spacing={1} alignItems="center">
                  {fieldDef.type === 'boolean' ? (
                    <FormControlLabel
                      control={
                        <Switch
                          checked={Boolean(state.value)}
                          onChange={(_, v) =>
                            setFields(prev => ({
                              ...prev,
                              [fieldDef.key]: { ...prev[fieldDef.key], value: v },
                            }))
                          }
                        />
                      }
                      label={fieldDef.label}
                    />
                  ) : fieldDef.type === 'select' ? (
                    <TextField
                      select
                      size="small"
                      fullWidth
                      value={state.value}
                      onChange={e =>
                        setFields(prev => ({
                          ...prev,
                          [fieldDef.key]: { ...prev[fieldDef.key], value: e.target.value },
                        }))
                      }
                    >
                      {fieldDef.options?.map(opt => (
                        <MenuItem key={opt} value={opt}>
                          {opt}
                        </MenuItem>
                      ))}
                    </TextField>
                  ) : fieldDef.key === 'loja_cep' && channel.id === 'dados_operacionais' ? (
                    <CepInput
                      size="small"
                      fullWidth
                      label=""
                      value={state.value as string}
                      onChange={(v) =>
                        setFields(prev => ({
                          ...prev,
                          [fieldDef.key]: { ...prev[fieldDef.key], value: v },
                        }))
                      }
                      isLoading={isCepLoading}
                      onComplete={handleCepComplete}
                      error={state.status === 'invalid' || state.status === 'error'}
                      helperText={
                        state.status === 'invalid' || state.status === 'error'
                          ? state.error
                          : cepResolved
                            ? `${cepResolved.cidade}/${cepResolved.uf}`
                            : undefined
                      }
                    />
                  ) : (
                    <TextField
                      size="small"
                      fullWidth
                      type={fieldDef.type === 'password' ? 'password' : 'text'}
                      placeholder={fieldDef.placeholder}
                      value={state.value}
                      onChange={e =>
                        setFields(prev => ({
                          ...prev,
                          [fieldDef.key]: { ...prev[fieldDef.key], value: e.target.value },
                        }))
                      }
                      helperText={
                        state.status === 'invalid' || state.status === 'error'
                          ? state.error
                          : fieldDef.type === 'password' && hasSavedSecret
                            ? 'Deixe vazio para manter a credencial atual.'
                            : undefined
                      }
                      error={state.status === 'invalid' || state.status === 'error'}
                      autoComplete="new-password"
                    />
                  )}

                  {statusIcon(state.status)}

                  {fieldDef.type !== 'boolean' && (
                    <>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleSave(fieldDef.key)}
                        disabled={state.status === 'saving'}
                      >
                        Salvar
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleValidate(fieldDef.key)}
                        disabled={state.status === 'validating'}
                      >
                        Validar
                      </Button>
                    </>
                  )}

                  {fieldDef.type === 'password' && hasSavedSecret && (
                    <Button size="small" color="error" onClick={() => handleRemoveSecret(fieldDef.key)}>
                      Remover
                    </Button>
                  )}
                </Stack>
                {fieldDef.key === 'endereco_floricultura' &&
                  channel.id === 'dados_operacionais' &&
                  cepResult &&
                  cepResult.cidade &&
                  cepResult.uf && (
                    <Button
                      size="small"
                      startIcon={<MapPin />}
                      onClick={handleUseAddress}
                      sx={{ mt: 0.5 }}
                    >
                      Usar este endereço
                    </Button>
                  )}
              </Box>
            );
          })}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancelar</Button>
        <Button variant="contained" onClick={handleSaveAll}>
          Salvar e sair
        </Button>
      </DialogActions>
    </Dialog>
  );
}