# -*- coding: utf-8 -*-
"""
Script para recriar outboxes (deletar e recriar para tentar novamente)
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

from app import create_app, db
from app.models.pedido import Pedido
from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

app = create_app()

with app.app_context():
    print("=" * 60)
    print("RECRIAR OUTBOXES")
    print("=" * 60)
    print()

    # Buscar todos os pedidos pagos
    pedidos_pagos = (
        Pedido.query.filter(
            func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
            Pedido.deleted_at.is_(None),
        )
        .order_by(Pedido.updated_at.desc())
        .all()
    )

    print(f"[INFO] Total de pedidos pagos encontrados: {len(pedidos_pagos)}")
    print()

    # Deletar todas as outboxes existentes para esses pedidos
    print("[INFO] Deletando outboxes existentes...")
    outbox_repo = MetaCapiOutboxRepository()

    deleted_count = 0
    for pedido in pedidos_pagos:
        existing = outbox_repo.get_by_order_id(pedido.id)
        if existing:
            db.session.delete(existing)
            deleted_count += 1

    db.session.commit()
    print(f"[OK] {deleted_count} outboxes deletadas")
    print()

    # Recriar outboxes
    print("[INFO] Recriando outboxes...")
    created_count = 0
    errors = []

    for pedido in pedidos_pagos:
        try:
            outbox = outbox_repo.create_from_pedido(pedido)
            if outbox:
                created_count += 1
                if created_count <= 5:  # Mostrar apenas os primeiros 5
                    print(f"  [OK] Outbox criada para pedido #{pedido.id}")
        except Exception as e:
            error_msg = f"Erro ao criar outbox para pedido #{pedido.id}: {str(e)}"
            errors.append(error_msg)
            print(f"  [ERRO] {error_msg}")

    db.session.commit()

    print()
    print("=" * 60)
    print("RESUMO")
    print("=" * 60)
    print(f"Outboxes deletadas: {deleted_count}")
    print(f"Outboxes criadas: {created_count}")
    print(f"Erros: {len(errors)}")

    if errors:
        print()
        print("Erros detalhados:")
        for error in errors[:10]:  # Mostrar apenas os primeiros 10
            print(f"  - {error}")

    print()
    print("[OK] Processo concluido!")
    print(
        "[INFO] Execute 'python backend\\scripts\\meta\\send_daily_purchases_to_meta.py' para enviar as outboxes"
    )
