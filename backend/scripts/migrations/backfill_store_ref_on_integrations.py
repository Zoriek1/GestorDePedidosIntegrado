# -*- coding: utf-8 -*-
"""Backfill de store_ref_id nas credenciais/instalações de integração (Fase B).

As colunas/FKs `nuvemshop_stores.store_ref_id` e `bling_credentials.store_ref_id`
já existem (add_store_foundation.py). Esta migration é defensiva e idempotente:
garante que quaisquer linhas residuais com `store_ref_id IS NULL` (ex.: instalações
criadas após a fundação e antes da Fase B) fiquem ligadas à loja `default`, para que
a resolução por FK funcione assim que uma segunda loja for criada.

Novas instalações OAuth já gravam `store_ref_id` a partir do state assinado.
Idempotente: só toca em linhas nulas; segunda execução é no-op.
"""

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.store import Store  # noqa: E402

DEFAULT_STORE_SLUG = "default"
TARGET_TABLES = ("nuvemshop_stores", "bling_credentials")


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


def _backfill_and_validate(connection, table: str, default_store_id: int) -> None:
    columns = {column["name"] for column in inspect(connection).get_columns(table)}
    if "store_ref_id" not in columns:
        raise RuntimeError(f"{table}.store_ref_id ausente; execute add_store_foundation.py antes.")

    result = connection.execute(
        text(f"UPDATE {table} SET store_ref_id = :store_id WHERE store_ref_id IS NULL"),
        {"store_id": default_store_id},
    )
    if result.rowcount:
        print(f"[BACKFILL] {table}: {result.rowcount} linha(s)")
    else:
        print(f"[SKIP] {table}: nada a preencher")

    orphan_count = connection.execute(
        text(
            f"SELECT COUNT(*) FROM {table} AS target "
            "LEFT JOIN stores ON stores.id = target.store_ref_id "
            "WHERE target.store_ref_id IS NOT NULL AND stores.id IS NULL"
        )
    ).scalar_one()
    if orphan_count:
        raise RuntimeError(f"Validacao falhou para {table}: {orphan_count} referencia(s) orfa(s).")


def migrate() -> None:
    with db.engine.begin() as connection:
        existing = set(inspect(connection).get_table_names())
        default_store_id = _resolve_default_store_id(connection)
        for table in TARGET_TABLES:
            if table not in existing:
                print(f"[SKIP] {table}: tabela ausente")
                continue
            _backfill_and_validate(connection, table, default_store_id)

    print("[SUCCESS] backfill de store_ref_id nas integrações aplicado")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
