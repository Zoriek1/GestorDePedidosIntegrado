# -*- coding: utf-8 -*-
"""Cria a fundacao multi-tenant e associa integracoes ao tenant legado."""

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.store import Store  # noqa: E402

DEFAULT_STORE_NAME = "Plante uma Flor"
DEFAULT_STORE_SLUG = "default"
TARGET_TABLES = {
    "nuvemshop_stores": "fk_nuvemshop_stores_store_ref_id_stores",
    "bling_credentials": "fk_bling_credentials_store_ref_id_stores",
}


def _ensure_targets_exist(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    missing = sorted(set(TARGET_TABLES) - existing)
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            "Tabelas de integracao ausentes: "
            f"{names}. Execute create_bling_integration.py antes desta migration."
        )


def _ensure_default_store(connection) -> int:
    store_id = connection.execute(
        select(Store.id).where(Store.slug == DEFAULT_STORE_SLUG)
    ).scalar_one_or_none()
    if store_id is None:
        result = connection.execute(
            Store.__table__.insert().values(
                name=DEFAULT_STORE_NAME,
                slug=DEFAULT_STORE_SLUG,
                active=True,
            )
        )
        store_id = result.inserted_primary_key[0]
        print(f"[ADD] stores.slug={DEFAULT_STORE_SLUG}")
    else:
        print(f"[SKIP] stores.slug={DEFAULT_STORE_SLUG}")
    return int(store_id)


def _ensure_column(connection, table: str) -> None:
    columns = {column["name"] for column in inspect(connection).get_columns(table)}
    if "store_ref_id" in columns:
        print(f"[SKIP] {table}.store_ref_id")
        return
    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN store_ref_id INTEGER"))
    print(f"[ADD] {table}.store_ref_id")


def _backfill_and_validate(connection, table: str, default_store_id: int) -> None:
    result = connection.execute(
        text(f"UPDATE {table} SET store_ref_id = :store_id " "WHERE store_ref_id IS NULL"),
        {"store_id": default_store_id},
    )
    if result.rowcount:
        print(f"[BACKFILL] {table}: {result.rowcount} linha(s)")

    null_count = connection.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE store_ref_id IS NULL")
    ).scalar_one()
    orphan_count = connection.execute(
        text(
            f"SELECT COUNT(*) FROM {table} AS target "
            "LEFT JOIN stores ON stores.id = target.store_ref_id "
            "WHERE target.store_ref_id IS NOT NULL AND stores.id IS NULL"
        )
    ).scalar_one()
    if null_count or orphan_count:
        raise RuntimeError(
            f"Validacao falhou para {table}: "
            f"{null_count} nulo(s), {orphan_count} referencia(s) orfa(s)."
        )


def _ensure_index(connection, table: str) -> None:
    index_name = f"ix_{table}_store_ref_id"
    connection.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} (store_ref_id)"))


def _ensure_postgres_fk(connection, table: str, constraint_name: str) -> None:
    if connection.dialect.name != "postgresql":
        return
    foreign_keys = inspect(connection).get_foreign_keys(table)
    has_fk = any(
        fk.get("constrained_columns") == ["store_ref_id"]
        and fk.get("referred_table") == "stores"
        and fk.get("referred_columns") == ["id"]
        for fk in foreign_keys
    )
    if has_fk:
        print(f"[SKIP] FK {table}.store_ref_id")
        return
    connection.execute(
        text(
            f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} "
            "FOREIGN KEY (store_ref_id) REFERENCES stores(id) ON DELETE RESTRICT"
        )
    )
    print(f"[ADD] {constraint_name}")


def migrate() -> None:
    """Aplica a fundacao usando uma transacao/conexao unica."""
    with db.engine.begin() as connection:
        _ensure_targets_exist(connection)
        Store.__table__.create(bind=connection, checkfirst=True)
        default_store_id = _ensure_default_store(connection)

        for table, constraint_name in TARGET_TABLES.items():
            _ensure_column(connection, table)
            _backfill_and_validate(connection, table, default_store_id)
            _ensure_index(connection, table)
            _ensure_postgres_fk(connection, table, constraint_name)

    print("[SUCCESS] Fundacao multi-tenant aplicada")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
