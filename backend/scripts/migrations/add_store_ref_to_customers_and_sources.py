# -*- coding: utf-8 -*-
"""Fase C.2: isola clientes, endereços e fontes por empresa."""

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.cliente import Cliente  # noqa: E402
from app.models.fonte_pedido import FontePedido  # noqa: E402
from app.models.store import Store  # noqa: E402

TABLES = ("clientes", "enderecos_clientes", "fontes_pedido")


def _default_store_id(connection) -> int:
    value = connection.execute(select(Store.id).where(Store.slug == "default")).scalar_one_or_none()
    if value is None:
        populated = sum(
            connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in TABLES
        )
        if populated:
            raise RuntimeError("Há clientes/fontes, mas a loja default não existe.")
        raise RuntimeError("Loja default ausente; execute add_store_foundation.py.")
    return int(value)


def _add_column(connection, table: str) -> None:
    columns = {column["name"] for column in inspect(connection).get_columns(table)}
    if "store_ref_id" not in columns:
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN store_ref_id INTEGER"))
    connection.execute(
        text(f"CREATE INDEX IF NOT EXISTS ix_{table}_store_ref_id " f"ON {table} (store_ref_id)")
    )


def _backfill(connection, store_id: int) -> None:
    connection.execute(
        text("UPDATE clientes SET store_ref_id=:store WHERE store_ref_id IS NULL"),
        {"store": store_id},
    )
    connection.execute(
        text("UPDATE fontes_pedido SET store_ref_id=:store WHERE store_ref_id IS NULL"),
        {"store": store_id},
    )
    connection.execute(
        text(
            "UPDATE enderecos_clientes SET store_ref_id=(SELECT store_ref_id FROM clientes "
            "WHERE clientes.id=enderecos_clientes.cliente_id) WHERE store_ref_id IS NULL"
        )
    )
    connection.execute(
        text("UPDATE enderecos_clientes SET store_ref_id=:store WHERE store_ref_id IS NULL"),
        {"store": store_id},
    )


def _postgres_constraints(connection) -> None:
    for table, column in (("clientes", "telefone"), ("fontes_pedido", "nome")):
        for constraint in inspect(connection).get_unique_constraints(table):
            if constraint.get("column_names") == [column] and constraint.get("name"):
                connection.execute(
                    text(f'ALTER TABLE {table} DROP CONSTRAINT "{constraint["name"]}"')
                )

    uniques = {
        "clientes": ("uq_clientes_store_telefone", "store_ref_id, telefone"),
        "fontes_pedido": ("uq_fontes_pedido_store_nome", "store_ref_id, nome"),
    }
    for table, (name, columns) in uniques.items():
        names = {item.get("name") for item in inspect(connection).get_unique_constraints(table)}
        if name not in names:
            connection.execute(
                text(f"ALTER TABLE {table} ADD CONSTRAINT {name} UNIQUE ({columns})")
            )

    for table in TABLES:
        if any(
            fk.get("constrained_columns") == ["store_ref_id"]
            for fk in inspect(connection).get_foreign_keys(table)
        ):
            continue
        connection.execute(
            text(
                f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_store_ref_id_stores "
                "FOREIGN KEY (store_ref_id) REFERENCES stores(id) ON DELETE RESTRICT"
            )
        )


def _sqlite_rebuild(connection, model, legacy_column: str, desired: tuple[str, str]) -> None:
    table = model.__table__
    name = table.name
    uniques = {
        tuple(item.get("column_names") or ())
        for item in inspect(connection).get_unique_constraints(name)
    }
    if (legacy_column,) not in uniques and desired in uniques:
        return

    old = f"{name}__c2_legacy"
    connection.execute(text(f"ALTER TABLE {name} RENAME TO {old}"))
    table.create(connection, checkfirst=False)
    old_columns = {column["name"] for column in inspect(connection).get_columns(old)}
    columns = [column.name for column in table.columns if column.name in old_columns]
    joined = ", ".join(columns)
    connection.execute(text(f"INSERT INTO {name} ({joined}) SELECT {joined} FROM {old}"))
    connection.execute(text(f"DROP TABLE {old}"))


def _migrate_connection(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    missing = sorted((set(TABLES) | {"stores"}) - existing)
    if missing:
        raise RuntimeError(f"Tabelas ausentes: {', '.join(missing)}")

    store_id = _default_store_id(connection)
    for table in TABLES:
        _add_column(connection, table)
    _backfill(connection, store_id)

    if connection.dialect.name == "postgresql":
        _postgres_constraints(connection)
    elif connection.dialect.name == "sqlite":
        _sqlite_rebuild(connection, Cliente, "telefone", ("store_ref_id", "telefone"))
        _sqlite_rebuild(connection, FontePedido, "nome", ("store_ref_id", "nome"))

    for table in TABLES:
        nulls = connection.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE store_ref_id IS NULL")
        ).scalar_one()
        if nulls:
            raise RuntimeError(f"Backfill incompleto em {table}: {nulls} linha(s)")


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
    print("[SUCCESS] Fase C.2 aplicada")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
