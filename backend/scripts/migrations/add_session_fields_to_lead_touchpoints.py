# -*- coding: utf-8 -*-
"""
Migration: Adicionar campos de sessão (first_landing_url, session_referrer) na
tabela lead_touchpoints.

A LP envia esses campos no POST /api/leads (camada sessionStorage), mas até então
eram descartados. Servem para diagnosticar perda de UTM: distinguir "URL tinha utm
mas campanha veio branca" (storage sandboxed em webview in-app) de teoria iOS/Apple.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()

TABLE = "lead_touchpoints"
NEW_COLUMNS = ("first_landing_url", "session_referrer")


def add_session_columns():
    """Adiciona colunas de sessão na tabela lead_touchpoints (idempotente)."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        if TABLE not in inspector.get_table_names():
            print(f"[SKIP] Tabela {TABLE} não existe")
            return

        existing_columns = {col["name"] for col in inspector.get_columns(TABLE)}
        to_add = [c for c in NEW_COLUMNS if c not in existing_columns]
        if not to_add:
            print("[SKIP] Colunas de sessão já existem")
            return

        for column in to_add:
            print(f"[MIGRATION] Adicionando coluna {column} em {TABLE}...")
            try:
                db.session.execute(db.text(f"ALTER TABLE {TABLE} ADD COLUMN {column} TEXT"))
                db.session.commit()
                print(f"[OK] Coluna '{column}' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Erro ao adicionar coluna '{column}': {e}")
                raise

        print("[OK] Migration concluída")


if __name__ == "__main__":
    add_session_columns()
