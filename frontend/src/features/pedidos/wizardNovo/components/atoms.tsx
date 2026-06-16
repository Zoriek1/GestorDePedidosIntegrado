/**
 * Átomos visuais do wizard redesenhado (Field, SectionHead, Divider).
 * Portados do mockup WizardPedido, com suporte a mensagem de erro do react-hook-form.
 */
import type { ReactNode } from 'react';
import { Leaf } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export function SectionHead({ icon: Ico, title, sub }: { icon: LucideIcon; title: string; sub: string }) {
  return (
    <div className="pw-shead">
      <span className="pw-shead-ic"><Ico size={18} /></span>
      <div><h2>{title}</h2><p>{sub}</p></div>
    </div>
  );
}

export function Field({
  label, req, hint, error, children,
}: {
  label: string; req?: boolean; hint?: ReactNode; error?: string; children: ReactNode;
}) {
  return (
    <label className="pw-field">
      <span className="pw-field-lbl">{label}{req && <i>*</i>}</span>
      {children}
      {error
        ? <span className="pw-field-err">{error}</span>
        : hint && <span className="pw-field-hint">{hint}</span>}
    </label>
  );
}

export function Divider({ label }: { label: string }) {
  return (<div className="pw-divider"><span><Leaf size={12} /> {label}</span></div>);
}
