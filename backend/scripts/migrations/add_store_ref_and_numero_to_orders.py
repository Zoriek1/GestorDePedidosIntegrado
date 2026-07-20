# -*- coding: utf-8 -*-
"""Fase C.1: tenant em pedidos/leads/dependências e numeração local."""

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.lead import Lead  # noqa: E402
from app.models.push_subscription import PushSubscription  # noqa: E402
from app.models.store import Store  # noqa: E402

DEFAULT_STORE_SLUG = "default"
TABLES = (
    "pedidos",
    "leads",
    "lead_touchpoints",
    "pedido_sugestoes_endereco",
    "pedido_manual_overrides",
    "rotas_otimizadas",
    "push_subscriptions",
)


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
            raise RuntimeError("Há dados de domínio, mas a loja default não existe.")
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
    connection.execute(
        text("UPDATE pedidos SET store_ref_id=:s WHERE store_ref_id IS NULL"), {"s": store_id}
    )
    connection.execute(text("UPDATE pedidos SET numero_pedido=id WHERE numero_pedido IS NULL"))
    connection.execute(
        text("UPDATE leads SET store_ref_id=:s WHERE store_ref_id IS NULL"), {"s": store_id}
    )
    connection.execute(
        text(
            "UPDATE lead_touchpoints SET store_ref_id=(SELECT store_ref_id FROM leads "
            "WHERE leads.id=lead_touchpoints.lead_id) WHERE store_ref_id IS NULL"
        )
    )
    for table in ("pedido_sugestoes_endereco", "pedido_manual_overrides"):
        connection.execute(
            text(
                f"UPDATE {table} SET store_ref_id=(SELECT store_ref_id FROM pedidos "
                f"WHERE pedidos.id={table}.pedido_id) WHERE store_ref_id IS NULL"
            )
        )
    connection.execute(
        text(
            "UPDATE push_subscriptions SET store_ref_id=(SELECT store_ref_id FROM pedidos "
            "WHERE pedidos.id=push_subscriptions.pedido_id) "
            "WHERE store_ref_id IS NULL AND pedido_id IS NOT NULL"
        )
    )
    for table in TABLES:
        connection.execute(
            text(f"UPDATE {table} SET store_ref_id=:s WHERE store_ref_id IS NULL"),
            {"s": store_id},
        )


def _postgres_constraints(connection) -> None:
    for table, column in (("leads", "dedup_key"), ("push_subscriptions", "endpoint")):
        for constraint in inspect(connection).get_unique_constraints(table):
            if constraint.get("column_names") == [column] and constraint.get("name"):
                connection.execute(
                    text(f'ALTER TABLE {table} DROP CONSTRAINT "{constraint["name"]}"')
                )

    constraints = {
        "pedidos": (
            "uq_pedidos_store_numero_pedido",
            "store_ref_id, numero_pedido",
        ),
        "leads": ("uq_leads_store_dedup_key", "store_ref_id, dedup_key"),
        "push_subscriptions": (
            "uq_push_subscriptions_store_endpoint",
            "store_ref_id, endpoint",
        ),
    }
    for table, (name, columns) in constraints.items():
        existing = {c.get("name") for c in inspect(connection).get_unique_constraints(table)}
        if name not in existing:
            connection.execute(
                text(f"ALTER TABLE {table} ADD CONSTRAINT {name} UNIQUE ({columns})")
            )

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


def _sqlite_rebuild(connection, model) -> None:
    table = model.__table__
    name = table.name
    uniques = {
        tuple(c.get("column_names") or ()) for c in inspect(connection).get_unique_constraints(name)
    }
    legacy_single = ("dedup_key",) if name == "leads" else ("endpoint",)
    desired = (
        ("store_ref_id", "dedup_key")
        if name == "leads"
        else ("store_ref_id", "endpoint")
    )
    if legacy_single not in uniques and desired in uniques:
        return

    old = f"{name}__c1_legacy"
    connection.execute(text(f"ALTER TABLE {name} RENAME TO {old}"))
    table.create(connection, checkfirst=False)
    old_columns = {c["name"] for c in inspect(connection).get_columns(old)}
    columns = [c.name for c in table.columns if c.name in old_columns]
    joined = ", ".join(columns)
    connection.execute(text(f"INSERT INTO {name} ({joined}) SELECT {joined} FROM {old}"))
    connection.execute(text(f"DROP TABLE {old}"))


def _sqlite_pedido_unique(connection) -> None:
    desired = ("store_ref_id", "numero_pedido")
    constraints = {
        tuple(item.get("column_names") or ())
        for item in inspect(connection).get_unique_constraints("pedidos")
    }
    indexes = {
        tuple(item.get("column_names") or ())
        for item in inspect(connection).get_indexes("pedidos")
        if item.get("unique")
    }
    if desired not in constraints | indexes:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX uq_pedidos_store_numero_pedido "
                "ON pedidos (store_ref_id, numero_pedido)"
            )
        )


def _migrate_connection(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    missing = sorted((set(TABLES) | {"stores"}) - existing)
    if missing:
        raise RuntimeError(f"Tabelas ausentes: {', '.join(missing)}")

    store_id = _default_store_id(connection)
    for table in TABLES:
        _add_column(connection, table, "store_ref_id INTEGER")
        _index(connection, table, "store_ref_id")
    _add_column(connection, "pedidos", "numero_pedido INTEGER")
    _index(connection, "pedidos", "numero_pedido")
    _backfill(connection, store_id)

    if connection.dialect.name == "postgresql":
        _postgres_constraints(connection)
    elif connection.dialect.name == "sqlite":
        _sqlite_pedido_unique(connection)
        _sqlite_rebuild(connection, Lead)
        _sqlite_rebuild(connection, PushSubscription)

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
    print("[SUCCESS] Fase C.1 aplicada")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
