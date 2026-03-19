# -*- coding: utf-8 -*-
"""
Migration: Adicionar campo fbp na tabela leads.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def add_fbp_column():
    """Adiciona coluna fbp na tabela leads."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        if "leads" not in existing_tables:
            print("[SKIP] Tabela leads não existe")
            return

        existing_columns = [col["name"] for col in inspector.get_columns("leads")]
        if "fbp" in existing_columns:
            print("[SKIP] Coluna 'fbp' já existe")
            return

        print("[MIGRATION] Adicionando coluna fbp na tabela leads...")
        try:
            db.session.execute(db.text("ALTER TABLE leads ADD COLUMN fbp VARCHAR(255) NULL"))
            db.session.commit()
            print("[OK] Coluna 'fbp' adicionada")
        except Exception as e:
            db.session.rollback()
            print(f"[ERRO] Erro ao adicionar coluna 'fbp': {e}")
            raise

        print("[OK] Migration concluída")


if __name__ == "__main__":
    add_fbp_column()
