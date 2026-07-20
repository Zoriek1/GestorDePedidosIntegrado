# -*- coding: utf-8 -*-
"""Fase C.3: isola referências externas de pedido por empresa."""

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.pedido_external_ref import PedidoExternalRef  # noqa: E402
from app.models.store import Store  # noqa: E402

TABLE = "pedido_external_refs"
UNIQUE_NAME = "uq_pedido_external_tenant_provider_store_order"
LEGACY_UNIQUE_NAME = "uq_pedido_external_legacy_provider_store_order"


def _default_store_id(connection) -> int:
    value = connection.execute(select(Store.id).where(Store.slug == "default")).scalar_one_or_none()
    if value is None:
        count = connection.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()
        if count:
            raise RuntimeError("Há referências externas, mas a loja default não existe.")
        raise RuntimeError("Loja default ausente; execute add_store_foundation.py.")
    return int(value)


def _sqlite_rebuild(connection) -> None:
    uniques = {
        tuple(item.get("column_names") or ())
        for item in inspect(connection).get_unique_constraints(TABLE)
    }
    desired = ("store_ref_id", "provider", "store_id", "external_order_id")
    if desired in uniques:
        return

    old = f"{TABLE}__c3_legacy"
    connection.execute(text(f"ALTER TABLE {TABLE} RENAME TO {old}"))
    PedidoExternalRef.__table__.create(connection, checkfirst=False)
    old_columns = {column["name"] for column in inspect(connection).get_columns(old)}
    columns = [
        column.name for column in PedidoExternalRef.__table__.columns if column.name in old_columns
    ]
    joined = ", ".join(columns)
    connection.execute(text(f"INSERT INTO {TABLE} ({joined}) SELECT {joined} FROM {old}"))
    connection.execute(text(f"DROP TABLE {old}"))


def _postgres_constraints(connection) -> None:
    desired = ["store_ref_id", "provider", "store_id", "external_order_id"]
    uniques = inspect(connection).get_unique_constraints(TABLE)
    for constraint in uniques:
        columns = constraint.get("column_names") or []
        name = constraint.get("name")
        if columns == ["provider", "store_id", "external_order_id"] and name:
            connection.execute(text(f'ALTER TABLE {TABLE} DROP CONSTRAINT "{name}"'))
    if not any(
        item.get("column_names") == desired
        for item in inspect(connection).get_unique_constraints(TABLE)
    ):
        connection.execute(
            text(
                f"ALTER TABLE {TABLE} ADD CONSTRAINT {UNIQUE_NAME} UNIQUE "
                "(store_ref_id, provider, store_id, external_order_id)"
            )
        )

    if not any(
        fk.get("constrained_columns") == ["store_ref_id"]
        for fk in inspect(connection).get_foreign_keys(TABLE)
    ):
        connection.execute(
            text(
                f"ALTER TABLE {TABLE} ADD CONSTRAINT fk_{TABLE}_store_ref_id_stores "
                "FOREIGN KEY (store_ref_id) REFERENCES stores(id) ON DELETE RESTRICT"
            )
        )


def _legacy_null_unique(connection) -> None:
    connection.execute(
        text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {LEGACY_UNIQUE_NAME} ON {TABLE} "
            "(provider, store_id, external_order_id) WHERE store_ref_id IS NULL"
        )
    )


def _migrate_connection(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    missing = sorted({TABLE, "pedidos", "stores"} - existing)
    if missing:
        raise RuntimeError(f"Tabelas ausentes: {', '.join(missing)}")

    columns = {column["name"] for column in inspect(connection).get_columns(TABLE)}
    if "store_ref_id" not in columns:
        connection.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN store_ref_id INTEGER"))
    connection.execute(
        text(f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_store_ref_id " f"ON {TABLE} (store_ref_id)")
    )

    default_store_id = _default_store_id(connection)
    connection.execute(
        text(
            f"UPDATE {TABLE} SET store_ref_id=(SELECT store_ref_id FROM pedidos "
            f"WHERE pedidos.id={TABLE}.pedido_id) WHERE store_ref_id IS NULL"
        )
    )
    connection.execute(
        text(f"UPDATE {TABLE} SET store_ref_id=:store WHERE store_ref_id IS NULL"),
        {"store": default_store_id},
    )

    if connection.dialect.name == "postgresql":
        _postgres_constraints(connection)
    elif connection.dialect.name == "sqlite":
        _sqlite_rebuild(connection)

    _legacy_null_unique(connection)

    nulls = connection.execute(
        text(f"SELECT COUNT(*) FROM {TABLE} WHERE store_ref_id IS NULL")
    ).scalar_one()
    if nulls:
        raise RuntimeError(f"Backfill incompleto em {TABLE}: {nulls} linha(s)")


def migrate() -> None:
    if db.engine.dialect.name == "sqlite":
        with db.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.exec_driver_sql("PRAGMA legacy_alter_table=ON")
            connection.commit()
            with connection.begin():
                _migrate_connection(connection)
            connection.exec_driver_sql("PRAGMA legacy_alter_table=OFF")
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
    else:
        with db.engine.begin() as connection:
            _migrate_connection(connection)
    print("[SUCCESS] Fase C.3 aplicada")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
