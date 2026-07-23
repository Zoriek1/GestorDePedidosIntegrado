# -*- coding: utf-8 -*-
"""Migration idempotente: adiciona colunas de taxa de cartao em store_settings."""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402

app = create_app()


def column_exists(table_name: str, column_name: str) -> bool:
    inspector = db.inspect(db.engine)
    if table_name not in inspector.get_table_names():
        return False
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def add_taxa_cartao_columns():
    with app.app_context():
        try:
            added = 0
            skipped = 0
            columns = [
                ("taxa_cartao_debito_pct", "FLOAT DEFAULT 0"),
                ("taxa_cartao_credito_json", "TEXT"),
            ]
            for col_name, definition in columns:
                if column_exists("store_settings", col_name):
                    skipped += 1
                    print(f"[SKIP] store_settings.{col_name}")
                    continue
                db.session.execute(
                    db.text(f"ALTER TABLE store_settings ADD COLUMN {col_name} {definition}")
                )
                added += 1
                print(f"[ADD] store_settings.{col_name}")

            db.session.commit()
            print(
                f"[SUCCESS] Taxa Cartao migration concluida: "
                f"{added} colunas adicionadas, {skipped} skips"
            )
        except Exception as exc:
            db.session.rollback()
            print(f"[ERROR] Migration Taxa Cartao falhou: {exc}")
            raise


if __name__ == "__main__":
    add_taxa_cartao_columns()
