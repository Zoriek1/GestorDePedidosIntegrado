# -*- coding: utf-8 -*-
"""
Command para geração de comprovantes em lote (até 4 pedidos por folha A4).

Layouts:
- 1 pedido  → A4 cheio (delega ao GerarComprovanteCommand)
- 2 pedidos → A4 retrato com 2 metades horizontais empilhadas
- 3 pedidos → grid 2x2 com 1 célula vazia
- 4 pedidos → grid 2x2 cheio

Espaçamento de ~6mm entre células e borda dashed para corte com tesoura.
"""
from app.commands.gerar_comprovante_command import (
    GerarComprovanteCommand,
    build_pedido_context,
    fmt,
    fmt_brl,
)
from app.repositories.pedido_repository import PedidoRepository

MAX_PEDIDOS_POR_LOTE = 4


class GerarComprovanteLoteCommand:
    def __init__(self, pedido_ids: list[int]):
        self.pedido_ids = pedido_ids
        self.pedido_repo = PedidoRepository()

    def execute(self) -> str:
        if not self.pedido_ids:
            raise ValueError("Nenhum pedido selecionado")
        if len(self.pedido_ids) > MAX_PEDIDOS_POR_LOTE:
            raise ValueError(f"Máximo de {MAX_PEDIDOS_POR_LOTE} pedidos por folha")

        # 1 pedido: comportamento atual preservado
        if len(self.pedido_ids) == 1:
            return GerarComprovanteCommand(self.pedido_ids[0]).execute()

        contexts = []
        for pid in self.pedido_ids:
            pedido = self.pedido_repo.get_by_id(pid)
            if not pedido:
                raise ValueError(f"Pedido #{pid} não encontrado")
            contexts.append(build_pedido_context(pedido))

        return self._render_grid(contexts)

    def _render_slip(self, ctx: dict) -> str:
        """Renderiza um comprovante compacto (cabe em 1/2 ou 1/4 de A4)."""
        endereco_html = ""
        is_retirada = str(ctx.get("tipo", "")).lower() == "retirada"
        if ctx.get("endereco"):
            cidade = fmt(ctx.get("cidade"))
            cep = fmt(ctx.get("cep"))
            taxa = fmt_brl(ctx.get("taxa")) if ctx.get("taxa") else ""
            distancia = f"{ctx['distancia']:.2f} km" if ctx.get("distancia") is not None else ""
            extras = " · ".join(p for p in [cidade, cep, distancia, taxa] if p and p != "-")
            endereco_html = f"""
              <div class="slip-line">
                <span class="slip-lbl">Endereço:</span>
                <span class="slip-val">{fmt(ctx['endereco'])}</span>
              </div>
              <div class="slip-line slip-sub">{extras}</div>
            """
        elif is_retirada:
            endereco_html = '<div class="slip-line slip-pickup">RETIRADA NA LOJA</div>'

        destinatario_html = ""
        if ctx.get("show_destinatario") and ctx.get("destinatario_nome"):
            destinatario_html = f"""
              <div class="slip-line">
                <span class="slip-lbl">Para:</span>
                <span class="slip-val">{fmt(ctx['destinatario_nome'])}</span>
              </div>
            """

        mensagem_html = ""
        if ctx.get("mensagem"):
            mensagem_html = f"""
              <div class="slip-msg">
                <div class="slip-msg-lbl">Mensagem do cartão</div>
                <div class="slip-msg-val">{fmt(ctx['mensagem'])}</div>
              </div>
            """

        flores_qtd = []
        if ctx.get("flores_cor"):
            flores_qtd.append(fmt(ctx["flores_cor"]))
        if ctx.get("quantidade"):
            flores_qtd.append(f"Qtd: {ctx['quantidade']}")
        flores_qtd_html = (
            f'<div class="slip-line slip-sub">{" · ".join(flores_qtd)}</div>' if flores_qtd else ""
        )

        pagamento_parts = [fmt(ctx.get("pagamento"))]
        if ctx.get("status_pagto"):
            pagamento_parts.append(fmt(ctx["status_pagto"]))
        pagamento_str = " · ".join(p for p in pagamento_parts if p and p != "-")

        return f"""
        <div class="slip">
          <div class="slip-head">
            <div class="slip-head-l">
              <strong>Pedido #{ctx['id']}</strong>
              <span class="slip-tipo">{fmt(ctx.get('tipo')).upper()}</span>
            </div>
            <div class="slip-head-r">
              <span class="slip-data">{fmt(ctx.get('data_entrega'))} {fmt(ctx.get('horario')) if ctx.get('horario') else ''}</span>
              <strong class="slip-valor">{fmt_brl(ctx.get('valor'))}</strong>
            </div>
          </div>
          <div class="slip-body">
            <div class="slip-line">
              <span class="slip-lbl">Cliente:</span>
              <span class="slip-val">{fmt(ctx.get('cliente_nome'))}</span>
              <span class="slip-tel">{fmt(ctx.get('cliente_tel'))}</span>
            </div>
            {destinatario_html}
            <div class="slip-line">
              <span class="slip-lbl">Produto:</span>
              <span class="slip-val">{fmt(ctx.get('produto'))}</span>
            </div>
            {flores_qtd_html}
            {mensagem_html}
            {endereco_html}
            <div class="slip-line slip-pagto">
              <span class="slip-lbl">Pagto:</span>
              <span class="slip-val">{pagamento_str}</span>
            </div>
          </div>
        </div>
        """

    def _render_grid(self, contexts: list[dict]) -> str:
        n = len(contexts)
        slips_html = "".join(self._render_slip(c) for c in contexts)
        # Em grid 2x2 com 3 pedidos, completar a 4ª célula com placeholder vazio
        if n == 3:
            slips_html += '<div class="slip slip-empty"></div>'

        if n == 2:
            grid_class = "grid-2"
        else:
            grid_class = "grid-4"

        ids_str = ", ".join(f"#{c['id']}" for c in contexts)

        return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Comprovantes em lote ({n} pedidos)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    @page {{ size: A4 portrait; margin: 8mm; }}
    html, body {{ height: 100%; }}
    body {{
      font-family: 'Helvetica', 'Arial', sans-serif;
      color: #000;
      background: #fff;
      font-size: 11px;
    }}

    .sheet {{
      width: 100%;
      height: calc(100vh - 0mm);
      display: grid;
      gap: 6mm;
    }}
    .grid-2 {{
      grid-template-columns: 1fr;
      grid-template-rows: 1fr 1fr;
    }}
    .grid-4 {{
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
    }}

    .slip {{
      border: 1px dashed #999;
      border-radius: 4px;
      padding: 6mm;
      overflow: hidden;
      page-break-inside: avoid;
      display: flex;
      flex-direction: column;
      gap: 3mm;
    }}
    .slip-empty {{
      border: 1px dashed #ddd;
    }}

    .slip-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 4mm;
      border-bottom: 1px solid #000;
      padding-bottom: 2mm;
    }}
    .slip-head-l strong {{ font-size: 14px; }}
    .slip-tipo {{
      display: inline-block;
      margin-left: 4mm;
      padding: 1mm 2mm;
      border: 1px solid #000;
      border-radius: 2px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}
    .slip-head-r {{
      text-align: right;
      display: flex;
      flex-direction: column;
      gap: 1mm;
    }}
    .slip-data {{ font-size: 11px; font-weight: 600; }}
    .slip-valor {{ font-size: 14px; }}

    .slip-body {{
      display: flex;
      flex-direction: column;
      gap: 1.5mm;
      flex: 1;
    }}
    .slip-line {{
      display: flex;
      flex-wrap: wrap;
      gap: 2mm;
      align-items: baseline;
      line-height: 1.3;
    }}
    .slip-lbl {{
      font-size: 9px;
      text-transform: uppercase;
      color: #555;
      font-weight: 700;
      flex-shrink: 0;
    }}
    .slip-val {{ font-weight: 600; }}
    .slip-tel {{ color: #333; font-size: 10px; }}
    .slip-sub {{ font-size: 10px; color: #444; }}
    .slip-pickup {{
      text-align: center;
      padding: 2mm;
      border: 1px dashed #999;
      font-weight: 700;
    }}
    .slip-pagto {{ margin-top: auto; padding-top: 1.5mm; border-top: 1px solid #ddd; }}

    .slip-msg {{
      border: 1px dashed #888;
      background: #fafafa;
      padding: 2mm 3mm;
      border-radius: 2px;
    }}
    .slip-msg-lbl {{
      font-size: 8px;
      text-transform: uppercase;
      color: #555;
      font-weight: 700;
      margin-bottom: 1mm;
    }}
    .slip-msg-val {{
      font-weight: 600;
      white-space: pre-wrap;
      font-size: 11px;
    }}

    .meta-foot {{
      position: fixed;
      bottom: 2mm;
      left: 8mm;
      right: 8mm;
      font-size: 8px;
      color: #888;
      display: flex;
      justify-content: space-between;
    }}

    @media print {{
      body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      .no-print {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="sheet {grid_class}">
    {slips_html}
  </div>
  <div class="meta-foot no-print-screen">
    <span>Lote: {ids_str}</span>
    <span>{contexts[0]['impresso_em']}</span>
  </div>
  <script>
    window.onload = function() {{
        setTimeout(function() {{ window.print(); }}, 500);
    }};
  </script>
</body>
</html>
"""
