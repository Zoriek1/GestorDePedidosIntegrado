# -*- coding: utf-8 -*-
"""Associa usuarios ao tenant: adiciona users.store_ref_id e faz backfill p/ default.

Idempotente e aditiva (Fase A do multi-tenant):
- resolve a loja default por slug (nunca por ID hardcoded);
- adiciona a coluna quando ausente;
- preenche apenas usuarios com store_ref_id IS NULL (preserva vinculos existentes);
- cria indice;
- garante a FK nomeada ON DELETE RESTRICT apenas no PostgreSQL (segura apos execucao parcial);
- nao reconstroi SQLite legado;
- valida nulos/orfaos e executa numa transacao unica (erro -> saida nao-zero).
Nao aplica NOT NULL nesta fase.
"""

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.store import Store  # noqa: E402

DEFAULT_STORE_SLUG = "default"
TABLE = "users"
INDEX_NAME = "ix_users_store_ref_id"
CONSTRAINT_NAME = "fk_users_store_ref_id_stores"


def _ensure_targets_exist(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    missing = sorted({"stores", TABLE} - existing)
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            f"Tabelas ausentes: {names}. "
            "Execute add_store_foundation.py e crie a tabela users antes desta migration."
        )


def _resolve_default_store_id(connection) -> int:
    store_id = connection.execute(
        select(Store.id).where(Store.slug == DEFAULT_STORE_SLUG)
    ).scalar_one_or_none()
    if store_id is None:
        raise RuntimeError(
            f"Loja default (slug={DEFAULT_STORE_SLUG!r}) ausente; "
            "execute add_store_foundation.py antes desta migration."
        )
    return int(store_id)


def _ensure_column(connection) -> None:
    columns = {column["name"] for column in inspect(connection).get_columns(TABLE)}
    if "store_ref_id" in columns:
        print(f"[SKIP] {TABLE}.store_ref_id")
        return
    connection.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN store_ref_id INTEGER"))
    print(f"[ADD] {TABLE}.store_ref_id")


def _backfill_and_validate(connection, default_store_id: int) -> None:
    result = connection.execute(
        text(f"UPDATE {TABLE} SET store_ref_id = :store_id WHERE store_ref_id IS NULL"),
        {"store_id": default_store_id},
    )
    if result.rowcount:
        print(f"[BACKFILL] {TABLE}: {result.rowcount} linha(s)")

    null_count = connection.execute(
        text(f"SELECT COUNT(*) FROM {TABLE} WHERE store_ref_id IS NULL")
    ).scalar_one()
    orphan_count = connection.execute(
        text(
            f"SELECT COUNT(*) FROM {TABLE} AS target "
            "LEFT JOIN stores ON stores.id = target.store_ref_id "
            "WHERE target.store_ref_id IS NOT NULL AND stores.id IS NULL"
        )
    ).scalar_one()
    if null_count or orphan_count:
        raise RuntimeError(
            f"Validacao falhou para {TABLE}: "
            f"{null_count} nulo(s), {orphan_count} referencia(s) orfa(s)."
        )


def _ensure_index(connection) -> None:
    connection.execute(text(f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON {TABLE} (store_ref_id)"))


def _ensure_postgres_fk(connection) -> None:
    if connection.dialect.name != "postgresql":
        return
    foreign_keys = inspect(connection).get_foreign_keys(TABLE)
    has_fk = any(
        fk.get("constrained_columns") == ["store_ref_id"]
        and fk.get("referred_table") == "stores"
        and fk.get("referred_columns") == ["id"]
        for fk in foreign_keys
    )
    if has_fk:
        print(f"[SKIP] FK {TABLE}.store_ref_id")
        return
    connection.execute(
        text(
            f"ALTER TABLE {TABLE} ADD CONSTRAINT {CONSTRAINT_NAME} "
            "FOREIGN KEY (store_ref_id) REFERENCES stores(id) ON DELETE RESTRICT"
        )
    )
    print(f"[ADD] {CONSTRAINT_NAME}")


def migrate() -> None:
    """Aplica a associacao usuario->loja numa transacao/conexao unica."""
    with db.engine.begin() as connection:
        _ensure_targets_exist(connection)
        default_store_id = _resolve_default_store_id(connection)
        _ensure_column(connection)
        _backfill_and_validate(connection, default_store_id)
        _ensure_index(connection)
        _ensure_postgres_fk(connection)

    print("[SUCCESS] users.store_ref_id aplicado")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
