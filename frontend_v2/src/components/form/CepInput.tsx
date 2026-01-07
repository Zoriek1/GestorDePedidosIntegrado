/**
 * CepInput - Input de CEP com Máscara
 * Formato: 99999-999
 * Integração com MUI TextField e react-hook-form
 */

import { forwardRef, useCallback, useRef } from 'react';
import TextField, { TextFieldProps } from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import CircularProgress from '@mui/material/CircularProgress';
import SearchIcon from '@mui/icons-material/Search';

interface CepInputProps extends Omit<TextFieldProps, 'onChange' | 'value'> {
  value: string | undefined;
  onChange: (value: string) => void;
  /** Se true, mostra spinner de loading */
  isLoading?: boolean;
  /** Callback quando o CEP completo é inserido (8 dígitos) */
  onComplete?: (cep: string) => void;
}

/**
 * Aplica máscara de CEP (99999-999)
 */
function applyCepMask(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 8);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

/**
 * Campo de entrada para CEP brasileiro
 * Aplica máscara automática conforme digitação
 * 
 * @example
 * <Controller
 *   name="cep"
 *   control={control}
 *   render={({ field }) => (
 *     <CepInput
 *       {...field}
 *       label="CEP"
 *       onComplete={handleCepComplete}
 *       isLoading={isFetchingAddress}
 *       error={!!errors.cep}
 *       helperText={errors.cep?.message}
 *     />
 *   )}
 * />
 */
export const CepInput = forwardRef<HTMLInputElement, CepInputProps>(
  function CepInput(props, ref) {
    const { value, onChange, isLoading, onComplete, ...textFieldProps } = props;
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);

    const handleChange = useCallback(
      (event: React.ChangeEvent<HTMLInputElement>) => {
        const rawValue = event.target.value;
        const maskedValue = applyCepMask(rawValue);
        onChange(maskedValue);

        // Limpar timeout anterior
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }

        // Verificar se o CEP está completo (8 dígitos)
        const digits = maskedValue.replace(/\D/g, '');
        if (digits.length === 8 && onComplete) {
          // Debounce de 500ms antes de chamar onComplete
          timeoutRef.current = setTimeout(() => {
            onComplete(maskedValue);
            timeoutRef.current = null;
          }, 500);
        }
      },
      [onChange, onComplete]
    );

    const handleBlur = useCallback(
      (event: React.FocusEvent<HTMLInputElement>) => {
        // Trigger onComplete também no blur se completo
        const digits = (value || '').replace(/\D/g, '');
        if (digits.length === 8 && onComplete) {
          onComplete(value || '');
        }

        // Call original onBlur if provided
        if (textFieldProps.onBlur) {
          textFieldProps.onBlur(event);
        }
      },
      [value, onComplete, textFieldProps]
    );

    return (
      <TextField
        {...textFieldProps}
        value={value ?? ''}
        onChange={handleChange}
        onBlur={handleBlur}
        ref={ref}
        inputProps={{
          maxLength: 9, // 99999-999
          inputMode: 'numeric',
        }}
        placeholder="00000-000"
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                {isLoading ? (
                  <CircularProgress size={20} />
                ) : (
                  <SearchIcon color="action" />
                )}
              </InputAdornment>
            ),
          },
        }}
      />
    );
  }
);

export default CepInput;

