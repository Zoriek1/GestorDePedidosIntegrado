# -*- coding: utf-8 -*-
"""
Migration: adiciona vendedor padrao por loja Nuvemshop.

Uso:
  cd backend
  python scripts/migrations/add_default_vendor_to_nuvemshop_store.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def _column_exists(inspector, table: str, column: str) -> bool:
    return column in [c["name"] for c in inspector.get_columns(table)]


def _index_exists(inspector, table: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def run():
    from sqlalchemy import inspect, text

    from app import create_app, db

    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        dialect = db.engine.dialect.name

        if not _column_exists(inspector, "nuvemshop_stores", "default_vendedor_id"):
            print("[migration] nuvemshop_stores.default_vendedor_id...")
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE nuvemshop_stores "
                        "ADD COLUMN default_vendedor_id INTEGER REFERENCES users(id)"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE nuvemshop_stores ADD COLUMN default_vendedor_id INTEGER")
                )
            db.session.commit()
            print("[migration] ok")

        inspector = inspect(db.engine)
        index_name = "ix_nuvemshop_stores_default_vendedor_id"
        if not _index_exists(inspector, "nuvemshop_stores", index_name):
            print(f"[migration] index {index_name}...")
            db.session.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    "ON nuvemshop_stores(default_vendedor_id)"
                )
            )
            db.session.commit()
            print("[migration] ok")

        print("\n[migration] Concluido.")


if __name__ == "__main__":
    run()
