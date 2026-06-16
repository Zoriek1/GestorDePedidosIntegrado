/**
 * Etapa 3 (novo wizard) — Logística de entrega.
 * Mantém: CEP com auto-preenchimento (ViaCEP), busca reversa por endereço,
 * endereços salvos do cliente, quadra/lote, gerar endereço automático.
 * Acrescenta (do mockup): tipo de local (casa/prédio/comercial) + apto/bloco/torre/andar.
 */
import { useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { MapPin, Home, Building2, Store, Check, ChevronDown } from 'lucide-react';
import { Field, SectionHead, Divider } from '../components/atoms';
import { BuscaCepPorEndereco } from '../components/BuscaCepPorEndereco';
import { applyCepMask } from '../../schemas';
import { useCepLookup } from '../../useCases/cepLookup';
import { useClienteEnderecos } from '../../../../api/endpoints/customers';
import type { PedidoFormDataExt, TipoLocal } from '../types';

const TIPOS: { k: TipoLocal; label: string; icon: typeof Home }[] = [
  { k: 'casa', label: 'Casa', icon: Home },
  { k: 'predio', label: 'Prédio', icon: Building2 },
  { k: 'comercial', label: 'Comercial', icon: Store },
];

export function StepEntregaNovo() {
  const { control, register, setValue, getValues, formState: { errors } } = useFormContext<PedidoFormDataExt>();

  const cep = useWatch({ control, name: 'cep' }) ?? '';
  const cidade = useWatch({ control, name: 'cidade' }) ?? '';
  const tipoLocal = (useWatch({ control, name: 'tipo_local' }) ?? 'casa') as TipoLocal;
  const clienteId = useWatch({ control, name: 'cliente_id' });

  const { lookupCep } = useCepLookup();
  const { data: enderecosData } = useClienteEnderecos(clienteId);
  const enderecosSalvos = enderecosData?.enderecos ?? [];

  const [mais, setMais] = useState(false);

  const handleCepChange = async (raw: string) => {
    const masked = applyCepMask(raw);
    setValue('cep', masked, { shouldValidate: true });
    const digits = masked.replace(/\D/g, '');
    if (digits.length === 8) {
      const r = await lookupCep(masked);
      if (r) {
        if (r.rua) setValue('rua', r.rua, { shouldValidate: true });
        if (r.bairro) setValue('bairro', r.bairro, { shouldValidate: true });
        if (r.cidade) setValue('cidade', r.cidade, { shouldValidate: true });
      }
    }
  };

  const handleSelectEndereco = (id: number) => {
    const e = enderecosSalvos.find((x) => x.id === id);
    if (!e) return;
    const enderecoCompleto = e.endereco_completo || [e.rua, e.numero, e.bairro, e.cidade]
      .filter(Boolean)
      .join(', ');
    setValue('cep', e.cep, { shouldValidate: true });
    setValue('rua', e.rua, { shouldValidate: true });
    setValue('numero', e.numero, { shouldValidate: true });
    setValue('complemento', e.complemento, { shouldValidate: true });
    setValue('bairro', e.bairro, { shouldValidate: true });
    setValue('cidade', e.cidade, { shouldValidate: true });
    setValue('endereco', enderecoCompleto, { shouldValidate: true });
  };

  const handleTipoLocalChange = (tipo: TipoLocal) => {
    setValue('tipo_local', tipo, { shouldValidate: true });
    if (tipo === 'casa') {
      setValue('nome_local', '');
      setValue('apto', '');
      setValue('bloco', '');
      setValue('torre', '');
      setValue('andar', '');
    } else {
      setValue('quadra', '');
      setValue('lote', '');
    }
  };

  const gerarEndereco = () => {
    const v = getValues();
    const partes: string[] = [];
    if (v.rua) {
      const n = (v.numero || '').toUpperCase();
      if (v.numero && n !== '0' && n !== 'S/N' && n !== 'SN') partes.push(`${v.rua}, ${v.numero}`);
      else partes.push(v.rua);
    }
    if (v.tipo_local === 'casa' && v.quadra) partes.push(`Qd ${v.quadra}`);
    if (v.tipo_local === 'casa' && v.lote) partes.push(`Lt ${v.lote}`);
    if (v.bairro) partes.push(v.bairro);
    if (v.cidade) partes.push(v.cidade);
    if (v.cep) partes.push(`CEP: ${v.cep}`);

    const enderecoBase = partes.join(', ');
    const nomeLocal = v.nome_local?.trim();
    const apto = v.apto?.trim();
    let prefixoLocal = '';

    if (v.tipo_local === 'predio') {
      prefixoLocal = [nomeLocal || 'Prédio', apto ? `AP ${apto}` : null].filter(Boolean).join(' ');
    }
    if (v.tipo_local === 'comercial') {
      prefixoLocal = nomeLocal || 'Comércio';
    }

    setValue('endereco', [prefixoLocal, enderecoBase].filter(Boolean).join(' - '), { shouldValidate: true });
  };

  return (
    <>
      <SectionHead icon={MapPin} title="Logística de entrega" sub="Onde entregar e como encontrar o local." />

      <div className="pw-row2">
        <Field label="CEP" error={errors.cep?.message}>
          <input className={`pw-in${errors.cep ? ' err' : ''}`} value={cep} inputMode="numeric" maxLength={9}
            placeholder="00000-000" onChange={(e) => handleCepChange(e.target.value)} />
        </Field>
        <Field label="Rua / logradouro" req error={errors.rua?.message}>
          <input className="pw-in" {...register('rua')} placeholder="Preenchido pelo CEP ou manualmente" />
        </Field>
      </div>

      <BuscaCepPorEndereco
        cidadeAtual={cidade}
        onPick={(item) => {
          if (item.cep) setValue('cep', item.cep, { shouldValidate: true });
          if (item.logradouro) setValue('rua', item.logradouro, { shouldValidate: true });
          if (item.bairro) setValue('bairro', item.bairro, { shouldValidate: true });
          if (item.localidade) setValue('cidade', item.localidade, { shouldValidate: true });
        }}
      />

      <div className="pw-row3">
        <Field label="Número" req error={errors.numero?.message}>
          <input className="pw-in" {...register('numero')} />
        </Field>
        <Field label="Complemento" error={errors.complemento?.message}>
          <input className="pw-in" {...register('complemento')} placeholder="Apto, bloco…" />
        </Field>
        <Field label="Bairro" error={errors.bairro?.message}>
          <input className="pw-in" {...register('bairro')} />
        </Field>
      </div>

      <Field label="Cidade" req error={errors.cidade?.message}>
        <input className="pw-in" {...register('cidade')} />
      </Field>

      <Divider label="Tipo de local" />
      <div className="pw-seg">
        {TIPOS.map((t) => {
          const on = tipoLocal === t.k;
          const Ico = t.icon;
          return (
            <button type="button" key={t.k} className={`pw-seg-item ${on ? 'on' : ''}`}
              onClick={() => handleTipoLocalChange(t.k)}>
              {on && <span className="pw-seg-check"><Check size={12} /></span>}
              <span className="pw-seg-ic"><Ico size={20} /></span>{t.label}
            </button>
          );
        })}
      </div>

      {tipoLocal === 'comercial' && (
        <Field label="Nome do estabelecimento" req>
          <input className="pw-in" {...register('nome_local')} placeholder="Ex.: Colégio Planeta Vestibulares" />
        </Field>
      )}
      {tipoLocal === 'predio' && (
        <div className="pw-nest">
          <Field label="Nome do prédio / condomínio" req>
            <input className="pw-in" {...register('nome_local')} placeholder="Ex.: Edifício Jardim das Flores" />
          </Field>
          <div className="pw-row4">
            <Field label="Apartamento" req><input className="pw-in" {...register('apto')} /></Field>
            <Field label="Bloco"><input className="pw-in" {...register('bloco')} /></Field>
            <Field label="Torre"><input className="pw-in" {...register('torre')} /></Field>
            <Field label="Andar"><input className="pw-in" {...register('andar')} /></Field>
          </div>
        </div>
      )}

      <Field label="Ponto de referência" error={errors.obs_entrega?.message}>
        <input className="pw-in" {...register('obs_entrega')} placeholder="Portão azul, ao lado da farmácia…" />
      </Field>

      <Field label="Endereço completo" req hint="Gerado automaticamente ou preencha manualmente" error={errors.endereco?.message}>
        <textarea className={`pw-in ta sm${errors.endereco ? ' err' : ''}`} {...register('endereco')} />
      </Field>
      <button type="button" className="pw-btn ghost" onClick={gerarEndereco} style={{ marginBottom: 14 }}>
        Gerar endereço automático
      </button>

      <button type="button" className={`pw-disc ${mais ? 'open' : ''}`} onClick={() => setMais((v) => !v)}>
        <ChevronDown size={16} /> Mais opções da entrega
      </button>
      {mais && (
        <div className="pw-disc-body">
          {enderecosSalvos.length > 0 && (
            <Field label="Endereços salvos do cliente" hint="Selecione para preencher automaticamente">
              <select className="pw-in" defaultValue="" onChange={(e) => e.target.value && handleSelectEndereco(Number(e.target.value))}>
                <option value="">Selecione um endereço salvo</option>
                {enderecosSalvos.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.apelido ? `${e.apelido} — ` : ''}{e.endereco_completo || `${e.rua}, ${e.numero} - ${e.bairro}`}
                  </option>
                ))}
              </select>
            </Field>
          )}
          {tipoLocal === 'casa' && (
            <div className="pw-row2">
              <Field label="Quadra"><input className="pw-in" {...register('quadra')} placeholder="Ex.: 5" /></Field>
              <Field label="Lote"><input className="pw-in" {...register('lote')} placeholder="Ex.: 12" /></Field>
            </div>
          )}
        </div>
      )}
    </>
  );
}

export default StepEntregaNovo;
