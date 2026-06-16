/** Cartão de entrega — "visão do entregador" (gift tag). Lê o form em tempo real. */
import { useFormContext, useWatch } from 'react-hook-form';
import { Home, Building2, Store, Printer, MapPin, Clock, Phone } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { PedidoFormDataExt, TipoLocal } from '../types';

const META: Record<TipoLocal, { label: string; icon: LucideIcon }> = {
  casa: { label: 'Casa', icon: Home },
  predio: { label: 'Prédio', icon: Building2 },
  comercial: { label: 'Comercial', icon: Store },
};

export function CartaoEntrega() {
  const { control } = useFormContext<PedidoFormDataExt>();
  const destinatario = useWatch({ control, name: 'destinatario' });
  const rua = useWatch({ control, name: 'rua' });
  const numero = useWatch({ control, name: 'numero' });
  const complemento = useWatch({ control, name: 'complemento' });
  const bairro = useWatch({ control, name: 'bairro' });
  const cidade = useWatch({ control, name: 'cidade' });
  const referencia = useWatch({ control, name: 'obs_entrega' });
  const horario = useWatch({ control, name: 'horario' });
  const telefone = useWatch({ control, name: 'telefone_cliente' });
  const tipoLocal = (useWatch({ control, name: 'tipo_local' }) ?? 'casa') as TipoLocal;
  const nomeLocal = useWatch({ control, name: 'nome_local' });
  const apto = useWatch({ control, name: 'apto' });
  const bloco = useWatch({ control, name: 'bloco' });
  const torre = useWatch({ control, name: 'torre' });
  const andar = useWatch({ control, name: 'andar' });

  const meta = META[tipoLocal] ?? META.casa;
  const Ico = meta.icon;
  const det = [
    apto && `AP ${apto}`,
    bloco && `Bloco ${bloco}`,
    torre && `Torre ${torre}`,
    andar && `${andar}º andar`,
  ].filter(Boolean).join(' · ');

  return (
    <div className="pw-deliv">
      <span className="pw-deliv-ribbon" />
      <div className="pw-deliv-top">
        <span className="pw-deliv-tag"><Printer size={12} /> Visão do entregador</span>
        <span className="pw-deliv-type"><Ico size={12} /> {meta.label}</span>
      </div>
      <div className="pw-deliv-to">{destinatario || '—'}</div>
      <div className="pw-deliv-addr">
        {rua || '—'}{numero ? `, ${numero}` : ''}{complemento ? ` — ${complemento}` : ''}
        <br />{bairro}{bairro && cidade ? ' · ' : ''}{cidade}
      </div>
      {nomeLocal && tipoLocal !== 'casa' && (
        <div className="pw-deliv-local"><Ico size={14} /> {nomeLocal}</div>
      )}
      {det && <div className="pw-deliv-det">{det}</div>}
      {referencia && (<div className="pw-deliv-ref"><MapPin size={13} /> {referencia}</div>)}
      <div className="pw-deliv-foot">
        <span><Clock size={13} /> {horario || '—'}</span>
        <span><Phone size={13} /> {telefone || '—'}</span>
      </div>
    </div>
  );
}
