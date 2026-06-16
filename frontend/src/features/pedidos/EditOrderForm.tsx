/**
 * EditOrderForm — edição de pedido em PÁGINA ÚNICA (rolável), sem etapas.
 * Reaproveita as seções MUI já existentes (StepCliente/StepProduto/StepEntrega/StepPagamento)
 * e o mesmo schema/validação do wizard. Ideal para ajustes rápidos de 1-2 campos.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm, FormProvider, useWatch } from 'react-hook-form';
import type { FieldPath } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Box, Stack, Button, Divider, Alert, CircularProgress } from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import {
  pedidoFormSchema, pedidoFormDefaultValues, transformFormToApiPayload, type PedidoFormData,
} from './schemas';
import { StepCliente, StepProduto, StepEntrega, StepPagamento } from './components/WizardSteps';

interface EditOrderFormProps {
  onSubmit: (data: Record<string, unknown>) => Promise<boolean>;
  isSubmitting?: boolean;
  initialData?: Partial<PedidoFormData>;
}

export function EditOrderForm({ onSubmit, isSubmitting = false, initialData }: EditOrderFormProps) {
  const methods = useForm<PedidoFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(pedidoFormSchema) as any,
    defaultValues: { ...pedidoFormDefaultValues, ...initialData },
    mode: 'onBlur',
  });
  const { control, getValues, setError, reset } = methods;
  const tipoPedido = useWatch({ control, name: 'tipo_pedido' });
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Reaplica initialData quando o pedido carregado muda.
  const initialDataKey = useMemo(() => JSON.stringify(initialData ?? {}), [initialData]);
  const appliedRef = useRef<string | null>(null);
  useEffect(() => {
    if (!initialData) return;
    if (appliedRef.current === initialDataKey) return;
    appliedRef.current = initialDataKey;
    reset({ ...pedidoFormDefaultValues, ...initialData });
  }, [initialData, initialDataKey, reset]);

  const handleSave = async () => {
    const data = getValues();
    const result = pedidoFormSchema.safeParse(data);
    if (!result.success) {
      result.error.issues.forEach((err) => {
        setError(err.path.join('.') as FieldPath<PedidoFormData>, { type: 'manual', message: err.message });
      });
      setErrorMsg('Revise os campos destacados antes de salvar.');
      return;
    }
    setErrorMsg(null);
    await onSubmit(transformFormToApiPayload(data));
  };

  return (
    <FormProvider {...methods}>
      <Stack spacing={3} divider={<Divider flexItem />}>
        <Box><StepCliente /></Box>
        <Box><StepProduto /></Box>
        {tipoPedido === 'Entrega' && <Box><StepEntrega /></Box>}
        <Box><StepPagamento /></Box>
      </Stack>

      {errorMsg && <Alert severity="error" sx={{ mt: 2 }}>{errorMsg}</Alert>}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
        <Button
          type="button"
          variant="contained"
          color="primary"
          onClick={handleSave}
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={18} color="inherit" /> : <SaveIcon />}
        >
          {isSubmitting ? 'Salvando…' : 'Salvar alterações'}
        </Button>
      </Box>
    </FormProvider>
  );
}

export default EditOrderForm;
