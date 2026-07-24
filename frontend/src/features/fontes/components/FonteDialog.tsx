/**
 * Fonte Dialog Component
 * Modal para criar/editar fonte de pedido
 */

import { useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  Stack,
} from '@mui/material';
import { useForm, Controller } from 'react-hook-form';
import type { FontePedido, CreateFontePayload, UpdateFontePayload } from '../../../api/endpoints/fontes';

export interface FonteDialogProps {
  open: boolean;
  fonte?: FontePedido | null;
  onClose: () => void;
  onSubmit: (data: CreateFontePayload | UpdateFontePayload) => void;
  isLoading?: boolean;
}

export function FonteDialog({ open, fonte, onClose, onSubmit, isLoading }: FonteDialogProps) {
  const { control, handleSubmit, reset, formState: { errors } } = useForm<CreateFontePayload>({
    defaultValues: {
      nome: '',
      ativo: true,
    },
  });

  useEffect(() => {
    if (fonte) {
      reset({
        nome: fonte.nome,
        ativo: fonte.ativo,
      });
    } else {
      reset({
        nome: '',
        ativo: true,
      });
    }
  }, [fonte, reset]);

  const handleFormSubmit = (data: CreateFontePayload) => {
    onSubmit(data);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogTitle>{fonte ? 'Editar Fonte' : 'Nova Fonte'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Controller
              name="nome"
              control={control}
              rules={{ required: 'Nome é obrigatório', minLength: { value: 2, message: 'Nome deve ter pelo menos 2 caracteres' } }}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Nome da Fonte"
                  fullWidth
                  required
                  error={!!errors.nome}
                  helperText={errors.nome?.message}
                  autoFocus
                />
              )}
            />
            <Controller
              name="ativo"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Checkbox {...field} checked={field.value} />}
                  label="Ativa"
                />
              )}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button type="submit" variant="contained" disabled={isLoading}>
            {isLoading ? 'Salvando…' : fonte ? 'Atualizar' : 'Criar'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
