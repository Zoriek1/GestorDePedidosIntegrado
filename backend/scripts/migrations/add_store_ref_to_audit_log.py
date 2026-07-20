# -*- coding: utf-8 -*-
"""Fase C.4: isola o log de auditoria por empresa."""

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.store import Store  # noqa: E402

TABLE = "audit_log"


def _default_store_id(connection) -> int | None:
    value = connection.execute(select(Store.id).where(Store.slug == "default")).scalar_one_or_none()
    if value is not None:
        return int(value)
    count = connection.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()
    if count:
        raise RuntimeError("Ha logs de auditoria, mas a loja default nao existe.")
    return None


def _postgres_fk(connection) -> None:
    if any(
        fk.get("constrained_columns") == ["store_ref_id"]
        for fk in inspect(connection).get_foreign_keys(TABLE)
    ):
        return
    connection.execute(
        text(
            f"ALTER TABLE {TABLE} ADD CONSTRAINT fk_{TABLE}_store_ref_id_stores "
            "FOREIGN KEY (store_ref_id) REFERENCES stores(id) ON DELETE RESTRICT"
        )
    )


def _sqlite_rebuild_if_needed(connection) -> None:
    if any(
        fk.get("constrained_columns") == ["store_ref_id"]
        for fk in inspect(connection).get_foreign_keys(TABLE)
    ):
        return

    indexes = [
        index
        for index in inspect(connection).get_indexes(TABLE)
        if index.get("name") and index.get("column_names")
    ]
    old = f"{TABLE}__c4_legacy"
    connection.execute(text(f"ALTER TABLE {TABLE} RENAME TO {old}"))
    for index in indexes:
        connection.execute(text(f'DROP INDEX IF EXISTS "{index["name"]}"'))

    AuditLog.__table__.create(connection, checkfirst=False)
    old_columns = {column["name"] for column in inspect(connection).get_columns(old)}
    columns = [column.name for column in AuditLog.__table__.columns if column.name in old_columns]
    joined = ", ".join(columns)
    connection.execute(text(f"INSERT INTO {TABLE} ({joined}) SELECT {joined} FROM {old}"))
    connection.execute(text(f"DROP TABLE {old}"))

    current_names = {index.get("name") for index in inspect(connection).get_indexes(TABLE)}
    for index in indexes:
        name = index["name"]
        if name in current_names:
            continue
        columns_sql = ", ".join(f'"{column}"' for column in index["column_names"])
        unique = "UNIQUE " if index.get("unique") else ""
        connection.execute(text(f'CREATE {unique}INDEX "{name}" ON {TABLE} ({columns_sql})'))


def _migrate_connection(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    missing = sorted({TABLE, "stores"} - existing)
    if missing:
        raise RuntimeError(f"Tabelas ausentes: {', '.join(missing)}")

    columns = {column["name"] for column in inspect(connection).get_columns(TABLE)}
    if "store_ref_id" not in columns:
        connection.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN store_ref_id INTEGER"))
    connection.execute(
        text(f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_store_ref_id " f"ON {TABLE} (store_ref_id)")
    )

    default_store_id = _default_store_id(connection)
    if default_store_id is not None:
        connection.execute(
            text(f"UPDATE {TABLE} SET store_ref_id=:store WHERE store_ref_id IS NULL"),
            {"store": default_store_id},
        )

    if connection.dialect.name == "postgresql":
        _postgres_fk(connection)
    elif connection.dialect.name == "sqlite":
        _sqlite_rebuild_if_needed(connection)

    if default_store_id is not None:
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
    print("[SUCCESS] Fase C.4 aplicada")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
