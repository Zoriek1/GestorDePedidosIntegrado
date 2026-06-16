/**
 * Cálculo do valor líquido em tempo real (produto − taxa de entrega − taxa de cartão).
 * Espelha a lógica do StepPagamento original; usado pelo ResumoVivo e pela barra de total.
 */
import { useFormContext, useWatch } from 'react-hook-form';
import { parseCurrencyToFloat } from '../../schemas';
import { useTaxaCartaoConfig } from '../../../config/hooks/useConfig';
import { calcularTaxaCartao } from '../../../config/services/configService';
import type { PedidoFormDataExt } from '../types';

export function useValorLiquido() {
  const { control } = useFormContext<PedidoFormDataExt>();
  const valor = useWatch({ control, name: 'valor' });
  const taxaEntrega = useWatch({ control, name: 'taxa_entrega' });
  const tipoPedido = useWatch({ control, name: 'tipo_pedido' });
  const pagamento = useWatch({ control, name: 'pagamento' });
  const parcelas = useWatch({ control, name: 'parcelas_cartao' });

  const { config } = useTaxaCartaoConfig();

  const valorFloat = parseCurrencyToFloat(valor) || 0;
  const taxaFloat = tipoPedido === 'Entrega' ? parseCurrencyToFloat(taxaEntrega) || 0 : 0;
  const taxaCartaoFloat = calcularTaxaCartao(config, pagamento, parcelas, valorFloat);
  const liquido = Math.max(0, valorFloat - taxaFloat - taxaCartaoFloat);

  return { valorFloat, taxaFloat, taxaCartaoFloat, liquido };
}
