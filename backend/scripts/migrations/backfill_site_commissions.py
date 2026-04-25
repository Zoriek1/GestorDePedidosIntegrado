# -*- coding: utf-8 -*-
"""
Backfill: gera comissões retroativas para pedidos da fonte 'Site' (Nuvemshop)
da semana corrente em diante.

Antes da correção do bug primário, pedidos importados pela integração Nuvemshop
nunca disparavam apply_commission_lifecycle, então mesmo pedidos pagos com
vendedor atribuído ficaram sem CREDIT no ledger. Este script recupera os
pedidos a partir da segunda-feira da semana atual.

Idempotente: se já existe CREDIT ativo (não voidado) para o pedido, pula.
Reaproveita generate_commission(), respeitando todas as regras de cálculo.

Uso:
  cd backend
  python scripts/migrations/backfill_site_commissions.py            # dry-run
  python scripts/migrations/backfill_site_commissions.py --commit   # grava
"""
import argparse
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def run(commit: bool) -> dict:
    from app import create_app, db
    from app.models import FontePedido, Pedido
    from app.repositories.ledger_repository import LedgerRepository
    from app.services.commission_service import generate_commission
    from app.utils.date_utils import get_monday, today_brazil

    app = create_app()
    with app.app_context():
        monday = get_monday(today_brazil())
        print(f"[backfill] Considerando pedidos com created_at >= {monday}")

        pedidos = (
            Pedido.query.join(FontePedido, Pedido.fonte_pedido_id == FontePedido.id)
            .filter(
                Pedido.created_at >= monday,
                Pedido.status_pagamento.in_(["Pago", "Parcial"]),
                Pedido.vendedor_id.isnot(None),
                FontePedido.nome == "Site",
            )
            .all()
        )

        ledger_repo = LedgerRepository()
        created = 0
        skipped_existing = 0
        skipped_no_config = 0
        errors = 0

        for pedido in pedidos:
            if ledger_repo.get_by_pedido_id(pedido.id):
                skipped_existing += 1
                continue
            try:
                generate_commission(pedido, pedido.vendedor_id)
                # generate_commission só cria entry se houve config — checa se
                # de fato gerou algo (post-condition)
                if ledger_repo.get_by_pedido_id(pedido.id):
                    created += 1
                else:
                    skipped_no_config += 1
            except Exception as exc:
                print(f"[backfill] Pedido #{pedido.id} erro: {exc}")
                errors += 1
                db.session.rollback()

        if commit:
            db.session.commit()
            mode = "COMMIT"
        else:
            db.session.rollback()
            mode = "DRY-RUN (use --commit para gravar)"

        report = {
            "monday": monday.isoformat(),
            "total_candidatos": len(pedidos),
            "created": created,
            "skipped_existing": skipped_existing,
            "skipped_no_config": skipped_no_config,
            "errors": errors,
            "mode": mode,
        }

        print("\n[backfill] Relatório:")
        for k, v in report.items():
            print(f"  {k}: {v}")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Grava as comissões. Sem essa flag, apenas reporta (dry-run).",
    )
    args = parser.parse_args()
    run(commit=args.commit)
