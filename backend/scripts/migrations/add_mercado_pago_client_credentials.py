# -*- coding: utf-8 -*-
"""Migration idempotente: adiciona client_id e client_secret ao Mercado Pago."""

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


def add_mercado_pago_client_credentials():
    with app.app_context():
        try:
            db.create_all()
            db.session.commit()

            added = 0
            skipped = 0
            columns = [
                ("mercado_pago_client_id_encrypted", "TEXT"),
                ("mercado_pago_client_secret_encrypted", "TEXT"),
            ]
            for col_name, definition in columns:
                if column_exists("store_settings", col_name):
                    skipped += 1
                    print(f"[SKIP] store_settings.{col_name}")
                    continue
                db.session.execute(
                    db.text(f"ALTER TABLE store_settings ADD COLUMN {col_name} {definition}")
                )
                db.session.commit()
                added += 1
                print(f"[ADD] store_settings.{col_name}")

            print(
                f"[SUCCESS] Mercado Pago client credentials migration concluida: "
                f"{added} colunas adicionadas, {skipped} skips"
            )
        except Exception as exc:
            db.session.rollback()
            print(f"[ERROR] Migration Mercado Pago client credentials falhou: {exc}")
            raise


if __name__ == "__main__":
    add_mercado_pago_client_credentials()
