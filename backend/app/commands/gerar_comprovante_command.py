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


def build_pedido_context(pedido) -> dict:
    """Constrói o data bag de contexto a partir do model Pedido."""
    cliente_norm = (pedido.cliente or "").strip().lower()
    destinatario_norm = (pedido.destinatario or "").strip().lower()
    is_mesma_pessoa = cliente_norm == destinatario_norm

    is_retirada = (pedido.tipo_pedido or "").lower() == "retirada"
    delivery_details = [] if is_retirada else build_delivery_detail_lines(pedido)

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


COMPROVANTE_CSS = """
    :root { --text: #000; --bg: #fff; --border: #ccc; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    @page { size: A4; margin: 10mm; }
    body { font-family: 'Helvetica', 'Arial', sans-serif; color: var(--text); background: var(--bg); padding: 0; font-size: 14px; }

    .header { border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-end; }
    .title { font-size: 32px; font-weight: 900; line-height: 1; }
    .subtitle { font-size: 18px; font-weight: 700; margin-top: 5px; }
    .meta { text-align: right; font-size: 12px; }

    .key-info { display: flex; gap: 12px; margin-bottom: 12px; background: #f0f0f0; padding: 12px; border-radius: 8px; border: 1px solid #999; align-items: center; }
    .k-item { flex: 1; }
    .k-label { font-size: 10px; text-transform: uppercase; font-weight: 700; color: #555; }
    .k-val { font-size: 16px; font-weight: 900; }

    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .card { border: 1px solid #999; border-radius: 8px; padding: 10px; page-break-inside: avoid; }
    .card.full { grid-column: 1 / -1; }

    .h { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .dot { width: 10px; height: 10px; background: #000; border-radius: 50%; }
    .h-title { font-weight: 900; font-size: 14px; text-transform: uppercase; }

    .rows { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .row { display: flex; flex-direction: column; }
    .label { font-size: 10px; text-transform: uppercase; color: #666; }
    .value { font-weight: 700; font-size: 13px; }
    .detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 8px; }

    .box { border: 2px dashed #999; padding: 10px; background: #fafafa; font-weight: 700; white-space: pre-wrap; }

    .badge-black { background: #000; color: #fff; padding: 2px 6px; border-radius: 4px; display: inline-block; }

    /* VIS-05: produto em destaque (montagem) + selo de pagamento visível */
    .produto-xl { font-size: 22px; font-weight: 800; line-height: 1.2; }
    .slip-seal { display: inline-block; padding: 3px 10px; border-radius: 4px; font-weight: 800; font-size: 14px; letter-spacing: 0.5px; }
    .seal-paid { background: #000; color: #fff; }
    .seal-pending { background: #fff; color: #000; border: 2px solid #000; }

    @media print {
        .no-print { display: none; }
        body { -webkit-print-color-adjust: exact; }
    }
"""


def payment_seal(ctx: dict) -> tuple:
    """VIS-05: classe + texto do selo de pagamento (PAGO sólido / PENDENTE contornado)."""
    status_raw = str(ctx.get("status_pagto") or "").strip().lower()
    if status_raw == "pendente":
        return "seal-pending", "PENDENTE"
    if status_raw == "parcial":
        return "seal-pending", "PARCIAL"
    if status_raw:
        return "seal-paid", "PAGO"
    return "seal-pending", "—"


def render_comprovante_body(ctx: dict) -> str:
    """Conteúdo interno do comprovante (header + key-info + grid), sem <html>/<style>/
    <script>. Reusado pelo comprovante single e pelo lote 1-por-página."""
    seal_class, seal_text = payment_seal(ctx)

    html_destinatario = ""
    if ctx["show_destinatario"]:
        html_destinatario = f"""
            <div class="row">
                <div class="label">Para (Destinatário)</div>
                <div class="value">{fmt(ctx['destinatario_nome'])}</div>
            </div>
            """

    html_endereco = ""
    if ctx["endereco"] or ctx.get("delivery_details"):
        detalhes_html = ""
        if ctx.get("delivery_details"):
            detail_items = "".join(
                f'<div class="row"><div class="label">{fmt(label)}</div><div class="value">{fmt(value)}</div></div>'
                for label, value in ctx["delivery_details"]
            )
            detalhes_html = f'<div class="detail-grid">{detail_items}</div>'
        html_endereco = f"""
             <div class="card full">
                <div class="h"><span class="dot"></span><span class="h-title">Endereço de Entrega</span></div>
                <div class="box">{fmt(ctx['endereco'])}</div>
                {detalhes_html}
                <div class="rows" style="margin-top:8px">
                    <div class="row"><div class="label">Cidade</div><div class="value">{fmt(ctx['cidade'])}</div></div>
                    <div class="row"><div class="label">CEP</div><div class="value">{fmt(ctx['cep'])}</div></div>
                    <div class="row"><div class="label">Distância</div><div class="value">{f"{ctx['distancia']:.2f} km" if ctx['distancia'] else "-"}</div></div>
                    <div class="row"><div class="label">Taxa</div><div class="value">{fmt_brl(ctx['taxa'])}</div></div>
                </div>
             </div>
             """
    elif str(ctx["tipo"]).lower() == "retirada":
        html_endereco = """
             <div class="card full">
                <div class="h"><span class="dot"></span><span class="h-title">Logística</span></div>
                <div class="box" style="text-align:center; padding:15px">RETIRADA NA LOJA (Sem entrega)</div>
             </div>
             """

    return f"""
  <div class="header">
    <div>
        <div class="title">Pedido #{ctx['id']}</div>
        <div class="subtitle">{fmt(ctx['tipo']).upper()}</div>
    </div>
    <div class="meta">
        <div>Emissão: {ctx['impresso_em']}</div>
        <div>Fonte: {fmt(ctx['fonte'])}</div>
    </div>
  </div>

  <div class="key-info">
    <div class="k-item">
        <div class="k-label">Data Entrega</div>
        <div class="k-val">{ctx['data_entrega']} <small>{ctx['horario']}</small></div>
    </div>
    <div class="k-item">
        <div class="k-label">Cliente</div>
        <div class="k-val">{fmt(ctx['cliente_nome'])}</div>
    </div>
    <div class="k-item">
        <div class="k-label">Valor Total</div>
        <div class="k-val">{fmt_brl(ctx['valor'])}</div>
    </div>
    <div class="k-item">
        <div class="k-label">Pagamento</div>
        <div class="k-val"><span class="slip-seal {seal_class}">{seal_text}</span></div>
    </div>
  </div>

  <div class="grid">
    <!-- Produto (destaque para a montagem) -->
    <div class="card full">
        <div class="h"><span class="dot"></span><span class="h-title">Produto</span></div>
        <div class="produto-xl">{fmt(ctx['produto'])}</div>
        <div class="rows" style="margin-top:8px">
            <div class="row">
                <div class="label">Flores/Cor</div>
                <div class="value">{fmt(ctx['flores_cor'])}</div>
            </div>
            <div class="row">
                <div class="label">Qtd</div>
                <div class="value">{fmt(ctx['quantidade'])}</div>
            </div>
        </div>
    </div>

    <!-- Mensagem (Full Width) -->
    <div class="card full">
        <div class="h"><span class="dot"></span><span class="h-title">Cartão / Mensagem</span></div>
        <div class="box">{fmt(ctx['mensagem'])}</div>
    </div>

    <!-- Logística (Endereço ou Retirada) -->
    {html_endereco}

    <!-- Cliente -->
    <div class="card">
        <div class="h"><span class="dot"></span><span class="h-title">Dados do Cliente</span></div>
        <div class="rows">
            <div class="row">
                <div class="label">Nome</div>
                <div class="value">{fmt(ctx['cliente_nome'])}</div>
            </div>
            <div class="row">
                <div class="label">Telefone</div>
                <div class="value">{fmt(ctx['cliente_tel'])}</div>
            </div>
            {html_destinatario}
        </div>
    </div>

    <!-- Pagamento -->
    <div class="card">
        <div class="h"><span class="dot"></span><span class="h-title">Pagamento</span></div>
        <div class="rows">
            <div class="row">
                <div class="label">Forma</div>
                <div class="value">{fmt(ctx['pagamento'])}</div>
            </div>
            <div class="row">
                <div class="label">Status</div>
                <div class="value"><span class="slip-seal {seal_class}">{seal_text}</span></div>
            </div>
            <div class="row">
                <div class="label">Observações</div>
                <div class="value">{fmt(ctx['obs'])}</div>
            </div>
        </div>
    </div>
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
