# -*- coding: utf-8 -*-
"""
Migration: Criar tabela meta_capi_outbox
Cria tabela para outbox de eventos Meta Conversions API.
Compatível com SQLite e PostgreSQL (usa model SQLAlchemy para gerar DDL).
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def create_meta_capi_outbox_table():
    """Cria tabela meta_capi_outbox a partir do model SQLAlchemy (portável)."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if "meta_capi_outbox" in existing_tables:
            print("[SKIP] Tabela meta_capi_outbox já existe")
            return

        print("[CREATE] Criando tabela meta_capi_outbox...")

        try:
            from app.models.meta_capi_outbox import MetaCapiOutbox

            MetaCapiOutbox.__table__.create(db.engine)
            print(f"[SUCCESS] Tabela meta_capi_outbox criada ({db.engine.dialect.name})")
        except Exception as e:
            print(f"[ERROR] Erro ao criar tabela: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    create_meta_capi_outbox_table()
