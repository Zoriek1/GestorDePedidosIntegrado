# -*- coding: utf-8 -*-
"""
Migration: Criar tabela leads
Compatível com SQLite e PostgreSQL (usa model SQLAlchemy para gerar DDL).
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def create_leads_table():
    """Cria tabela leads a partir do model SQLAlchemy (portável)."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if "leads" in existing_tables:
            print("[SKIP] Tabela leads já existe")
            return

        print("[CREATE] Criando tabela leads...")

        try:
            from app.models.lead import Lead

            Lead.__table__.create(db.engine)
            print(f"[SUCCESS] Tabela leads criada ({db.engine.dialect.name})")
        except Exception as e:
            print(f"[ERROR] Erro ao criar tabela: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    create_leads_table()
