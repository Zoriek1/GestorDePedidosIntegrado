# -*- coding: utf-8 -*-
"""
Migration (backfill): preenche `pedidos.slot_inicio` a partir de `horario` quando nulo.

Contexto (INT-01): a lista de pedidos passa a ordenar pelo horário REAL (slot_inicio, Time)
em vez da string lexicográfica de `horario`. Pedidos do site já têm slot_inicio (alocador);
pedidos manuais antigos não. Este script deriva slot_inicio do `horario` parseado para todas
as linhas que ainda estão nulas, usando o mesmo `parse_customer_window` do alocador.

Idempotente — só toca linhas com slot_inicio NULL e horario parseável. Independe de dialeto
(backfill em Python via ORM).

Uso (VPS):
    docker compose exec backend python scripts/migrations/backfill_slot_inicio_from_horario.py
"""

from app import create_app, db
from app.models.pedido import Pedido
from app.services.delivery_slot_allocator import derive_slot_inicio


def run() -> bool:
    print(f"[INFO] Dialeto: {db.engine.dialect.name}")

    pendentes = (
        Pedido.query.filter(Pedido.slot_inicio.is_(None)).filter(Pedido.horario.isnot(None)).all()
    )
    print(f"[INFO] {len(pendentes)} pedido(s) sem slot_inicio com horário preenchido.")

    atualizados = 0
    nao_parseaveis = 0
    for pedido in pendentes:
        slot = derive_slot_inicio(pedido.horario)
        if slot is None:
            nao_parseaveis += 1
            continue
        pedido.slot_inicio = slot
        atualizados += 1

    db.session.commit()
    print(f"[OK] slot_inicio preenchido em {atualizados} pedido(s).")
    if nao_parseaveis:
        print(f"[INFO] {nao_parseaveis} pedido(s) com horário não parseável — mantidos nulos.")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Migration (backfill): pedidos.slot_inicio a partir de horario")
    print("=" * 60)
    with create_app().app_context():
        try:
            run()
        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise
    print("=" * 60)
