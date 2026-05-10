# -*- coding: utf-8 -*-
"""
Migration: adiciona coluna 'cartao_impresso' (BOOLEAN) à tabela 'pedidos'.

Idempotente — pode ser rodado várias vezes sem efeito colateral.
Detecta SQLite vs PostgreSQL para emitir a sintaxe correta de DEFAULT.

Uso (VPS):
    docker compose exec backend python scripts/migrations/add_cartao_impresso_column.py
"""
from app import create_app, db


def column_exists(table: str, col: str) -> bool:
    from sqlalchemy import inspect

    return col in [c["name"] for c in inspect(db.engine).get_columns(table)]


def run() -> bool:
    if column_exists("pedidos", "cartao_impresso"):
        print("[OK] Coluna 'cartao_impresso' já existe — nada a fazer.")
        return True

    dialect = db.engine.dialect.name
    if dialect == "postgresql":
        sql = "ALTER TABLE pedidos ADD COLUMN cartao_impresso BOOLEAN NOT NULL DEFAULT FALSE"
    else:
        sql = "ALTER TABLE pedidos ADD COLUMN cartao_impresso BOOLEAN NOT NULL DEFAULT 0"

    print(f"[INFO] Dialeto: {dialect}")
    print(f"[INFO] Executando: {sql}")
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] Coluna 'cartao_impresso' adicionada com sucesso.")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: pedidos.cartao_impresso")
    print("=" * 60)
    with create_app().app_context():
        try:
            run()
        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise
    print("=" * 60)
