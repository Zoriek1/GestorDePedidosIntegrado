/**
 * PhoneInput - Input de Telefone com Máscara Dinâmica
 * Suporta formato (XX) XXXX-XXXX e (XX) XXXXX-XXXX
 * Integração com MUI TextField e react-hook-form
 */

import { forwardRef, useCallback } from 'react';
import TextField, { TextFieldProps } from '@mui/material/TextField';

interface PhoneInputProps extends Omit<TextFieldProps, 'onChange' | 'value'> {
  value: string | undefined;
  onChange: (value: string) => void;
}

/**
 * Aplica máscara dinâmica ao telefone
 * - 10 dígitos: (XX) XXXX-XXXX
 * - 11 dígitos: (XX) XXXXX-XXXX
 */
function applyPhoneMask(value: string): string {
  // Remove tudo que não é dígito
  const digits = value.replace(/\D/g, '');
  
  // Limita a 11 dígitos
  const limited = digits.slice(0, 11);
  
  if (limited.length === 0) return '';
  if (limited.length <= 2) return `(${limited}`;
  if (limited.length <= 6) return `(${limited.slice(0, 2)}) ${limited.slice(2)}`;
  
  // Telefone fixo (10 dígitos)
  if (limited.length <= 10) {
    return `(${limited.slice(0, 2)}) ${limited.slice(2, 6)}-${limited.slice(6)}`;
  }
  
  // Celular (11 dígitos)
  return `(${limited.slice(0, 2)}) ${limited.slice(2, 7)}-${limited.slice(7)}`;
}

/**
 * Campo de entrada para telefone brasileiro
 * Aplica máscara automática conforme digitação
 * 
 * @example
 * <Controller
 *   name="telefone_cliente"
 *   control={control}
 *   render={({ field }) => (
 *     <PhoneInput
 *       {...field}
 *       label="Telefone/WhatsApp"
 *       error={!!errors.telefone_cliente}
 *       helperText={errors.telefone_cliente?.message}
 *     />
 *   )}
 * />
 */
export const PhoneInput = forwardRef<HTMLInputElement, PhoneInputProps>(
  function PhoneInput(props, ref) {
    const { value, onChange, ...textFieldProps } = props;

    const handleChange = useCallback(
      (event: React.ChangeEvent<HTMLInputElement>) => {
        const maskedValue = applyPhoneMask(event.target.value);
        onChange(maskedValue);
      },
      [onChange]
    );

    return (
      <TextField
        {...textFieldProps}
        value={value ?? ''}
        onChange={handleChange}
        ref={ref}
        type="tel"
        inputProps={{
          maxLength: 16, // (XX) XXXXX-XXXX = 15 chars + margem
        }}
        placeholder="(00) 00000-0000"
      />
    );
  }
);

export default PhoneInput;

