# -*- coding: utf-8 -*-
"""
Command para geração de comprovante de pedido
Segue o padrão Command Pattern e isola a lógica de visualização (Template)
"""
from datetime import datetime

from app.repositories.pedido_repository import PedidoRepository


def fmt(val):
    return str(val) if val is not None and val != "" else "-"


def parse_valor_to_float(val):
    """
    Parse valor de qualquer formato para float
    Suporta:
    - Números: 10.00, 65
    - Formato BR: "R$ 65,00", "65,00", "1.234,56"
    - Formato US: "10.00", "65.5"
    - String simples: "10", "65"
    """
    if val is None or val == "":
        return 0.0

    if isinstance(val, (int, float)):
        return float(val)

    val_str = str(val).strip().replace("R$", "").strip()
    if not val_str:
        return 0.0

    if "," in val_str:
        clean = val_str.replace(".", "").replace(",", ".")
        try:
            return float(clean)
        except (ValueError, TypeError):
            return 0.0

    if "." in val_str:
        dot_count = val_str.count(".")
        if dot_count == 1:
            try:
                return float(val_str)
            except (ValueError, TypeError):
                return 0.0
        else:
            clean = val_str.replace(".", "")
            try:
                return float(clean)
            except (ValueError, TypeError):
                return 0.0

    try:
        return float(val_str)
    except (ValueError, TypeError):
        return 0.0


def fmt_brl(val):
    if val is None or val == "":
        return "-"
    try:
        num = parse_valor_to_float(val)
        return f"R$ {num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(val)


TIPO_LOCAL_LABELS = {
    "casa": "Casa",
    "predio": "Predio",
    "comercial": "Comercial",
}


def build_delivery_detail_lines(pedido) -> list[tuple[str, str]]:
    tipo_local = (getattr(pedido, "tipo_local", None) or "casa").strip().lower()
    lines: list[tuple[str, str]] = []
    label = TIPO_LOCAL_LABELS.get(tipo_local, "Casa")
    lines.append(("Tipo de local", label))

    if tipo_local in ("predio", "comercial") and getattr(pedido, "nome_local", None):
        lines.append(("Local", pedido.nome_local))
    if tipo_local == "predio":
        for field, label in [
            ("apto", "Apartamento"),
            ("bloco", "Bloco"),
            ("torre", "Torre"),
            ("andar", "Andar"),
        ]:
            value = getattr(pedido, field, None)
            if value:
                lines.append((label, value))
    if tipo_local == "casa":
        if getattr(pedido, "quadra", None):
            lines.append(("Quadra", pedido.quadra))
        if getattr(pedido, "lote", None):
            lines.append(("Lote", pedido.lote))
    if getattr(pedido, "complemento", None):
        lines.append(("Complemento", pedido.complemento))
    if getattr(pedido, "obs_entrega", None):
        lines.append(("Referencia", pedido.obs_entrega))
    return [(label, str(value)) for label, value in lines if value]


# tipo_local no banco é "casa | predio | comercial". Aceitamos sinônimos comuns
# (edificio, condominio, comercio, loja...) para não depender de digitação exata.
def _normalize_tipo_local(tipo_local) -> str:
    t = (tipo_local or "casa").strip().lower()
    if t in ("predio", "prédio", "edificio", "edifício", "apartamento", "ap", "apto",
             "condominio", "condomínio", "flat"):
        return "predio"
    if t in ("comercial", "comercio", "comércio", "empresa", "loja", "escritorio", "escritório"):
        return "comercial"
    return "casa"


def _s(value) -> str:
    return (str(value).strip() if value is not None else "")


def build_address_block(pedido) -> list[tuple[bool, str]]:
    """Formatação inteligente do endereço para a comanda da florista.

    Retorna uma lista de (forte, texto), onde `forte` indica destaque (negrito/maior).
    Regras por tipo de local (usa só os campos já existentes, sem repetir dado):
      - predio    → "EDIFÍCIO: <nome>, AP <apto>"  +  "RUA: <rua>, <numero>"
      - casa      → "CASA"                          +  "RUA: <rua>, <numero>"
      - comercial → "COMÉRCIO: <nome>"              +  "RUA: <rua>, <numero>"
    Depois: complementos (bloco/torre/andar/quadra/lote/complemento) e bairro/cidade/CEP.
    """
    tipo = _normalize_tipo_local(getattr(pedido, "tipo_local", None))
    nome = _s(getattr(pedido, "nome_local", None))
    apto = _s(getattr(pedido, "apto", None))
    rua = _s(getattr(pedido, "rua", None))
    numero = _s(getattr(pedido, "numero", None))
    endereco = _s(getattr(pedido, "endereco", None))
    bairro = _s(getattr(pedido, "bairro", None))
    cidade = _s(getattr(pedido, "cidade", None))
    cep = _s(getattr(pedido, "cep", None))

    lines: list[tuple[bool, str]] = []

    # Linha 1 — identificação do local (destaque)
    if tipo == "predio":
        head = "EDIFÍCIO"
        if nome:
            head += f": {nome}"
        if apto:
            head += f", AP {apto}"
        lines.append((True, head))
    elif tipo == "comercial":
        lines.append((True, f"COMÉRCIO: {nome}" if nome else "COMÉRCIO"))
    else:
        lines.append((True, "CASA"))

    # Linha 2 — logradouro (destaque). Fallback p/ o campo `endereco` legado.
    if rua:
        lines.append((True, f"RUA: {rua}, {numero}" if numero else f"RUA: {rua}"))
    elif endereco:
        lines.append((True, f"RUA: {endereco}"))

    # Complementos (discretos) — não repete apto (já está na linha 1).
    extras = []
    for label, field in (
        ("Bloco", "bloco"),
        ("Torre", "torre"),
        ("Andar", "andar"),
        ("Quadra", "quadra"),
        ("Lote", "lote"),
        ("Compl.", "complemento"),
    ):
        val = _s(getattr(pedido, field, None))
        if val:
            extras.append(f"{label} {val}")
    if extras:
        lines.append((False, " · ".join(extras)))

    # Bairro / cidade / CEP (discreto)
    loc = " · ".join(p for p in (bairro, cidade, cep) if p)
    if loc:
        lines.append((False, loc))

    return lines


def build_pedido_context(pedido) -> dict:
    """Constrói o data bag de contexto a partir do model Pedido."""
    cliente_norm = (pedido.cliente or "").strip().lower()
    destinatario_norm = (pedido.destinatario or "").strip().lower()
    is_mesma_pessoa = cliente_norm == destinatario_norm

    is_retirada = (pedido.tipo_pedido or "").lower() == "retirada"
    delivery_details = [] if is_retirada else build_delivery_detail_lines(pedido)
    endereco_lines = [] if is_retirada else build_address_block(pedido)

    return {
        "id": pedido.id,
        "status": pedido.status,
        "tipo": pedido.tipo_pedido,
        "fonte": pedido.fonte_pedido_rel.nome
        if pedido.fonte_pedido_rel
        else (pedido.fonte_pedido or ""),
        "cliente_nome": pedido.cliente,
        "cliente_tel": pedido.telefone_cliente,
        "destinatario_nome": pedido.destinatario,
        "show_destinatario": not is_mesma_pessoa,
        "produto": pedido.produto,
        "flores_cor": pedido.flores_cor,
        "mensagem": pedido.mensagem,
        "quantidade": pedido.quantidade,
        "valor": pedido.valor,
        "data_entrega": pedido.dia_entrega.strftime("%d/%m/%Y") if pedido.dia_entrega else "",
        "horario": pedido.horario,
        "endereco": None if is_retirada else pedido.endereco,
        "endereco_lines": endereco_lines,
        "rua": None if is_retirada else pedido.rua,
        "numero": None if is_retirada else pedido.numero,
        "bairro": None if is_retirada else pedido.bairro,
        "instrucao_entrega": None if is_retirada else pedido.obs_entrega,
        "tipo_local": None if is_retirada else (pedido.tipo_local or "casa"),
        "nome_local": None if is_retirada else pedido.nome_local,
        "apto": None if is_retirada else pedido.apto,
        "bloco": None if is_retirada else pedido.bloco,
        "torre": None if is_retirada else pedido.torre,
        "andar": None if is_retirada else pedido.andar,
        "quadra": None if is_retirada else pedido.quadra,
        "lote": None if is_retirada else pedido.lote,
        "complemento": None if is_retirada else pedido.complemento,
        "delivery_details": delivery_details,
        "cidade": None if is_retirada else pedido.cidade,
        "cep": None if is_retirada else pedido.cep,
        "distancia": None if is_retirada else pedido.distancia_km,
        "taxa": None if is_retirada else pedido.taxa_entrega,
        "obs_entrega": None if is_retirada else pedido.obs_entrega,
        "pagamento": pedido.pagamento,
        "status_pagto": pedido.status_pagamento,
        "obs": pedido.observacoes,
        "impresso_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }


# P&B / térmica: nada depende de cor. Sinais = caixa alta, negrito, bordas pretas,
# tracejado e borda dupla. Sem fundos cinza pra transmitir informação (em térmica
# o fundo costuma não sair) — só tinta preta sobre branco.
COMPROVANTE_CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    @page { size: A4; margin: 8mm; }
    body { font-family: 'Arial', 'Helvetica', sans-serif; color: #000; background: #fff; font-size: 13px; line-height: 1.3; }

    /* 3. Tipo de operação no topo: GARRAFAIS dentro de retângulo TRACEJADO */
    .op-banner { border: 3px dashed #000; text-align: center; padding: 7px 10px; margin-bottom: 10px; }
    .op-text { font-size: 30px; font-weight: 900; letter-spacing: 4px; text-transform: uppercase; line-height: 1; }

    /* 4. Número do pedido ENORME (>=28pt) + 1. Origem/Fonte ao lado da data */
    .head { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #000; padding-bottom: 8px; margin-bottom: 10px; gap: 12px; }
    .order-no { font-size: 42px; font-weight: 900; line-height: 0.92; }
    .order-sub { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }
    .head-meta { text-align: right; font-size: 12px; line-height: 1.5; white-space: nowrap; }
    .head-meta .fonte { font-size: 15px; font-weight: 800; text-transform: uppercase; }
    .head-meta b { font-weight: 800; }

    /* 2. Pagamento em destaque: CAIXA ALTA, NEGRITO, BORDA DUPLA */
    .pay { border: 5px double #000; text-align: center; padding: 8px 10px; margin-bottom: 10px; }
    .pay-text { font-size: 24px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; line-height: 1.05; }
    .pay-sub { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }

    /* Seções genéricas (borda preta sólida) */
    .sec { border: 1.5px solid #000; padding: 8px 10px; margin-bottom: 8px; page-break-inside: avoid; }
    .sec-title { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #000; padding-bottom: 3px; margin-bottom: 6px; }

    .produto-xl { font-size: 24px; font-weight: 900; line-height: 1.15; }
    .kv { font-size: 12px; line-height: 1.5; }
    .kv b { font-weight: 800; }
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

    /* 5. Endereço inteligente */
    .addr-strong { font-size: 16px; font-weight: 800; line-height: 1.35; }
    .addr-normal { font-size: 12px; line-height: 1.4; }
    /* 6. Instrução de entrega — destaque tracejado logo abaixo do endereço */
    .instr { border: 2px dashed #000; padding: 6px 9px; margin-top: 7px; }
    .instr-lbl { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }
    .instr-val { font-size: 14px; font-weight: 800; white-space: pre-wrap; }

    .msg { white-space: pre-wrap; font-size: 14px; font-weight: 700; min-height: 14px; }

    .pickup { text-align: center; border: 2px solid #000; padding: 12px; font-size: 16px; font-weight: 900; letter-spacing: 1px; }

    /* 7. Checkbox de conferência do florista (sem assinatura) */
    .florist { display: flex; align-items: center; gap: 12px; margin-top: 10px; border-top: 2px dashed #000; padding-top: 9px; }
    .florist .chk { width: 26px; height: 26px; border: 3px solid #000; flex: 0 0 auto; }
    .florist .chk-lbl { font-size: 15px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }

    /* Selo inline (reusado pelo lote 1-up; mantém alto contraste) */
    .slip-seal { display: inline-block; padding: 2px 8px; border: 2px solid #000; font-weight: 800; font-size: 13px; letter-spacing: 0.5px; }
    .seal-paid { background: #000; color: #fff; }
    .seal-pending { background: #fff; color: #000; }

    @media print {
        .no-print { display: none; }
        body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
"""


def payment_seal(ctx: dict) -> tuple:
    """Selo inline (classe + texto). Reusado pelo lote 1-up."""
    status_raw = str(ctx.get("status_pagto") or "").strip().lower()
    if status_raw == "pendente":
        return "seal-pending", "PENDENTE"
    if status_raw == "parcial":
        return "seal-pending", "PARCIAL"
    if status_raw:
        return "seal-paid", "PAGO"
    return "seal-pending", "—"


def payment_display(ctx: dict) -> dict:
    """Destaque do status de pagamento (caixa alta + símbolo monocromático).

    Usa dingbats P&B (✔ U+2714 / ✘ U+2718), não emoji com cor, pra sair preto na
    impressora térmica. A PALAVRA em caixa alta é o sinal primário; o símbolo reforça.
    """
    status_raw = str(ctx.get("status_pagto") or "").strip().lower()
    if status_raw == "pendente":
        return {"word": "PENDENTE", "symbol": "✘", "sub": "AGUARDANDO PAGAMENTO"}
    if status_raw == "parcial":
        return {"word": "PAGAMENTO PARCIAL", "symbol": "◑", "sub": "CONFERIR SALDO"}
    if status_raw:
        return {"word": "PAGO", "symbol": "✔", "sub": "PAGAMENTO CONFIRMADO"}
    return {"word": "PAGAMENTO NÃO INFORMADO", "symbol": "?", "sub": ""}


def render_comprovante_body(ctx: dict) -> str:
    """Comanda da florista em P&B (térmica): tipo de operação garrafal, número
    enorme, pagamento em borda dupla, endereço inteligente, instrução de entrega
    e checkbox de conferência. Sem <html>/<style>/<script> — reusado pelo single
    e pelo lote 1-por-página."""
    seal_class, seal_text = payment_seal(ctx)
    pay = payment_display(ctx)
    is_retirada = str(ctx.get("tipo") or "").lower() == "retirada"

    # 3. Banner da operação (garrafais, retângulo tracejado)
    op_text = "RETIRADA NA LOJA" if is_retirada else "ENTREGA"

    # 4 + 1. Número enorme + origem/fonte ao lado da data
    order_sub = (
        f"Para: {fmt(ctx['destinatario_nome'])}"
        if ctx.get("show_destinatario")
        else f"Cliente: {fmt(ctx['cliente_nome'])}"
    )

    # 2. Pagamento em destaque (caixa alta, negrito, borda dupla, símbolo P&B)
    pay_sub_parts = []
    if fmt(ctx.get("pagamento")) != "-":
        pay_sub_parts.append(f"FORMA: {fmt(ctx['pagamento'])}")
    pay_sub_parts.append(f"TOTAL: {fmt_brl(ctx.get('valor'))}")
    if pay.get("sub"):
        pay_sub_parts.append(pay["sub"])
    pay_sub = " · ".join(pay_sub_parts)

    # 5 + 6. Endereço inteligente + instrução de entrega
    if is_retirada:
        endereco_html = (
            '<div class="sec"><div class="pickup">RETIRADA NA LOJA — SEM ENTREGA</div></div>'
        )
    else:
        addr_rows = "".join(
            f'<div class="{"addr-strong" if strong else "addr-normal"}">{text}</div>'
            for strong, text in (ctx.get("endereco_lines") or [])
        )
        if not addr_rows:
            addr_rows = f'<div class="addr-strong">{fmt(ctx.get("endereco"))}</div>'

        op_extra = []
        if ctx.get("distancia"):
            op_extra.append(f"<b>Distância:</b> {ctx['distancia']:.2f} km")
        if ctx.get("taxa"):
            op_extra.append(f"<b>Taxa:</b> {fmt_brl(ctx['taxa'])}")
        op_extra_html = (
            f'<div class="addr-normal" style="margin-top:4px">{" · ".join(op_extra)}</div>'
            if op_extra
            else ""
        )

        instr = fmt(ctx.get("instrucao_entrega"))
        instr_html = (
            f'<div class="instr"><div class="instr-lbl">Instrução de entrega</div>'
            f'<div class="instr-val">{instr}</div></div>'
            if instr != "-"
            else ""
        )

        endereco_html = f"""
    <div class="sec">
        <div class="sec-title">Endereço de entrega</div>
        {addr_rows}
        {op_extra_html}
        {instr_html}
    </div>"""

    # Mensagem do cartão (só imprime se houver)
    mensagem_html = ""
    if fmt(ctx.get("mensagem")) != "-":
        mensagem_html = f"""
    <div class="sec">
        <div class="sec-title">Cartão / Mensagem</div>
        <div class="msg">{fmt(ctx['mensagem'])}</div>
    </div>"""

    # Linha de produto: Flores/Cor só aparece se preenchida; Qtd sempre.
    flores = fmt(ctx.get("flores_cor"))
    produto_meta = (
        f"<b>Flores/Cor:</b> {flores} &nbsp;·&nbsp; <b>Qtd:</b> {fmt(ctx['quantidade'])}"
        if flores != "-"
        else f"<b>Qtd:</b> {fmt(ctx['quantidade'])}"
    )

    html_destinatario = (
        f'<div class="kv"><b>Para:</b> {fmt(ctx["destinatario_nome"])}</div>'
        if ctx.get("show_destinatario")
        else ""
    )
    obs_html = (
        f'<div class="kv"><b>Obs.:</b> {fmt(ctx["obs"])}</div>'
        if fmt(ctx.get("obs")) != "-"
        else ""
    )

    return f"""
  <!-- 3. Tipo de operação (garrafais, tracejado) -->
  <div class="op-banner"><div class="op-text">{op_text}</div></div>

  <!-- 4. Número enorme · 1. Fonte/origem ao lado da data -->
  <div class="head">
    <div>
        <div class="order-no">#{ctx['id']}</div>
        <div class="order-sub">{order_sub}</div>
    </div>
    <div class="head-meta">
        <div class="fonte">Fonte: {fmt(ctx['fonte'])}</div>
        <div><b>Entrega:</b> {ctx['data_entrega']} {fmt(ctx['horario'])}</div>
        <div>Emissão: {ctx['impresso_em']}</div>
    </div>
  </div>

  <!-- 2. Pagamento (caixa alta, negrito, borda dupla) -->
  <div class="pay">
    <div class="pay-text">{pay['symbol']} {pay['word']}</div>
    <div class="pay-sub">{pay_sub}</div>
  </div>

  <!-- Produto (destaque para a montagem) -->
  <div class="sec">
    <div class="sec-title">Produto — montar</div>
    <div class="produto-xl">{fmt(ctx['produto'])}</div>
    <div class="kv" style="margin-top:6px">{produto_meta}</div>
  </div>
{mensagem_html}
  <!-- 5. Endereço inteligente · 6. Instrução de entrega -->
  {endereco_html}

  <!-- Cliente + Pagamento -->
  <div class="sec two-col">
    <div>
        <div class="sec-title">Cliente</div>
        <div class="kv"><b>{fmt(ctx['cliente_nome'])}</b></div>
        <div class="kv">{fmt(ctx['cliente_tel'])}</div>
        {html_destinatario}
    </div>
    <div>
        <div class="sec-title">Pagamento</div>
        <div class="kv"><b>Forma:</b> {fmt(ctx['pagamento'])}</div>
        <div class="kv"><b>Status:</b> <span class="slip-seal {seal_class}">{seal_text}</span></div>
        <div class="kv"><b>Total:</b> {fmt_brl(ctx['valor'])}</div>
        {obs_html}
    </div>
  </div>

  <!-- 7. Conferência do florista (apenas marcação) -->
  <div class="florist">
    <span class="chk"></span>
    <span class="chk-lbl">Conferido pelo florista</span>
  </div>
"""


class GerarComprovanteCommand:
    def __init__(self, pedido_id: int):
        self.pedido_id = pedido_id
        self.pedido_repo = PedidoRepository()

    def execute(self) -> str:
        """
        Executa a geração do comprovante:
        1. Busca dados (Repository)
        2. Aplica regras de negócio (Business Logic)
        3. Renderiza visual (Template)
        """
        pedido = self.pedido_repo.get_by_id(self.pedido_id)
        if not pedido:
            raise ValueError("Pedido não encontrado")

        ctx = build_pedido_context(pedido)
        return self._render_template(ctx)

    def _render_template(self, ctx: dict) -> str:
        """Documento A4 completo de um comprovante (reusa o corpo compartilhado)."""
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Pedido #{ctx['id']}</title>
  <style>{COMPROVANTE_CSS}</style>
</head>
<body>
{render_comprovante_body(ctx)}
  <script>
    window.onload = function() {{
        setTimeout(function() {{ window.print(); }}, 500);
    }};
  </script>
</body>
</html>
"""
