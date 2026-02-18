# -*- coding: utf-8 -*-
"""
Migration: Adicionar campos fbc e fbp na tabela pedidos
Esses campos armazenam Facebook Click ID e Facebook Browser ID para melhorar
a qualidade de correspondência de eventos na Meta Conversions API.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def add_fbc_fbp_columns():
    """Adiciona colunas fbc e fbp na tabela pedidos"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_columns = [col["name"] for col in inspector.get_columns("pedidos")]

        print("[MIGRATION] Adicionando campos fbc e fbp na tabela pedidos...")

        # Adicionar coluna fbc se não existir
        if "fbc" not in existing_columns:
            try:
                db.session.execute(db.text("ALTER TABLE pedidos ADD COLUMN fbc VARCHAR(255) NULL"))
                db.session.commit()
                print("[OK] Coluna 'fbc' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Erro ao adicionar coluna 'fbc': {e}")
        else:
            print("[SKIP] Coluna 'fbc' já existe")

        # Adicionar coluna fbp se não existir
        if "fbp" not in existing_columns:
            try:
                db.session.execute(db.text("ALTER TABLE pedidos ADD COLUMN fbp VARCHAR(255) NULL"))
                db.session.commit()
                print("[OK] Coluna 'fbp' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Erro ao adicionar coluna 'fbp': {e}")
        else:
            print("[SKIP] Coluna 'fbp' já existe")

        print("[OK] Migration concluída")


if __name__ == "__main__":
    add_fbc_fbp_columns()
