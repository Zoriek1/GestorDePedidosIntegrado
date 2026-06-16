/**
 * Inputs nativos com máscara (telefone, moeda) estilizados com a classe `.pw-in`.
 * Reaproveitam a mesma lógica dos componentes MUI existentes (PhoneInput/CurrencyInput),
 * porém renderizando <input> nativo para o visual do mockup.
 */
import { forwardRef, useCallback, useMemo } from 'react';
import { NumericFormat } from 'react-number-format';

/** Máscara dinâmica de telefone BR (idêntica ao PhoneInput de components/form). */
function applyPhoneMask(value: string): string {
  const trimmed = value.trim();
  const hasPlus = trimmed.startsWith('+');
  const digits = trimmed.replace(/\D/g, '');
  if (hasPlus || digits.length > 11) {
    const limited = digits.slice(0, 15);
    return limited ? `+${limited}` : '+';
  }
  const limited = digits.slice(0, 11);
  if (limited.length === 0) return '';
  if (limited.length <= 2) return `(${limited}`;
  if (limited.length <= 6) return `(${limited.slice(0, 2)}) ${limited.slice(2)}`;
  if (limited.length <= 10) return `(${limited.slice(0, 2)}) ${limited.slice(2, 6)}-${limited.slice(6)}`;
  return `(${limited.slice(0, 2)}) ${limited.slice(2, 7)}-${limited.slice(7)}`;
}

interface PwPhoneProps {
  value: string | undefined;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
  onBlur?: () => void;
}

export const PwPhoneInput = forwardRef<HTMLInputElement, PwPhoneProps>(function PwPhoneInput(
  { value, onChange, disabled, className, placeholder = '(00) 00000-0000 ou +código', onBlur }, ref,
) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => onChange(applyPhoneMask(e.target.value)),
    [onChange],
  );
  return (
    <input
      ref={ref}
      type="tel"
      className={`pw-in${disabled ? ' dim' : ''}${className ? ` ${className}` : ''}`}
      value={value ?? ''}
      onChange={handleChange}
      onBlur={onBlur}
      disabled={disabled}
      maxLength={20}
      placeholder={placeholder}
    />
  );
});

/** Converte "R$ 1.000,00" → "1000.00" para alimentar o NumericFormat. */
function parseFormattedToNumeric(value: string | number | undefined): string {
  if (value === undefined || value === null || value === '') return '';
  if (typeof value === 'number') return value.toString();
  const cleaned = value.replace(/R\$\s*/g, '').trim();
  if (!cleaned) return '';
  if (cleaned.includes(',')) return cleaned.replace(/\./g, '').replace(',', '.');
  return cleaned.replace(/\./g, '');
}

interface PwCurrencyProps {
  value: string | undefined;
  onChange: (value: string) => void;
  className?: string;
  placeholder?: string;
}

export function PwCurrencyInput({ value, onChange, className, placeholder = 'R$ 0,00' }: PwCurrencyProps) {
  const numericValue = useMemo(() => parseFormattedToNumeric(value), [value]);
  return (
    <NumericFormat
      className={`pw-in${className ? ` ${className}` : ''}`}
      value={numericValue}
      onValueChange={(values) => onChange(values.formattedValue)}
      thousandSeparator="."
      decimalSeparator=","
      prefix="R$ "
      decimalScale={2}
      fixedDecimalScale
      allowNegative={false}
      valueIsNumericString
      placeholder={placeholder}
      inputMode="decimal"
    />
  );
}
