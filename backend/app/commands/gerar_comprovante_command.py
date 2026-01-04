# -*- coding: utf-8 -*-
"""
Command para geração de comprovante de pedido
Segue o padrão Command Pattern e isola a lógica de visualização (Template)
"""
from datetime import datetime

from app.repositories.pedido_repository import PedidoRepository


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
        # 1. Busca dados
        pedido = self.pedido_repo.get_by_id(self.pedido_id)
        if not pedido:
            raise ValueError("Pedido não encontrado")

        # 2. Regras de Negócio

        # Regra de Atores: Cliente == Destinatário?
        cliente_norm = (pedido.cliente or "").strip().lower()
        destinatario_norm = (pedido.destinatario or "").strip().lower()
        is_mesma_pessoa = cliente_norm == destinatario_norm

        # Regra de Contexto: Retirada vs Entrega
        is_retirada = (pedido.tipo_pedido or "").lower() == "retirada"

        # Preparação do Contexto (Data Bag)
        ctx = {
            "id": pedido.id,
            "status": pedido.status,
            "tipo": pedido.tipo_pedido,
            "fonte": pedido.fonte_pedido_rel.nome
            if pedido.fonte_pedido_rel
            else (pedido.fonte_pedido or ""),
            # Atores
            "cliente_nome": pedido.cliente,
            "cliente_tel": pedido.telefone_cliente,
            "destinatario_nome": pedido.destinatario,
            "show_destinatario": not is_mesma_pessoa,  # Flag para o template
            # Produto
            "produto": pedido.produto,
            "flores_cor": pedido.flores_cor,
            "mensagem": pedido.mensagem,
            "quantidade": pedido.quantidade,
            "valor": pedido.valor,
            # Logística
            "data_entrega": pedido.dia_entrega.strftime("%d/%m/%Y") if pedido.dia_entrega else "",
            "horario": pedido.horario,
            "endereco": None if is_retirada else pedido.endereco,  # Null Check Rule
            "cidade": None if is_retirada else pedido.cidade,
            "cep": None if is_retirada else pedido.cep,
            "distancia": None if is_retirada else pedido.distancia_km,
            "taxa": None if is_retirada else pedido.taxa_entrega,
            "obs_entrega": None if is_retirada else pedido.obs_entrega,
            # Pagamento
            "pagamento": pedido.pagamento,
            "status_pagto": pedido.status_pagamento,
            "obs": pedido.observacoes,
            # Meta
            "impresso_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }

        # 3. Renderiza Template
        return self._render_template(ctx)

    def _render_template(self, ctx: dict) -> str:
        """
        Template Engine Embutido (String Interpolation)
        Gera HTML otimizado para impressão térmica/A4
        """

        # Helpers de formatação
        def fmt(val):
            return str(val) if val is not None and val != "" else "-"

        def fmt_brl(val):
            if val is None or val == "":
                return "-"
            try:
                # Tenta converter string "R$ 100,00" ou float
                if isinstance(val, (int, float)):
                    num = val
                else:
                    clean = (
                        str(val)
                        .replace("R$", "")
                        .replace(" ", "")
                        .replace(".", "")
                        .replace(",", ".")
                    )
                    num = float(clean)
                return f"R$ {num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except (ValueError, TypeError):
                return str(val)

        # Badges e Estilos Condicionais
        status_pagto_class = (
            "badge-black" if str(ctx.get("status_pagto")).lower() == "pendente" else "badge"
        )

        # Lógica de renderização de seções (simulando 'if' do template engine)

        # Seção Destinatário (só renderiza se show_destinatario for True)
        html_destinatario = ""
        if ctx["show_destinatario"]:
            html_destinatario = f"""
            <div class="row">
                <div class="label">Para (Destinatário)</div>
                <div class="value">{fmt(ctx['destinatario_nome'])}</div>
            </div>
            """

        # Seção Endereço (só renderiza se não for Retirada e tiver endereço)
        html_endereco = ""
        if ctx["endereco"]:
            html_endereco = f"""
             <div class="card full">
                <div class="h"><span class="dot"></span><span class="h-title">Endereço de Entrega</span></div>
                <div class="box">{fmt(ctx['endereco'])}</div>
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

        # HTML Structure
        return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Pedido #{ctx['id']}</title>
  <style>
    :root {{ --text: #000; --bg: #fff; --border: #ccc; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    @page {{ size: A4; margin: 10mm; }}
    body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: var(--text); background: var(--bg); padding: 10mm; font-size: 14px; }}

    .header {{ border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end; }}
    .title {{ font-size: 32px; font-weight: 900; line-height: 1; }}
    .subtitle {{ font-size: 18px; font-weight: 700; margin-top: 5px; }}
    .meta {{ text-align: right; font-size: 12px; }}

    .key-info {{ display: flex; gap: 15px; margin-bottom: 20px; background: #f0f0f0; padding: 15px; border-radius: 8px; border: 1px solid #999; }}
    .k-item {{ flex: 1; }}
    .k-label {{ font-size: 10px; text-transform: uppercase; font-weight: 700; color: #555; }}
    .k-val {{ font-size: 16px; font-weight: 900; }}

    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
    .card {{ border: 1px solid #999; border-radius: 8px; padding: 12px; page-break-inside: avoid; }}
    .card.full {{ grid-column: 1 / -1; }}

    .h {{ display: flex; align-items: center; gap: 8px; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
    .dot {{ width: 10px; height: 10px; background: #000; border-radius: 50%; }}
    .h-title {{ font-weight: 900; font-size: 14px; text-transform: uppercase; }}

    .rows {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .row {{ display: flex; flex-direction: column; }}
    .label {{ font-size: 10px; text-transform: uppercase; color: #666; }}
    .value {{ font-weight: 700; font-size: 13px; }}

    .box {{ border: 2px dashed #999; padding: 10px; background: #fafafa; font-weight: 700; white-space: pre-wrap; }}

    .badge-black {{ background: #000; color: #fff; padding: 2px 6px; border-radius: 4px; display: inline-block; }}

    @media print {{
        .no-print {{ display: none; }}
        body {{ -webkit-print-color-adjust: exact; }}
    }}
  </style>
</head>
<body>
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
  </div>

  <div class="grid">
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

    <!-- Produto -->
    <div class="card">
        <div class="h"><span class="dot"></span><span class="h-title">Produto</span></div>
        <div class="row" style="margin-bottom:8px">
            <div class="label">Descrição</div>
            <div class="value">{fmt(ctx['produto'])}</div>
        </div>
        <div class="rows">
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

    <!-- Pagamento -->
    <div class="card full">
        <div class="h"><span class="dot"></span><span class="h-title">Pagamento</span></div>
        <div class="rows">
            <div class="row">
                <div class="label">Forma</div>
                <div class="value">{fmt(ctx['pagamento'])}</div>
            </div>
            <div class="row">
                <div class="label">Status</div>
                <div class="value"><span class="{status_pagto_class}">{fmt(ctx['status_pagto'])}</span></div>
            </div>
            <div class="row">
                <div class="label">Observações</div>
                <div class="value">{fmt(ctx['obs'])}</div>
            </div>
        </div>
    </div>
  </div>

  <script>
    window.onload = function() {{
        setTimeout(function() {{ window.print(); }}, 500);
    }};
  </script>
</body>
</html>
"""
