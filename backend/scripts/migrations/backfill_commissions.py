# -*- coding: utf-8 -*-
"""
Backfill: gera comissões para pedidos pagos que ainda não têm entry de comissão.

Uso:
  cd backend
  python scripts/migrations/backfill_commissions.py

  # Dry-run (não salva nada):
  python scripts/migrations/backfill_commissions.py --dry-run

  # Limitar a um vendedor:
  python scripts/migrations/backfill_commissions.py --vendedor-id 2
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def run(dry_run: bool = False, vendedor_id_filter: int | None = None):
    from app import db
    from app.models.ledger_entry import LedgerEntry
    from app.models.pedido import Pedido
    from app.services.commission_service import generate_commission

    print(f"[BACKFILL] dry_run={dry_run}, vendedor_id_filter={vendedor_id_filter}")

    # Pedidos pagos com vendedor atribuído
    query = Pedido.query.filter(
        Pedido.status_pagamento.in_(["Pago", "Parcial"]),
        Pedido.vendedor_id.isnot(None),
    )
    if vendedor_id_filter:
        query = query.filter(Pedido.vendedor_id == vendedor_id_filter)

    pedidos = query.order_by(Pedido.id).all()
    print(f"[BACKFILL] {len(pedidos)} pedido(s) pago(s) com vendedor encontrado(s).")

    # IDs que já têm entry de comissão ativa
    existing_pedido_ids = {
        r[0]
        for r in db.session.query(LedgerEntry.pedido_id)
        .filter(LedgerEntry.pedido_id.isnot(None), LedgerEntry.voided.is_(False))
        .all()
    }

    generated = 0
    skipped = 0
    errors = 0

    for pedido in pedidos:
        if pedido.id in existing_pedido_ids:
            skipped += 1
            continue

        try:
            if not dry_run:
                generate_commission(pedido, pedido.vendedor_id)
            print(
                f"[BACKFILL] {'[DRY]' if dry_run else '[OK] '} Pedido #{pedido.id} "
                f"(vendedor={pedido.vendedor_id}, fonte={pedido.fonte_pedido})"
            )
            generated += 1
        except Exception as e:
            print(f"[BACKFILL] [ERRO] Pedido #{pedido.id}: {e}")
            db.session.rollback()
            errors += 1

    if not dry_run and generated:
        db.session.commit()

    print(
        f"\n[BACKFILL] Concluído — gerados: {generated}, já existiam: {skipped}, erros: {errors}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--vendedor-id", type=int, default=None)
    args = parser.parse_args()

    from app import create_app

    app = create_app()
    with app.app_context():
        run(dry_run=args.dry_run, vendedor_id_filter=args.vendedor_id)
