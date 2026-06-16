/** Resumo vivo do pedido (sidebar sticky / inline no mobile). */
import { useFormContext, useWatch } from 'react-hook-form';
import { Printer } from 'lucide-react';
import { formatCurrency } from '../../schemas';
import type { PedidoFormDataExt } from '../types';
import { useValorLiquido } from './useValorLiquido';

export function ResumoVivo() {
  const { control } = useFormContext<PedidoFormDataExt>();
  const cliente = useWatch({ control, name: 'cliente' });
  const destinatario = useWatch({ control, name: 'destinatario' });
  const tipoPedido = useWatch({ control, name: 'tipo_pedido' });
  const produto = useWatch({ control, name: 'produto' });
  const dia = useWatch({ control, name: 'dia_entrega' }) || '';
  const horario = useWatch({ control, name: 'horario' });
  const { valorFloat, taxaFloat, liquido } = useValorLiquido();

  const dataBR = dia ? dia.split('-').reverse().join('/') : '—';
  const produtoCurto = produto ? (produto.length > 42 ? `${produto.slice(0, 42)}…` : produto) : '—';
  const rows: [string, string][] = [
    ['Cliente', cliente || '—'],
    ['Destinatário', destinatario || '—'],
    ['Tipo', tipoPedido],
    ['Produto', produtoCurto],
    ['Data / hora', `${dataBR}${horario ? ` · ${horario}` : ''}`],
  ];

  return (
    <div className="pw-sum-card">
      <div className="pw-sum-head"><Printer size={15} /> Resumo do pedido</div>
      {rows.map(([k, v]) => (
        <div className="pw-sum-row" key={k}><span>{k}</span><b>{v}</b></div>
      ))}
      <div className="pw-sum-money">
        <div><span>Produto</span><b>{valorFloat > 0 ? formatCurrency(valorFloat) : '—'}</b></div>
        {tipoPedido === 'Entrega' && (
          <div><span>Taxa de entrega</span><b>{taxaFloat > 0 ? `− ${formatCurrency(taxaFloat)}` : 'Grátis'}</b></div>
        )}
        <div className="liq"><span>Líquido</span><b>{formatCurrency(liquido)}</b></div>
      </div>
    </div>
  );
}
