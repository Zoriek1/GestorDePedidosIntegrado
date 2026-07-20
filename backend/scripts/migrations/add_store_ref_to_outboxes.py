# -*- coding: utf-8 -*-
"""Fase D: tenant (store_ref_id) nas outboxes de integração.

Adiciona `store_ref_id` às quatro filas assíncronas e faz backfill pela entidade
de origem (pedido ou lead), para que o worker resolva o tenant a partir da própria
linha da fila. Idempotente: pode rodar em banco novo, legado e reexecutar.
"""

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.store import Store  # noqa: E402

DEFAULT_STORE_SLUG = "default"

# tabela da outbox -> (tabela-pai, coluna FK para o pai)
OUTBOX_SOURCES = {
    "meta_capi_outbox": ("pedidos", "order_id"),
    "marketing_conversion_outbox": ("pedidos", "pedido_id"),
    "bling_outbox": ("pedidos", "pedido_id"),
    "meta_capi_lead_outbox": ("leads", "lead_id"),
}
TABLES = tuple(OUTBOX_SOURCES.keys())


def _default_store_id(connection) -> int:
    value = connection.execute(
        select(Store.id).where(Store.slug == DEFAULT_STORE_SLUG)
    ).scalar_one_or_none()
    if value is None:
        populated = sum(
            connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in TABLES
            if table in inspect(connection).get_table_names()
        )
        if populated:
            raise RuntimeError("Há linhas nas outboxes, mas a loja default não existe.")
        raise RuntimeError("Loja default ausente; execute add_store_foundation.py.")
    return int(value)


def _add_column(connection, table: str, definition: str) -> None:
    columns = {c["name"] for c in inspect(connection).get_columns(table)}
    name = definition.split()[0]
    if name not in columns:
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))
        print(f"[ADD] {table}.{name}")


def _index(connection, table: str, column: str) -> None:
    connection.execute(
        text(f"CREATE INDEX IF NOT EXISTS ix_{table}_{column} ON {table} ({column})")
    )


def _backfill(connection, store_id: int) -> None:
    for table, (parent, fk) in OUTBOX_SOURCES.items():
        connection.execute(
            text(
                f"UPDATE {table} SET store_ref_id=(SELECT {parent}.store_ref_id FROM {parent} "
                f"WHERE {parent}.id={table}.{fk}) WHERE store_ref_id IS NULL"
            )
        )
    # Rede de segurança: qualquer linha remanescente (ex.: pai órfão) cai na loja default.
    for table in TABLES:
        connection.execute(
            text(f"UPDATE {table} SET store_ref_id=:s WHERE store_ref_id IS NULL"),
            {"s": store_id},
        )


def _postgres_constraints(connection) -> None:
    for table in TABLES:
        fks = inspect(connection).get_foreign_keys(table)
        if any(fk.get("constrained_columns") == ["store_ref_id"] for fk in fks):
            continue
        name = f"fk_{table}_store_ref_id_stores"
        connection.execute(
            text(
                f"ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY (store_ref_id) "
                "REFERENCES stores(id) ON DELETE RESTRICT"
            )
        )


def _migrate_connection(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    missing = sorted((set(TABLES) | {"stores", "pedidos", "leads"}) - existing)
    if missing:
        raise RuntimeError(f"Tabelas ausentes: {', '.join(missing)}")

    store_id = _default_store_id(connection)
    for table in TABLES:
        _add_column(connection, table, "store_ref_id INTEGER")
        _index(connection, table, "store_ref_id")
    _backfill(connection, store_id)

    if connection.dialect.name == "postgresql":
        _postgres_constraints(connection)

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
            connection.commit()
            with connection.begin():
                _migrate_connection(connection)
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
    else:
        with db.engine.begin() as connection:
            _migrate_connection(connection)
    print("[SUCCESS] Fase D aplicada (store_ref_id nas outboxes)")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
