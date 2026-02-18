# -*- coding: utf-8 -*-
"""
Script simples para verificar pedidos pagos e outboxes
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Carregar variáveis de ambiente
from dotenv import load_dotenv

env_path = backend_dir / ".env"
load_dotenv(env_path, override=True)

from sqlalchemy import func

from app import create_app
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.models.pedido import Pedido

app = create_app()

with app.app_context():
    print("=" * 60)
    print("VERIFICACAO DE PEDIDOS PAGOS E OUTBOXES")
    print("=" * 60)
    print()

    # Contar pedidos pagos
    pedidos_pagos = Pedido.query.filter(
        func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]), Pedido.deleted_at.is_(None)
    ).count()

    print(f"[INFO] Total de pedidos pagos (Pago ou Parcial): {pedidos_pagos}")

    # Contar outboxes
    total_outboxes = MetaCapiOutbox.query.count()
    print(f"[INFO] Total de outboxes criadas: {total_outboxes}")

    # Contar outboxes por status
    pending = MetaCapiOutbox.query.filter(MetaCapiOutbox.status == "pending").count()
    sent = MetaCapiOutbox.query.filter(MetaCapiOutbox.status == "sent").count()
    failed = MetaCapiOutbox.query.filter(MetaCapiOutbox.status == "failed").count()

    print()
    print("[INFO] Outboxes por status:")
    print(f"  - Pending: {pending}")
    print(f"  - Sent: {sent}")
    print(f"  - Failed: {failed}")

    # Verificar pedidos pagos sem outbox
    pedidos_sem_outbox = (
        Pedido.query.filter(
            func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
            Pedido.deleted_at.is_(None),
        )
        .outerjoin(MetaCapiOutbox, Pedido.id == MetaCapiOutbox.order_id)
        .filter(MetaCapiOutbox.id.is_(None))
        .count()
    )

    print()
    print(f"[INFO] Pedidos pagos SEM outbox: {pedidos_sem_outbox}")

    # Listar alguns pedidos pagos
    print()
    print("[INFO] Primeiros 10 pedidos pagos:")
    pedidos = (
        Pedido.query.filter(
            func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
            Pedido.deleted_at.is_(None),
        )
        .order_by(Pedido.updated_at.desc())
        .limit(10)
        .all()
    )

    for p in pedidos:
        outbox = MetaCapiOutbox.query.filter_by(order_id=p.id).first()
        tem_outbox = "SIM" if outbox else "NAO"
        status_outbox = outbox.status if outbox else "N/A"
        print(
            f"  Pedido #{p.id} | Status: {p.status_pagamento} | Outbox: {tem_outbox} ({status_outbox})"
        )
