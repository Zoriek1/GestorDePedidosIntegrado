# -*- coding: utf-8 -*-
"""
Migration: role entregador + crédito da taxa_entrega no ledger.

- pedidos: entregador_id, delivery_assigned_at, delivery_completed_at
- ledger_entry: delivery_pedido_id + índice único parcial uq_ledger_delivery_pedido_active

Uso
---
    cd backend && python scripts/migrations/add_entregador_and_delivery_credit.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db


def is_sqlite() -> bool:
    return db.engine.dialect.name == "sqlite"


def column_exists(table: str, col: str) -> bool:
    from sqlalchemy import inspect as sa_inspect

    insp = sa_inspect(db.engine)
    return col in [c["name"] for c in insp.get_columns(table)]


def index_exists(table: str, name: str) -> bool:
    from sqlalchemy import inspect as sa_inspect

    insp = sa_inspect(db.engine)
    return any(ix.get("name") == name for ix in insp.get_indexes(table))


def add_column_if_missing(table: str, col: str, ddl_type: str, fk: str | None = None) -> None:
    if column_exists(table, col):
        print(f"[SKIP] {table}.{col} já existe")
        return
    fk_sql = f" REFERENCES {fk}" if fk else ""
    db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl_type}{fk_sql}"))
    db.session.commit()
    print(f"[OK]   {table}.{col} criado")


def migrate() -> None:
    print(f"[MIGRATION] add_entregador_and_delivery_credit (banco: {db.engine.dialect.name})")

    # Postgres usa TIMESTAMP; SQLite aceita TIMESTAMP também (alias de DATETIME).
    ts_type = "TIMESTAMP NULL"

    # 1) Colunas em pedidos
    add_column_if_missing("pedidos", "entregador_id", "INTEGER NULL", fk="users(id)")
    add_column_if_missing("pedidos", "delivery_assigned_at", ts_type)
    add_column_if_missing("pedidos", "delivery_completed_at", ts_type)

    # Index auxiliar em entregador_id (não-único) para acelerar filtros
    if not index_exists("pedidos", "ix_pedidos_entregador_id"):
        db.session.execute(
            db.text("CREATE INDEX IF NOT EXISTS ix_pedidos_entregador_id ON pedidos(entregador_id)")
        )
        db.session.commit()
        print("[OK]   ix_pedidos_entregador_id criado")

    # 2) Coluna em ledger_entry
    add_column_if_missing("ledger_entry", "delivery_pedido_id", "INTEGER NULL", fk="pedidos(id)")

    # 3) Índice único parcial para idempotência do CREDIT do entregador
    if index_exists("ledger_entry", "uq_ledger_delivery_pedido_active"):
        print("[SKIP] uq_ledger_delivery_pedido_active já existe")
    else:
        if is_sqlite():
            ddl = (
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_delivery_pedido_active "
                "ON ledger_entry(delivery_pedido_id) "
                "WHERE voided=0 AND delivery_pedido_id IS NOT NULL"
            )
            db.session.execute(db.text(ddl))
            db.session.commit()
        else:
            ddl = (
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_delivery_pedido_active "
                "ON ledger_entry(delivery_pedido_id) "
                "WHERE voided = FALSE AND delivery_pedido_id IS NOT NULL"
            )
            with db.engine.connect() as conn:
                conn.execute(db.text("SET lock_timeout = '5s'"))
                conn.execute(db.text(ddl))
                conn.commit()
        print("[OK]   uq_ledger_delivery_pedido_active criado")

    print("[OK] Migration concluída")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
