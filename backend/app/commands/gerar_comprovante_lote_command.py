# -*- coding: utf-8 -*-
"""
Command para geração de comprovantes em lote (até 100 pedidos).

A moldura é escolhida pelo usuário (pedidos por folha A4):
- layout=1 → comprovante rico (mesmo template do single), 1 folha por pedido.
- layout=2 → 2 guias retrato lado a lado (2 colunas) por folha — VIS-05.
- layout=4 → grid 2x2 (4 guias) por folha; última folha completa com células vazias.

Espaçamento de ~6mm entre células e borda dashed para corte com tesoura.
"""
from app.commands.gerar_comprovante_command import (
    COMPROVANTE_CSS,
    build_pedido_context,
    fmt,
    fmt_brl,
    render_comprovante_body,
)
from app.repositories.pedido_repository import PedidoRepository

# Moldura escolhida pelo usuário: 1, 2 ou 4 pedidos por folha A4.
LAYOUTS_VALIDOS = (1, 2, 4)
MAX_PEDIDOS_POR_LOTE = 100


class GerarComprovanteLoteCommand:
    def __init__(self, pedido_ids: list[int], layout: int = 4):
        self.pedido_ids = pedido_ids
        # Normaliza a moldura; valores fora de {1,2,4} caem no padrão 4.
        self.layout = layout if layout in LAYOUTS_VALIDOS else 4
        self.pedido_repo = PedidoRepository()

    def execute(self) -> str:
        if not self.pedido_ids:
            raise ValueError("Nenhum pedido selecionado")
        if len(self.pedido_ids) > MAX_PEDIDOS_POR_LOTE:
            raise ValueError(f"Máximo de {MAX_PEDIDOS_POR_LOTE} pedidos por lote")

        contexts = []
        for pid in self.pedido_ids:
            pedido = self.pedido_repo.get_by_id(pid)
            if not pedido:
                raise ValueError(f"Pedido #{pid} não encontrado")
            contexts.append(build_pedido_context(pedido))

        # 1 por página: comprovante rico (mesmo template do single), uma folha por pedido.
        if self.layout == 1:
            return self._render_full_pages(contexts)
        # 2 ou 4 por página: guias compactas em grade.
        return self._render_grid(contexts, self.layout)

    @staticmethod
    def _payment_seal(ctx: dict) -> tuple[str, str]:
        """VIS-05: selo de pagamento visível (PAGO sólido / PENDENTE contornado)."""
        status = str(ctx.get("status_pagto") or "").strip().lower()
        if status == "pendente":
            return "seal-pending", "PENDENTE"
        if status == "parcial":
            return "seal-pending", "PARCIAL"
        if status:
            return "seal-paid", "PAGO"
        return "", ""

    def _render_slip(self, ctx: dict) -> str:
        """Renderiza um comprovante compacto com hierarquia visual forte
        (cabe em 1/2 ou 1/4 de A4). Prioridade de leitura:
        1. Destinatário (Para) — XL bold
        2. Produto — L bold
        3. Mensagem do cartão — destacada em bloco
        4. Endereço / Data / Cliente — médio
        5. Metadados (telefone, pagamento, taxa) — pequeno/discreto
        """
        endereco_html = ""
        is_retirada = str(ctx.get("tipo", "")).lower() == "retirada"
        if ctx.get("endereco"):
            cidade = fmt(ctx.get("cidade"))
            cep = fmt(ctx.get("cep"))
            taxa = fmt_brl(ctx.get("taxa")) if ctx.get("taxa") else ""
            distancia = f"{ctx['distancia']:.2f} km" if ctx.get("distancia") is not None else ""
            extras = " · ".join(p for p in [cidade, cep, distancia, taxa] if p and p != "-")
            extras_html = f'<div class="slip-sub">{extras}</div>' if extras else ""
            details = ctx.get("delivery_details") or []
            details_text = " | ".join(
                f"{fmt(label)}: {fmt(value)}" for label, value in details if value
            )
            details_html = f'<div class="slip-sub">{details_text}</div>' if details_text else ""
            endereco_html = f"""
              <div class="slip-block">
                <div class="slip-lbl">Endereço</div>
                <div class="slip-val-md">{fmt(ctx['endereco'])}</div>
                {details_html}
                {extras_html}
              </div>
            """
        elif is_retirada:
            endereco_html = '<div class="slip-pickup">RETIRADA NA LOJA</div>'

        destinatario_html = ""
        if ctx.get("show_destinatario") and ctx.get("destinatario_nome"):
            destinatario_html = f"""
              <div class="slip-block slip-priority">
                <div class="slip-lbl">Para</div>
                <div class="slip-val-xl">{fmt(ctx['destinatario_nome'])}</div>
              </div>
            """

        mensagem_html = ""
        if ctx.get("mensagem"):
            mensagem_html = f"""
              <div class="slip-msg">
                <div class="slip-msg-lbl">✉ Mensagem do cartão</div>
                <div class="slip-msg-val">{fmt(ctx['mensagem'])}</div>
              </div>
            """

        flores_qtd = []
        if ctx.get("flores_cor"):
            flores_qtd.append(fmt(ctx["flores_cor"]))
        if ctx.get("quantidade"):
            flores_qtd.append(f"Qtd: {ctx['quantidade']}")
        flores_qtd_html = (
            f'<div class="slip-sub">{" · ".join(flores_qtd)}</div>' if flores_qtd else ""
        )

        # Status agora aparece no selo do cabeçalho; o rodapé mostra só a forma.
        seal_class, seal_text = self._payment_seal(ctx)
        seal_html = (
            f'<span class="slip-seal {seal_class}">{seal_text}</span>' if seal_text else ""
        )
        pagamento_str = fmt(ctx.get("pagamento"))

        cliente_tel_html = (
            f'<span class="slip-tel"> · {fmt(ctx.get("cliente_tel"))}</span>'
            if ctx.get("cliente_tel") and fmt(ctx.get("cliente_tel")) != "-"
            else ""
        )

        return f"""
        <div class="slip">
          <div class="slip-head">
            <div class="slip-head-l">
              <span class="slip-id">#{ctx['id']}</span>
              <span class="slip-tipo">{fmt(ctx.get('tipo')).upper()}</span>
              {seal_html}
            </div>
            <div class="slip-head-r">
              <span class="slip-data">{fmt(ctx.get('data_entrega'))} {fmt(ctx.get('horario')) if ctx.get('horario') else ''}</span>
              <span class="slip-valor">{fmt_brl(ctx.get('valor'))}</span>
            </div>
          </div>
          <div class="slip-body">
            {destinatario_html}
            <div class="slip-block slip-priority">
              <div class="slip-lbl">Produto</div>
              <div class="slip-val-lg">{fmt(ctx.get('produto'))}</div>
              {flores_qtd_html}
            </div>
            {mensagem_html}
            {endereco_html}
            <div class="slip-foot">
              <div class="slip-foot-line">
                <span class="slip-foot-lbl">Cliente:</span>
                <span class="slip-foot-val">{fmt(ctx.get('cliente_nome'))}</span>
                {cliente_tel_html}
              </div>
              <div class="slip-foot-line">
                <span class="slip-foot-lbl">Pagto:</span>
                <span class="slip-foot-val">{pagamento_str}</span>
              </div>
            </div>
          </div>
        </div>
        """

    def _render_sheet(self, page_contexts: list[dict], layout: int) -> str:
        slips_html = "".join(self._render_slip(c) for c in page_contexts)
        # Completa as células faltantes da última folha com placeholders vazios,
        # preservando a grade da moldura escolhida.
        empties = layout - len(page_contexts)
        slips_html += '<div class="slip slip-empty"></div>' * max(0, empties)

        grid_class = "grid-2" if layout == 2 else "grid-4"
        return f'<div class="sheet {grid_class}">{slips_html}</div>'

    def _render_grid(self, contexts: list[dict], layout: int) -> str:
        n = len(contexts)
        # Quebra em folhas de `layout` pedidos (2 ou 4 por folha).
        pages = [contexts[i : i + layout] for i in range(0, n, layout)]
        sheets_html = "".join(self._render_sheet(p, layout) for p in pages)

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
      height: 281mm; /* A4 portrait (297mm) menos margens (8mm cada) */
      display: grid;
      gap: 6mm;
      page-break-after: always;
      break-after: page;
    }}
    .sheet:last-child {{
      page-break-after: auto;
      break-after: auto;
    }}
    /* VIS-05: 2-up são guias RETRATO lado a lado → 2 colunas, 1 linha
       (antes eram 2 metades horizontais empilhadas, que liam como paisagem). */
    .grid-2 {{
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr;
    }}
    .grid-4 {{
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
    }}

    .slip {{
      border: 1.5px dashed #555;
      border-radius: 4px;
      padding: 5mm 6mm;
      overflow: hidden;
      page-break-inside: avoid;
      display: flex;
      flex-direction: column;
      gap: 2.5mm;
    }}
    .slip-empty {{
      border: 1px dashed #ddd;
    }}

    /* ===== HEAD: identificador discreto (id, tipo, data, valor) ===== */
    .slip-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 4mm;
      border-bottom: 1px solid #000;
      padding-bottom: 1.5mm;
    }}
    .slip-head-l {{
      display: flex;
      align-items: center;
      gap: 3mm;
    }}
    .slip-id {{
      font-size: 11px;
      font-weight: 700;
      color: #444;
    }}
    .slip-tipo {{
      display: inline-block;
      padding: 0.8mm 2mm;
      background: #000;
      color: #fff;
      border-radius: 2px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.6px;
    }}
    /* VIS-05: selo de pagamento (alto contraste em P&B) */
    .slip-seal {{
      display: inline-block;
      padding: 0.6mm 2mm;
      border-radius: 2px;
      font-size: 9px;
      font-weight: 800;
      letter-spacing: 0.6px;
    }}
    .seal-paid {{ background: #000; color: #fff; }}
    .seal-pending {{ background: #fff; color: #000; border: 1.5px solid #000; }}
    .slip-head-r {{
      text-align: right;
      display: flex;
      align-items: baseline;
      gap: 4mm;
    }}
    .slip-data {{ font-size: 12px; font-weight: 700; color: #000; }}
    .slip-valor {{ font-size: 13px; font-weight: 700; color: #000; }}

    /* ===== BODY ===== */
    .slip-body {{
      display: flex;
      flex-direction: column;
      gap: 2.5mm;
      flex: 1;
    }}

    /* Bloco genérico: label discreto + valor destacado */
    .slip-block {{
      display: flex;
      flex-direction: column;
      gap: 0.5mm;
    }}
    .slip-priority {{
      padding-left: 2mm;
      border-left: 3px solid #000;
    }}
    .slip-lbl {{
      font-size: 8px;
      text-transform: uppercase;
      color: #777;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}

    /* Hierarquia tipográfica dos valores */
    .slip-val-xl {{
      font-size: 18px;
      font-weight: 800;
      color: #000;
      line-height: 1.15;
      letter-spacing: -0.2px;
    }}
    .slip-val-lg {{
      font-size: 14px;
      font-weight: 700;
      color: #000;
      line-height: 1.2;
    }}
    .slip-val-md {{
      font-size: 12px;
      font-weight: 600;
      color: #000;
      line-height: 1.25;
    }}
    .slip-sub {{
      font-size: 9.5px;
      color: #555;
      font-weight: 500;
      margin-top: 0.5mm;
    }}

    .slip-pickup {{
      text-align: center;
      padding: 2.5mm;
      border: 2px solid #000;
      font-weight: 800;
      font-size: 13px;
      letter-spacing: 1px;
    }}

    /* Mensagem do cartão — bloco destacado, alta prioridade visual */
    .slip-msg {{
      border: 1.5px solid #000;
      background: #f5f5f0;
      padding: 2.5mm 3mm;
      border-radius: 3px;
    }}
    .slip-msg-lbl {{
      font-size: 8px;
      text-transform: uppercase;
      color: #444;
      font-weight: 700;
      letter-spacing: 0.5px;
      margin-bottom: 1mm;
    }}
    .slip-msg-val {{
      font-weight: 600;
      white-space: pre-wrap;
      font-size: 12px;
      line-height: 1.3;
      color: #000;
      font-style: italic;
    }}

    /* Rodapé do slip: cliente + pagamento (informações secundárias) */
    .slip-foot {{
      margin-top: auto;
      padding-top: 1.5mm;
      border-top: 1px dotted #aaa;
      display: flex;
      flex-direction: column;
      gap: 0.8mm;
    }}
    .slip-foot-line {{
      display: flex;
      flex-wrap: wrap;
      gap: 1.5mm;
      align-items: baseline;
      font-size: 9.5px;
      line-height: 1.25;
    }}
    .slip-foot-lbl {{
      text-transform: uppercase;
      color: #777;
      font-weight: 700;
      font-size: 8px;
      letter-spacing: 0.4px;
    }}
    .slip-foot-val {{
      color: #333;
      font-weight: 600;
    }}
    .slip-tel {{ color: #555; font-weight: 500; }}

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
  {sheets_html}
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

    def _render_full_pages(self, contexts: list[dict]) -> str:
        """Moldura 1 por página: comprovante rico (mesmo corpo do single), uma folha
        por pedido, com quebra de página entre eles."""
        pages = "".join(
            f'<div class="page-1up">{render_comprovante_body(c)}</div>' for c in contexts
        )
        ids_str = ", ".join(f"#{c['id']}" for c in contexts)
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Comprovantes em lote ({len(contexts)} pedidos · 1 por página)</title>
  <style>{COMPROVANTE_CSS}
    .page-1up {{ page-break-after: always; break-after: page; }}
    .page-1up:last-child {{ page-break-after: auto; break-after: auto; }}
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
  </style>
</head>
<body>
  {pages}
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
