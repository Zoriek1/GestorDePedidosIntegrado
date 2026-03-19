# -*- coding: utf-8 -*-
"""
Migration: Adicionar campos phone e fbclid na tabela leads.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def add_phone_fbclid_columns():
    """Adiciona colunas phone e fbclid na tabela leads."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        if "leads" not in existing_tables:
            print("[SKIP] Tabela leads não existe")
            return

        existing_columns = [col["name"] for col in inspector.get_columns("leads")]
        print("[MIGRATION] Adicionando campos phone e fbclid na tabela leads...")

        if "phone" not in existing_columns:
            try:
                db.session.execute(db.text("ALTER TABLE leads ADD COLUMN phone VARCHAR(30) NULL"))
                db.session.commit()
                print("[OK] Coluna 'phone' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Erro ao adicionar coluna 'phone': {e}")
        else:
            print("[SKIP] Coluna 'phone' já existe")

        if "fbclid" not in existing_columns:
            try:
                db.session.execute(db.text("ALTER TABLE leads ADD COLUMN fbclid VARCHAR(255) NULL"))
                db.session.commit()
                print("[OK] Coluna 'fbclid' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Erro ao adicionar coluna 'fbclid': {e}")
        else:
            print("[SKIP] Coluna 'fbclid' já existe")

        print("[OK] Migration concluída")


if __name__ == "__main__":
    add_phone_fbclid_columns()
