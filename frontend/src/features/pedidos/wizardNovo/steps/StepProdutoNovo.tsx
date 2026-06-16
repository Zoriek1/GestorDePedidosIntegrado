/**
 * Etapa 2 (novo wizard) — Produto e agendamento.
 * Mantém: sugestões do catálogo + "Adicionar ao catálogo", máscara de valor,
 * data com aviso de feriado de floricultura e seleção de horário via TimeSlotDialog.
 */
import { useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { Flower2, Clock } from 'lucide-react';
import dayjs from 'dayjs';
import { Field, SectionHead, Divider } from '../components/atoms';
import { PwCurrencyInput } from '../components/inputs';
import { useDebouncedValue } from '../../../../hooks/useDebouncedValue';
import { useArranjoSugestoes, usePromoverArranjo } from '../../services/catalogoApi';
import { useToast } from '../../../../components/system/useToast';
import { getFloristHoliday, getUpcomingHolidays } from '../../utils/floristHolidays';
import { TimeSlotDialog } from '../../components/TimeSlotDialog';
import type { PedidoFormDataExt } from '../types';

export function StepProdutoNovo() {
  const { control, register, setValue, formState: { errors } } = useFormContext<PedidoFormDataExt>();

  const produto = useWatch({ control, name: 'produto' }) ?? '';
  const valor = useWatch({ control, name: 'valor' });
  const dia = useWatch({ control, name: 'dia_entrega' }) ?? '';
  const horario = useWatch({ control, name: 'horario' }) ?? '';

  // ---- Catálogo ----
  const [showCat, setShowCat] = useState(false);
  const produtoDebounced = useDebouncedValue(produto.trim(), 300);
  const { data: sugestoes = [] } = useArranjoSugestoes(produtoDebounced, produtoDebounced.length >= 2);
  const promover = usePromoverArranjo();
  const toast = useToast();
  const jaNoCatalogo = sugestoes.some((s) => s.toLowerCase() === produto.trim().toLowerCase());

  // ---- Feriados ----
  const selectedHoliday = dia ? getFloristHoliday(dayjs(dia)) : null;
  const upcoming = getUpcomingHolidays(dayjs(), 90).slice(0, 3);

  // ---- Horário ----
  const [showTime, setShowTime] = useState(false);
  const hoje = dayjs().format('YYYY-MM-DD');

  return (
    <>
      <SectionHead icon={Flower2} title="Produto e agendamento" sub="Descreva o produto e informe quando será entregue." />

      <div className="pw-ac" onBlur={() => setTimeout(() => setShowCat(false), 120)}>
        <Field label="Descrição do produto" req
          hint="Sugestões do catálogo aparecem ao digitar; nome novo é sempre aceito"
          error={errors.produto?.message}>
          <input
            className={`pw-in${errors.produto ? ' err' : ''}`}
            value={produto}
            onChange={(e) => { setValue('produto', e.target.value, { shouldValidate: true }); setShowCat(true); }}
            onFocus={() => setShowCat(true)}
            placeholder="Ex.: Buquê de 12 rosas vermelhas com folhagens"
            autoComplete="off"
          />
        </Field>
        {showCat && produtoDebounced.length >= 2 && sugestoes.length > 0 && (
          <ul className="pw-ac-list">
            {sugestoes.map((s) => (
              <li key={s} onMouseDown={(e) => { e.preventDefault(); setValue('produto', s, { shouldValidate: true }); setShowCat(false); }}>
                <b>{s}</b>
              </li>
            ))}
          </ul>
        )}
      </div>

      {produto.trim().length >= 2 && !jaNoCatalogo && (
        <button type="button" className="pw-add-cat" disabled={promover.isPending}
          onClick={async () => {
            const nome = produto.trim();
            try { await promover.mutateAsync(nome); toast.success(`"${nome}" adicionado ao catálogo`); }
            catch (e) { toast.error(e instanceof Error ? e.message : 'Erro ao adicionar ao catálogo'); }
          }}>
          <span>+</span> Adicionar "{produto.trim()}" ao catálogo
        </button>
      )}

      <div className="pw-row2">
        <Field label="Flores e cores (detalhamento)" error={errors.flores_cor?.message}>
          <input className="pw-in" {...register('flores_cor')} placeholder="Ex.: Rosas vermelhas, astromélias brancas" />
        </Field>
        <Field label="Valor total (R$)" req error={errors.valor?.message}>
          <PwCurrencyInput value={valor} onChange={(v) => setValue('valor', v, { shouldValidate: true })} />
        </Field>
      </div>

      <Divider label="Agendamento" />

      <div className="pw-row2">
        <Field label="Data de entrega" req error={errors.dia_entrega?.message}>
          <input type="date" className={`pw-in${errors.dia_entrega ? ' err' : ''}`} value={dia} min={hoje}
            onChange={(e) => setValue('dia_entrega', e.target.value, { shouldValidate: true })} />
        </Field>
        <Field label="Janela de horário" req error={errors.horario?.message}>
          <button type="button" className={`pw-in${errors.horario ? ' err' : ''}`} disabled={!dia}
            onClick={() => setShowTime(true)}>
            <span>{horario ? horario : 'Selecionar horário'}</span>
            <Clock size={16} />
          </button>
        </Field>
      </div>

      {selectedHoliday ? (
        <div className="pw-holiday" style={{ color: selectedHoliday.color, background: `${selectedHoliday.color}1f` }}>
          <Flower2 size={13} /> {selectedHoliday.name}{selectedHoliday.tier === 'peak' && ' — pico de demanda'}
        </div>
      ) : upcoming.length > 0 ? (
        <div className="pw-holiday-soft">
          <span>Próximas datas:</span>
          {upcoming.map((u) => (
            <span key={u.date.format('YYYY-MM-DD')} className="pw-holiday-pill"
              style={{ color: u.holiday.color, background: `${u.holiday.color}1f` }}>
              {u.holiday.name} ({u.date.format('DD/MM')})
            </span>
          ))}
        </div>
      ) : null}

      <TimeSlotDialog
        open={showTime}
        onClose={() => setShowTime(false)}
        date={dia || hoje}
        currentSlot={horario}
        onSelectSlot={(slot) => { setValue('horario', slot, { shouldValidate: true }); setShowTime(false); }}
      />
    </>
  );
}

export default StepProdutoNovo;
