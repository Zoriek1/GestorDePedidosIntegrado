# -*- coding: utf-8 -*-
"""
Migration: Adicionar campo pedido_id na tabela leads.

Vincula o lead ao pedido criado a partir dele, permitindo exibir
o valor do pedido e navegar diretamente para ele no painel de Leads.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def add_pedido_id_column():
    """Adiciona coluna pedido_id (FK para pedidos.id) na tabela leads."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        if "leads" not in existing_tables:
            print("[SKIP] Tabela leads não existe")
            return

        existing_columns = [col["name"] for col in inspector.get_columns("leads")]
        if "pedido_id" in existing_columns:
            print("[SKIP] Coluna 'pedido_id' já existe")
            return

        print("[MIGRATION] Adicionando coluna pedido_id na tabela leads...")
        try:
            db.session.execute(
                db.text("ALTER TABLE leads ADD COLUMN pedido_id INTEGER NULL REFERENCES pedidos(id)")
            )
            db.session.execute(
                db.text("CREATE INDEX IF NOT EXISTS ix_leads_pedido_id ON leads (pedido_id)")
            )
            db.session.commit()
            print("[OK] Coluna 'pedido_id' adicionada com índice")
        except Exception as e:
            db.session.rollback()
            print(f"[ERRO] Erro ao adicionar coluna 'pedido_id': {e}")
            raise

        print("[OK] Migration concluída")


if __name__ == "__main__":
    add_pedido_id_column()
