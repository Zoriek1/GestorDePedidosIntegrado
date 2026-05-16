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
 * - BR fixo (10 dígitos): (XX) XXXX-XXXX
 * - BR celular (11 dígitos): (XX) XXXXX-XXXX
 * - Internacional (prefixo + ou >11 dígitos): mantém + e dígitos sem máscara BR
 */
function applyPhoneMask(value: string): string {
  const trimmed = value.trim();
  const hasPlus = trimmed.startsWith('+');
  const digits = trimmed.replace(/\D/g, '');

  // Internacional: usuário digitou "+" ou já passou de 11 dígitos
  if (hasPlus || digits.length > 11) {
    const limited = digits.slice(0, 15); // E.164 máximo
    return limited ? `+${limited}` : '+';
  }

  const limited = digits.slice(0, 11);
  if (limited.length === 0) return '';
  if (limited.length <= 2) return `(${limited}`;
  if (limited.length <= 6) return `(${limited.slice(0, 2)}) ${limited.slice(2)}`;
  if (limited.length <= 10) {
    return `(${limited.slice(0, 2)}) ${limited.slice(2, 6)}-${limited.slice(6)}`;
  }
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
          maxLength: 20, // suporta internacional (+, código país, etc.)
        }}
        placeholder="(00) 00000-0000 ou +código"
      />
    );
  }
);

export default PhoneInput;

