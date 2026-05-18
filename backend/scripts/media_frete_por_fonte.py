#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script: média dos valores de frete por fonte de pedido.

Agrega por FontePedido (com fallback para o campo legado Pedido.fonte_pedido)
e calcula média/contagem para:
  - taxa_entrega          (custo operacional)
  - frete_cobrado_cliente (frete cobrado do cliente)
  - frete_liquido_cliente (frete líquido pago pelo cliente)

Uso:
    docker compose exec backend python scripts/media_frete_por_fonte.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import case, func  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models.fonte_pedido import FontePedido  # noqa: E402
from app.models.pedido import Pedido  # noqa: E402


def media_frete_por_fonte():
    # Rótulo: nome da fonte (join) ou string legada; "(sem fonte)" se nenhum.
    fonte_label = func.coalesce(
        FontePedido.nome,
        case((Pedido.fonte_pedido != "", Pedido.fonte_pedido), else_=None),
        "(sem fonte)",
    ).label("fonte")

    rows = (
        db.session.query(
            fonte_label,
            func.count(Pedido.id).label("total_pedidos"),
            func.avg(Pedido.taxa_entrega).label("media_taxa_entrega"),
            func.count(Pedido.taxa_entrega).label("n_taxa_entrega"),
            func.avg(Pedido.frete_cobrado_cliente).label("media_frete_cobrado"),
            func.count(Pedido.frete_cobrado_cliente).label("n_frete_cobrado"),
            func.avg(Pedido.frete_liquido_cliente).label("media_frete_liquido"),
            func.count(Pedido.frete_liquido_cliente).label("n_frete_liquido"),
        )
        .outerjoin(FontePedido, Pedido.fonte_pedido_id == FontePedido.id)
        .filter(Pedido.deleted_at.is_(None))
        .group_by(fonte_label)
        .order_by(func.count(Pedido.id).desc())
        .all()
    )
    return rows


def fmt(v):
    return f"R$ {v:>8.2f}" if v is not None else "       —"


def main():
    app = create_app()
    with app.app_context():
        rows = media_frete_por_fonte()

        if not rows:
            print("Nenhum pedido encontrado.")
            return

        header = (
            f"{'Fonte':<25} {'Pedidos':>8} | "
            f"{'Taxa entrega (n)':>22} | "
            f"{'Frete cobrado (n)':>22} | "
            f"{'Frete líquido (n)':>22}"
        )
        print(header)
        print("-" * len(header))

        for r in rows:
            print(
                f"{(r.fonte or '(sem fonte)'):<25} "
                f"{r.total_pedidos:>8} | "
                f"{fmt(r.media_taxa_entrega)} ({r.n_taxa_entrega:>4}) | "
                f"{fmt(r.media_frete_cobrado)} ({r.n_frete_cobrado:>4}) | "
                f"{fmt(r.media_frete_liquido)} ({r.n_frete_liquido:>4})"
            )


if __name__ == "__main__":
    main()
