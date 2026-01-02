/**
 * CurrencyInput - Input de Moeda (BRL)
 * Integração com react-number-format e MUI TextField
 * Compatível com react-hook-form via Controller
 */

import { forwardRef } from 'react';
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
}

const NumericFormatCustom = forwardRef<NumericFormatProps, CustomNumericFormatProps>(
  function NumericFormatCustom(props, ref) {
    const { onChange, prefix = 'R$ ', allowNegative = false, ...other } = props;

    return (
      <NumericFormat
        {...other}
        getInputRef={ref}
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

    return (
      <TextField
        {...textFieldProps}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        ref={ref}
        slotProps={{
          input: {
            inputComponent: NumericFormatCustom as never,
            inputProps: {
              prefix,
              allowNegative,
            },
          },
        }}
      />
    );
  }
);

export default CurrencyInput;

