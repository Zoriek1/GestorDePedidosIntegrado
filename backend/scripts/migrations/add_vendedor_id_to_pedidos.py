# -*- coding: utf-8 -*-
"""
Migration: Adicionar coluna vendedor_id na tabela pedidos

Vincula cada pedido a um usuário com role=vendedor.
FK opcional (NULL = sem vendedor atribuído).
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def add_vendedor_id_column():
    """Adiciona coluna vendedor_id na tabela pedidos"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_columns = [col["name"] for col in inspector.get_columns("pedidos")]

        print("[MIGRATION] Adicionando coluna vendedor_id na tabela pedidos...")

        if "vendedor_id" not in existing_columns:
            try:
                db.session.execute(
                    db.text("ALTER TABLE pedidos ADD COLUMN vendedor_id INTEGER NULL REFERENCES users(id)")
                )
                db.session.commit()
                print("[OK] Coluna 'vendedor_id' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Erro ao adicionar coluna 'vendedor_id': {e}")
        else:
            print("[SKIP] Coluna 'vendedor_id' já existe")

        print("[OK] Migration concluída")


if __name__ == "__main__":
    add_vendedor_id_column()
