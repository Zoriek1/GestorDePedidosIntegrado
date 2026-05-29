# -*- coding: utf-8 -*-
"""
Migration: adiciona colunas de slot de entrega à tabela 'pedidos'.

Colunas:
  - slot_inicio    TIME NULL      — slot alocado (janela de 1h)
  - slot_deadline  TIME NULL      — deadline visível ao cliente
  - is_expressa    BOOLEAN NOT NULL DEFAULT FALSE

Idempotente — só adiciona o que ainda não existe. Detecta postgres/sqlite.

Uso (VPS):
    docker compose exec backend python scripts/migrations/add_slot_entrega_to_pedidos.py
"""
from app import create_app, db


def column_exists(table: str, col: str) -> bool:
    from sqlalchemy import inspect

    return col in [c["name"] for c in inspect(db.engine).get_columns(table)]


def _add_column(sql_postgres: str, sql_sqlite: str, col_name: str) -> None:
    if column_exists("pedidos", col_name):
        print(f"[OK] Coluna '{col_name}' já existe — pulando.")
        return
    sql = sql_postgres if db.engine.dialect.name == "postgresql" else sql_sqlite
    print(f"[INFO] Executando: {sql}")
    db.session.execute(db.text(sql))
    db.session.commit()
    print(f"[OK] Coluna '{col_name}' adicionada.")


def run() -> bool:
    print(f"[INFO] Dialeto: {db.engine.dialect.name}")

    _add_column(
        "ALTER TABLE pedidos ADD COLUMN slot_inicio TIME NULL",
        "ALTER TABLE pedidos ADD COLUMN slot_inicio TIME NULL",
        "slot_inicio",
    )
    _add_column(
        "ALTER TABLE pedidos ADD COLUMN slot_deadline TIME NULL",
        "ALTER TABLE pedidos ADD COLUMN slot_deadline TIME NULL",
        "slot_deadline",
    )
    _add_column(
        "ALTER TABLE pedidos ADD COLUMN is_expressa BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE pedidos ADD COLUMN is_expressa BOOLEAN NOT NULL DEFAULT 0",
        "is_expressa",
    )
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: pedidos.slot_inicio / slot_deadline / is_expressa")
    print("=" * 60)
    with create_app().app_context():
        try:
            run()
        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise
    print("=" * 60)
