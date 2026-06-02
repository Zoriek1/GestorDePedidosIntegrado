# -*- coding: utf-8 -*-
"""
Migration: Adicionar coluna codigo_whatsapp na tabela pedidos.
Armazena o token de rastreio do WhatsApp (token_rastreio do Lead) para que o pedido
preserve a chave de costura com o Lead/CAPI e o campo volte preenchido ao editar.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def add_codigo_whatsapp_column():
    """Adiciona coluna codigo_whatsapp na tabela pedidos"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_columns = [col["name"] for col in inspector.get_columns("pedidos")]

        print("[MIGRATION] Adicionando campo codigo_whatsapp na tabela pedidos...")

        if "codigo_whatsapp" not in existing_columns:
            try:
                db.session.execute(
                    db.text("ALTER TABLE pedidos ADD COLUMN codigo_whatsapp VARCHAR(64) NULL")
                )
                db.session.commit()
                print("[OK] Coluna 'codigo_whatsapp' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Erro ao adicionar coluna 'codigo_whatsapp': {e}")
        else:
            print("[SKIP] Coluna 'codigo_whatsapp' já existe")

        print("[OK] Migration concluída")


if __name__ == "__main__":
    add_codigo_whatsapp_column()
