/**
 * Etapa 4 (novo wizard) — Pagamento e finalização.
 * Mantém: forma/parcelas (crédito)/status, observações, cálculo de líquido real e
 * regra "Pago exige forma de pagamento". ResumoVivo inline no mobile; barra de total no desktop.
 */
import { useEffect } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { CreditCard, AlertTriangle } from 'lucide-react';
import { Field, SectionHead } from '../components/atoms';
import { ResumoVivo } from '../components/ResumoVivo';
import { useValorLiquido } from '../components/useValorLiquido';
import { FORMAS_PAGAMENTO, STATUS_PAGAMENTO, formatCurrency } from '../../schemas';
import { useTaxaCartaoConfig } from '../../../config/hooks/useConfig';
import type { PedidoFormDataExt } from '../types';

export function StepPagamentoNovo({ isMobile }: { isMobile: boolean }) {
  const { control, register, setValue, formState: { errors } } = useFormContext<PedidoFormDataExt>();

  const mensagem = useWatch({ control, name: 'mensagem' }) ?? '';
  const pagamento = useWatch({ control, name: 'pagamento' }) ?? '';
  const statusPagamento = useWatch({ control, name: 'status_pagamento' });
  const parcelas = useWatch({ control, name: 'parcelas_cartao' });

  const { config } = useTaxaCartaoConfig();
  const isCredito = pagamento === 'Cartão de Crédito';
  const opcoesParcelas = (config?.credito ?? [])
    .map((f) => Number(f.parcelas))
    .filter((n) => Number.isFinite(n) && n >= 1)
    .sort((a, b) => a - b);

  useEffect(() => {
    if (!isCredito && parcelas !== undefined) setValue('parcelas_cartao', undefined, { shouldDirty: true });
    else if (isCredito && !parcelas && opcoesParcelas.length > 0) setValue('parcelas_cartao', opcoesParcelas[0], { shouldDirty: true });
  }, [isCredito, parcelas, opcoesParcelas, setValue]);

  const invalido = statusPagamento === 'Pago' && !pagamento;
  const { liquido } = useValorLiquido();

  return (
    <>
      <SectionHead icon={CreditCard} title="Pagamento e finalização" sub="Informe os dados de pagamento e revise o resumo." />

      <Field label="Carta / mensagem" hint={`${mensagem.length}/1000 caracteres`} error={errors.mensagem?.message}>
        <textarea className="pw-in ta" maxLength={1000} {...register('mensagem')} />
      </Field>

      <div className="pw-row2">
        <Field label="Forma de pagamento" req={statusPagamento === 'Pago'} error={errors.pagamento?.message}>
          <select className={`pw-in${invalido ? ' err' : ''}`} value={pagamento}
            onChange={(e) => setValue('pagamento', e.target.value, { shouldValidate: true })}>
            <option value="">Selecione</option>
            {FORMAS_PAGAMENTO.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </Field>
        <Field label="Status do pagamento" req error={errors.status_pagamento?.message}>
          <select className="pw-in" value={statusPagamento}
            onChange={(e) => setValue('status_pagamento', e.target.value as typeof STATUS_PAGAMENTO[number], { shouldValidate: true })}>
            {STATUS_PAGAMENTO.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
      </div>

      {isCredito && (
        <Field label="Parcelas" hint="A taxa varia conforme o número de parcelas" error={errors.parcelas_cartao?.message}>
          <select className="pw-in" value={parcelas ?? ''}
            onChange={(e) => setValue('parcelas_cartao', e.target.value ? Number(e.target.value) : undefined, { shouldValidate: true })}>
            {opcoesParcelas.length === 0 && <option value="">Configure as taxas em Configurações</option>}
            {opcoesParcelas.map((n) => <option key={n} value={n}>{n}x</option>)}
          </select>
        </Field>
      )}

      {invalido && (
        <div className="pw-warn"><AlertTriangle size={16} /> Status "Pago" exige uma forma de pagamento antes de concluir.</div>
      )}

      <Field label="Observações gerais" error={errors.observacoes?.message}>
        <textarea className="pw-in ta sm" {...register('observacoes')} />
      </Field>

      {isMobile ? (
        <div className="pw-inline-card"><ResumoVivo /></div>
      ) : (
        <div className="pw-totalbar"><span>Valor líquido</span><strong>{formatCurrency(liquido)}</strong></div>
      )}
    </>
  );
}

export default StepPagamentoNovo;
