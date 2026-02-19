/**
 * CurrencyInput - Input de Moeda (BRL)
 * Integração com react-number-format e MUI TextField
 * Compatível com react-hook-form via Controller
 */

import { forwardRef, useMemo } from 'react';
import { NumericFormat, NumericFormatProps } from 'react-number-format';
import TextField, { TextFieldProps } from '@mui/material/TextField';

interface CurrencyInputProps extends Omit<TextFieldProps, 'onChange' | 'value'> {
  value: string | number | undefined;
  onChange: (value: string) => void;
  /** Prefixo monetário (default: "R$ ") */
  prefix?: string;
  /** Se true, permite valores negativos */
  allowNegative?: boolean;
}

interface CustomNumericFormatProps {
  onChange: (event: { target: { name: string; value: string } }) => void;
  name: string;
  prefix?: string;
  allowNegative?: boolean;
  numericValue?: string;
}

/**
 * Converte valor formatado (R$ 1.000,00) para numérico (1000.00)
 */
function parseFormattedToNumeric(value: string | number | undefined): string {
  if (!value) return '';
  if (typeof value === 'number') return value.toString();
  
  // Remove prefixo R$ e espaços
  const cleaned = value.replace(/R\$\s*/g, '').trim();
  if (!cleaned) return '';
  
  // Se tem vírgula, tratar como formato BR (1.000,00)
  if (cleaned.includes(',')) {
    // Remove pontos (separadores de milhar) e substitui vírgula por ponto
    const normalized = cleaned.replace(/\./g, '').replace(',', '.');
    return normalized;
  }
  
  // Se não tem vírgula, pode ser número puro ou formato incorreto
  // Remove pontos e trata como número inteiro
  return cleaned.replace(/\./g, '');
}

const NumericFormatCustom = forwardRef<NumericFormatProps, CustomNumericFormatProps>(
  function NumericFormatCustom(props, ref) {
    const { onChange, prefix = 'R$ ', allowNegative = false, numericValue, ...other } = props;

    return (
      <NumericFormat
        {...other}
        getInputRef={ref}
        value={numericValue}
        onValueChange={(values) => {
          onChange({
            target: {
              name: props.name,
              value: values.formattedValue,
            },
          });
        }}
        thousandSeparator="."
        decimalSeparator=","
        prefix={prefix}
        decimalScale={2}
        fixedDecimalScale
        allowNegative={allowNegative}
        valueIsNumericString
      />
    );
  }
);

/**
 * Campo de entrada para valores monetários em BRL
 * Formata automaticamente com separadores de milhar e decimal
 * 
 * @example
 * <Controller
 *   name="valor"
 *   control={control}
 *   render={({ field }) => (
 *     <CurrencyInput
 *       {...field}
 *       label="Valor do Produto"
 *       error={!!errors.valor}
 *       helperText={errors.valor?.message}
 *     />
 *   )}
 * />
 */
export const CurrencyInput = forwardRef<HTMLInputElement, CurrencyInputProps>(
  function CurrencyInput(props, ref) {
    const {
      value,
      onChange,
      prefix = 'R$ ',
      allowNegative = false,
      ...textFieldProps
    } = props;

    // Converte o valor formatado para numérico para o NumericFormat
    const numericValue = useMemo(() => {
      return parseFormattedToNumeric(value);
    }, [value]);

    return (
      <TextField
        {...textFieldProps}
        value={value ?? ''}
        onChange={onChange}
        ref={ref}
        slotProps={{
          input: {
            inputComponent: NumericFormatCustom as never,
            inputProps: {
              prefix,
              allowNegative,
              numericValue,
            },
          },
        }}
      />
    );
  }
);

export default CurrencyInput;

