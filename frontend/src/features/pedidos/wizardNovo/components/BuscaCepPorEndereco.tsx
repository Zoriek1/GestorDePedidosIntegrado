/**
 * Busca de CEP por endereço (ViaCEP reverso) — recurso novo trazido do mockup.
 * Consulta pública https://viacep.com.br/ws/UF/cidade/rua/json/ e devolve até 8 resultados.
 * Se a CSP bloquear a chamada externa, o erro é exibido de forma amigável.
 */
import { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';

export interface CepReversoItem {
  cep?: string;
  logradouro?: string;
  bairro?: string;
  localidade?: string;
  uf?: string;
}

export function BuscaCepPorEndereco({
  cidadeAtual,
  onPick,
}: {
  cidadeAtual?: string;
  onPick: (item: CepReversoItem) => void;
}) {
  const [open, setOpen] = useState(false);
  const [uf, setUf] = useState('GO');
  const [cidade, setCidade] = useState(cidadeAtual || 'Goiânia');
  const [rua, setRua] = useState('');
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');
  const [res, setRes] = useState<CepReversoItem[] | null>(null);

  async function buscar() {
    setErro(''); setRes(null);
    if (uf.length !== 2 || cidade.trim().length < 3 || rua.trim().length < 3) {
      setErro('Informe UF (2 letras), cidade e parte da rua (mín. 3 letras).');
      return;
    }
    setLoading(true);
    try {
      const url = `https://viacep.com.br/ws/${uf}/${encodeURIComponent(cidade)}/${encodeURIComponent(rua)}/json/`;
      const r = await fetch(url);
      const data = await r.json();
      if (!Array.isArray(data) || data.length === 0) setErro('Nenhum endereço encontrado.');
      else setRes((data as CepReversoItem[]).slice(0, 8));
    } catch {
      setErro('Falha na consulta. Verifique a conexão.');
    } finally {
      setLoading(false);
    }
  }

  function escolher(item: CepReversoItem) {
    onPick(item);
    setOpen(false); setRes(null); setRua('');
  }

  return (
    <div className="pw-cepwrap">
      <button type="button" className="pw-link cep-trigger" onClick={() => setOpen((v) => !v)}>
        <Search size={13} /> {open ? 'Fechar busca por endereço' : 'Não sei o CEP — buscar pelo endereço'}
      </button>
      {open && (
        <div className="pw-cepbox">
          <div className="pw-ceprow">
            <input className="pw-in uf" maxLength={2} value={uf}
              onChange={(e) => setUf(e.target.value.toUpperCase())} placeholder="UF" />
            <input className="pw-in" value={cidade} onChange={(e) => setCidade(e.target.value)} placeholder="Cidade" />
          </div>
          <div className="pw-ceprow">
            <input className="pw-in" value={rua} onChange={(e) => setRua(e.target.value)}
              placeholder="Nome da rua (ex.: Avenida 85)"
              onKeyDown={(e) => e.key === 'Enter' && buscar()} />
            <button type="button" className="pw-btn primary cep-go" onClick={buscar} disabled={loading}>
              {loading ? <Loader2 size={16} className="pw-spin" /> : <Search size={16} />}
            </button>
          </div>
          {erro && <p className="pw-cep-erro">{erro}</p>}
          {res && (
            <ul className="pw-cep-res">
              {res.map((item, i) => (
                <li key={i} onClick={() => escolher(item)}>
                  <b>{item.logradouro || '(sem logradouro)'}</b>
                  <span>{item.bairro} · {item.localidade}/{item.uf} — CEP {item.cep}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
