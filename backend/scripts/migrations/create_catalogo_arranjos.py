# -*- coding: utf-8 -*-
"""
Migration: cria a tabela `catalogo_arranjos` (CAT-01).

Catálogo curado + promoção: tabela começa VAZIA (não semear cru de `produto`). A entrada
livre no pedido continua aceita; o catálogo só cresce por promoção explícita da florista.

Postgres: tabela + índice GIN trigram (pg_trgm — compartilhado com BUS-01) para sugestão
por similaridade. SQLite/dev: só a tabela (sugestão cai para substring LIKE).

Idempotente (IF NOT EXISTS).

Uso (VPS):
    docker compose exec backend python scripts/migrations/create_catalogo_arranjos.py
"""

from app import create_app, db


def run() -> bool:
    dialect = db.engine.dialect.name
    print(f"[INFO] Dialeto: {dialect}")

    if dialect == "postgresql":
        stmts = [
            "CREATE EXTENSION IF NOT EXISTS pg_trgm",
            "CREATE TABLE IF NOT EXISTS catalogo_arranjos ("
            " id serial PRIMARY KEY,"
            " nome text UNIQUE NOT NULL,"
            " usos int NOT NULL DEFAULT 1"
            ")",
            "CREATE INDEX IF NOT EXISTS idx_arranjo_trgm "
            "ON catalogo_arranjos USING gin (nome gin_trgm_ops)",
        ]
    else:
        stmts = [
            "CREATE TABLE IF NOT EXISTS catalogo_arranjos ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " nome TEXT UNIQUE NOT NULL,"
            " usos INTEGER NOT NULL DEFAULT 1"
            ")",
        ]

    for sql in stmts:
        print(f"[INFO] Executando: {sql[:70]}...")
        db.session.execute(db.text(sql))
        db.session.commit()
    print("[OK] Tabela catalogo_arranjos pronta.")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: catalogo_arranjos (CAT-01)")
    print("=" * 60)
    with create_app().app_context():
        try:
            run()
        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise
    print("=" * 60)
