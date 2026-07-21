# -*- coding: utf-8 -*-
"""Adiciona store_ref_id à tabela nuvemshop_webhook_deliveries.

Backfill via nuvemshop_stores.store_ref_id (join por store_id string).
Idempotente: pode rodar em banco novo, legado e reexecutar.
"""

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.store import Store  # noqa: E402

DEFAULT_STORE_SLUG = "default"
TABLE = "nuvemshop_webhook_deliveries"


def _default_store_id(connection) -> int:
    value = connection.execute(
        select(Store.id).where(Store.slug == DEFAULT_STORE_SLUG)
    ).scalar_one_or_none()
    if value is None:
        populated = connection.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()
        if populated:
            raise RuntimeError(
                "Há linhas em nuvemshop_webhook_deliveries, mas a loja default não existe."
            )
        raise RuntimeError("Loja default ausente; execute add_store_foundation.py.")
    return int(value)


def _add_column(connection) -> None:
    columns = {c["name"] for c in inspect(connection).get_columns(TABLE)}
    if "store_ref_id" not in columns:
        connection.execute(
            text("ALTER TABLE nuvemshop_webhook_deliveries " "ADD COLUMN store_ref_id INTEGER")
        )
        print(f"[ADD] {TABLE}.store_ref_id")


def _index(connection) -> None:
    connection.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_nuvemshop_webhook_deliveries_store_ref_id "
            "ON nuvemshop_webhook_deliveries (store_ref_id)"
        )
    )


def _backfill(connection, store_id: int) -> None:
    connection.execute(
        text(
            "UPDATE nuvemshop_webhook_deliveries "
            "SET store_ref_id=(SELECT nuvemshop_stores.store_ref_id "
            "FROM nuvemshop_stores "
            "WHERE nuvemshop_stores.store_id=nuvemshop_webhook_deliveries.store_id) "
            "WHERE store_ref_id IS NULL"
        )
    )
    connection.execute(
        text(
            "UPDATE nuvemshop_webhook_deliveries " "SET store_ref_id=:s WHERE store_ref_id IS NULL"
        ),
        {"s": store_id},
    )


def _postgres_constraint(connection) -> None:
    fks = inspect(connection).get_foreign_keys(TABLE)
    if any(fk.get("constrained_columns") == ["store_ref_id"] for fk in fks):
        return
    connection.execute(
        text(
            "ALTER TABLE nuvemshop_webhook_deliveries "
            "ADD CONSTRAINT fk_nuvemshop_deliveries_store_ref_id_stores "
            "FOREIGN KEY (store_ref_id) REFERENCES stores(id) ON DELETE RESTRICT"
        )
    )


def _migrate_connection(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    missing = sorted({"nuvemshop_webhook_deliveries", "nuvemshop_stores", "stores"} - existing)
    if missing:
        raise RuntimeError(f"Tabelas ausentes: {', '.join(missing)}")

    store_id = _default_store_id(connection)
    _add_column(connection)
    _index(connection)
    _backfill(connection, store_id)

    if connection.dialect.name == "postgresql":
        _postgres_constraint(connection)

    nulls = connection.execute(
        text(f"SELECT COUNT(*) FROM {TABLE} WHERE store_ref_id IS NULL")
    ).scalar_one()
    if nulls:
        raise RuntimeError(f"Backfill incompleto em {TABLE}: {nulls} linha(s)")


def migrate() -> None:
    if db.engine.dialect.name == "sqlite":
        with db.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
            with connection.begin():
                _migrate_connection(connection)
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
    else:
        with db.engine.begin() as connection:
            _migrate_connection(connection)
    print("[SUCCESS] store_ref_id adicionado a nuvemshop_webhook_deliveries")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
