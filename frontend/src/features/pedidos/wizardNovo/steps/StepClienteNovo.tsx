/**
 * Etapa 1 (novo wizard) — Dados do cliente.
 * Porta o visual do mockup mantendo: autocomplete de cliente, chip "cliente existente",
 * lead por código do WhatsApp, vendedor (admin), fonte bloqueada e origem de anúncio.
 */
import { useEffect, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { User, Check, ChevronDown, Megaphone, Lock } from 'lucide-react';
import { Field, SectionHead } from '../components/atoms';
import { PwPhoneInput } from '../components/inputs';
import { useDebouncedValue } from '../../../../hooks/useDebouncedValue';
import { useCustomerSearch, type Customer } from '../../../../api/endpoints/customers';
import { useFontesPedido } from '../../../../api/endpoints/fontes';
import { useLeads } from '../../../../api/endpoints/leads';
import { useUsers } from '../../../users/services/userApi';
import { useAuth } from '../../../auth/authStore';
import { formatCpfCnpj } from '../../schemas';
import type { PedidoFormDataExt } from '../types';

export function StepClienteNovo() {
  const { control, register, setValue, formState: { errors } } = useFormContext<PedidoFormDataExt>();

  const { getUserRole } = useAuth();
  const isAdmin = getUserRole() === 'admin';
  const { data: usersData } = useUsers(isAdmin);
  const vendedores = (usersData ?? []).filter((u) => u.role === 'vendedor' && u.is_active);

  const cliente = useWatch({ control, name: 'cliente' }) ?? '';
  const clienteId = useWatch({ control, name: 'cliente_id' });
  const cpfCnpj = useWatch({ control, name: 'cpf_cnpj' }) ?? '';
  const tipoPedido = useWatch({ control, name: 'tipo_pedido' });
  const fonteId = useWatch({ control, name: 'fonte_pedido_id' });
  const codigoWhatsapp = useWatch({ control, name: 'codigo_whatsapp' }) ?? '';
  const origemAnuncio = useWatch({ control, name: 'origem_anuncio' });
  const vendedorId = useWatch({ control, name: 'vendedor_id' });

  const hasSelectedCustomer = typeof clienteId === 'number';
  const fonteLocked = typeof fonteId === 'number';

  // ---- Autocomplete de cliente ----
  const [showList, setShowList] = useState(false);
  const debounced = useDebouncedValue(cliente.trim(), 300);
  const { data: searchData, isFetching } = useCustomerSearch(debounced.length >= 3 ? debounced : '', 10);
  const customers = searchData?.clientes ?? [];

  const handleClienteChange = (val: string) => {
    setValue('cliente', val, { shouldValidate: true });
    if (hasSelectedCustomer) {
      setValue('cliente_id', undefined);
      setValue('cliente_modo', 'novo', { shouldValidate: true });
    }
    setShowList(true);
  };

  const handleSelectCustomer = (c: Customer) => {
    setValue('cliente', c.nome, { shouldValidate: true });
    setValue('telefone_cliente', c.telefone || '', { shouldValidate: true });
    setValue('cpf_cnpj', formatCpfCnpj(c.cpf_cnpj || ''), { shouldValidate: true });
    setValue('cliente_id', c.id);
    setValue('cliente_modo', 'busca', { shouldValidate: true });
    setShowList(false);
  };

  const handleCadastrarNovo = () => {
    setValue('cliente', '', { shouldValidate: true });
    setValue('telefone_cliente', '', { shouldValidate: true });
    setValue('cpf_cnpj', '', { shouldValidate: true });
    setValue('cliente_id', undefined);
    setValue('cliente_modo', 'novo', { shouldValidate: true });
    setMesmo(false);
  };

  // ---- Destinatário é o próprio cliente ----
  const [mesmo, setMesmo] = useState(false);
  useEffect(() => {
    if (mesmo && cliente) setValue('destinatario', cliente, { shouldValidate: true });
  }, [mesmo, cliente, setValue]);

  // ---- Lead por código do WhatsApp ----
  const tokenLookup = useDebouncedValue(codigoWhatsapp.trim().toUpperCase(), 400);
  const tokenLooksValid = /^[A-Z0-9]{10}$/.test(tokenLookup);
  const { data: leadLookup } = useLeads({ token_rastreio: tokenLookup }, { enabled: tokenLooksValid });
  const foundLead = tokenLooksValid ? (leadLookup?.leads?.find((l) => l.token_rastreio) ?? null) : null;
  useEffect(() => {
    if (!foundLead) return;
    if (foundLead.fbp) setValue('fbp', foundLead.fbp);
    if (foundLead.fbclid) {
      setValue('fbclid', foundLead.fbclid);
      setValue('origem_anuncio', true);
    }
  }, [foundLead, setValue]);

  // ---- Fonte ----
  const { data: fontesData } = useFontesPedido(true);
  const fonteNome = fontesData?.fontes?.find((f) => f.id === fonteId)?.nome;

  // ---- Disclosure "Mais opções" ----
  // Abre automaticamente quando já há dados nessa área (sem effect: derivado do estado atual).
  const [maisOpen, setMaisOpen] = useState(false);
  const mais = maisOpen || !!codigoWhatsapp || !!origemAnuncio || typeof vendedorId === 'number';

  return (
    <>
      <SectionHead icon={User} title="Dados do cliente"
        sub="Digite o nome ou telefone para buscar um cliente, ou preencha para criar um novo." />

      <div className="pw-ac" onBlur={() => setTimeout(() => setShowList(false), 120)}>
        <Field label="Nome do cliente" req error={errors.cliente?.message}>
          <input
            className={`pw-in${errors.cliente ? ' err' : ''}`}
            value={cliente}
            onChange={(e) => handleClienteChange(e.target.value)}
            onFocus={() => setShowList(true)}
            placeholder="Digite para buscar ou criar…"
            autoComplete="off"
          />
        </Field>
        {showList && !hasSelectedCustomer && (debounced.length >= 3) && (
          <ul className="pw-ac-list">
            {isFetching && <li className="pw-ac-empty">Buscando…</li>}
            {!isFetching && customers.length === 0 && (
              <li className="pw-ac-empty">Nenhum cliente encontrado. Continue digitando para criar novo.</li>
            )}
            {customers.map((c) => (
              <li key={c.id} onMouseDown={(e) => { e.preventDefault(); handleSelectCustomer(c); }}>
                <b>{c.nome}</b><span>{c.telefone}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {hasSelectedCustomer && (
        <div className="pw-chip-found">
          <span><span className="pw-chip-ic"><User size={14} /></span> Cliente existente · ID {clienteId}</span>
          <button type="button" className="pw-link sm" onClick={handleCadastrarNovo}>Cadastrar novo</button>
        </div>
      )}

      <Field label="Telefone / WhatsApp" req
        hint={hasSelectedCustomer ? 'Telefone do cliente selecionado' : 'Formato: (00) 00000-0000'}
        error={errors.telefone_cliente?.message}>
        <PwPhoneInputController disabled={hasSelectedCustomer} />
      </Field>

      <Field label="CPF/CNPJ" hint="Opcional; necessário para remover a pendência fiscal no Bling"
        error={errors.cpf_cnpj?.message}>
        <input
          className={`pw-in${errors.cpf_cnpj ? ' err' : ''}`}
          value={cpfCnpj}
          inputMode="numeric"
          maxLength={18}
          placeholder="000.000.000-00 ou 00.000.000/0000-00"
          onChange={(e) => setValue('cpf_cnpj', formatCpfCnpj(e.target.value), { shouldValidate: true })}
        />
      </Field>

      <label className="pw-check">
        <input type="checkbox" checked={mesmo} onChange={(e) => setMesmo(e.target.checked)} />
        <span className="pw-check-box"><Check size={13} /></span>
        <span>Destinatário é o próprio cliente</span>
      </label>

      {!mesmo && (
        <Field label="Para (destinatário)" req error={errors.destinatario?.message}>
          <input className={`pw-in${errors.destinatario ? ' err' : ''}`} {...register('destinatario')} />
        </Field>
      )}

      <div className="pw-row2">
        <Field label="Tipo de pedido" req error={errors.tipo_pedido?.message}>
          <select className="pw-in" value={tipoPedido}
            onChange={(e) => setValue('tipo_pedido', e.target.value as 'Entrega' | 'Retirada', { shouldValidate: true })}>
            <option value="Entrega">Entrega</option>
            <option value="Retirada">Retirada</option>
          </select>
        </Field>
        <Field label="Fonte do pedido" hint={fonteLocked ? 'Selecionada no início e bloqueada' : undefined}>
          {fonteLocked
            ? <div className="pw-locked"><Lock size={13} /> {fonteNome ?? `Fonte #${fonteId}`}</div>
            : <div className="pw-locked"><Lock size={13} /> Não informada</div>}
        </Field>
      </div>

      <button type="button" className={`pw-disc ${mais ? 'open' : ''}`} onClick={() => setMaisOpen((v) => !v)}>
        <ChevronDown size={16} /> Mais opções (opcional)
      </button>
      {mais && (
        <div className="pw-disc-body">
          <Field label="Código do WhatsApp" hint="Código exibido na mensagem do cliente" error={errors.codigo_whatsapp?.message}>
            <input className="pw-in" {...register('codigo_whatsapp')} placeholder="Ex.: A3F9B2K8Q1" />
          </Field>

          {foundLead ? (
            <div className="pw-lead">
              <h4>LEAD ENCONTRADO</h4>
              <p>Token: {foundLead.token_rastreio}</p>
              {foundLead.fbp && <p>Fbp: {foundLead.fbp}</p>}
              {foundLead.fbclid && <p>fbclid: {foundLead.fbclid}</p>}
            </div>
          ) : (
            <>
              <label className="pw-toggle">
                <input type="checkbox" checked={!!origemAnuncio}
                  onChange={(e) => setValue('origem_anuncio', e.target.checked, { shouldValidate: true })} />
                <span className="pw-toggle-track"><i /></span>
                <span className="pw-toggle-lbl"><Megaphone size={15} /> Pedido vindo de anúncio</span>
              </label>
              {origemAnuncio && (
                <Field label="Facebook Click ID (fbclid)" req hint="Cole o fbclid da mensagem do WhatsApp" error={errors.fbclid?.message}>
                  <input className={`pw-in${errors.fbclid ? ' err' : ''}`} {...register('fbclid')} placeholder="Ex.: AbCdEf…" />
                </Field>
              )}
            </>
          )}

          {isAdmin && vendedores.length > 0 && (
            <Field label="Vendedor responsável" hint="Opcional">
              <select className="pw-in" value={vendedorId ?? ''}
                onChange={(e) => setValue('vendedor_id', e.target.value ? Number(e.target.value) : undefined)}>
                <option value="">Não atribuído</option>
                {vendedores.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
              </select>
            </Field>
          )}
        </div>
      )}

      {/* fbp invisível, sempre registrado */}
      <input type="hidden" {...register('fbp')} />
    </>
  );
}

/** Telefone com máscara ligado ao RHF (Controller leve via useWatch/setValue). */
function PwPhoneInputController({ disabled }: { disabled?: boolean }) {
  const { control, setValue } = useFormContext<PedidoFormDataExt>();
  const telefone = useWatch({ control, name: 'telefone_cliente' }) ?? '';
  return (
    <PwPhoneInput
      value={telefone}
      disabled={disabled}
      onChange={(v) => setValue('telefone_cliente', v, { shouldValidate: true })}
    />
  );
}

export default StepClienteNovo;
