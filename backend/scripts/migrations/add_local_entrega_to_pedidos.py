# -*- coding: utf-8 -*-
"""
Migration: adiciona colunas de tipo/detalhe do local de entrega à tabela 'pedidos'.

Colunas:
  - tipo_local    VARCHAR(20) NULL DEFAULT 'casa'  — casa | predio | comercial
  - nome_local    VARCHAR(200) NULL                — prédio/condomínio ou estabelecimento
  - apartamento   VARCHAR(20) NULL
  - bloco         VARCHAR(20) NULL
  - torre         VARCHAR(20) NULL
  - andar         VARCHAR(20) NULL

Idempotente — só adiciona o que ainda não existe. Detecta postgres/sqlite.

Uso (VPS):
    docker compose exec backend python scripts/migrations/add_local_entrega_to_pedidos.py
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
        "ALTER TABLE pedidos ADD COLUMN tipo_local VARCHAR(20) DEFAULT 'casa'",
        "ALTER TABLE pedidos ADD COLUMN tipo_local VARCHAR(20) DEFAULT 'casa'",
        "tipo_local",
    )
    _add_column(
        "ALTER TABLE pedidos ADD COLUMN nome_local VARCHAR(200) NULL",
        "ALTER TABLE pedidos ADD COLUMN nome_local VARCHAR(200) NULL",
        "nome_local",
    )
    _add_column(
        "ALTER TABLE pedidos ADD COLUMN apartamento VARCHAR(20) NULL",
        "ALTER TABLE pedidos ADD COLUMN apartamento VARCHAR(20) NULL",
        "apartamento",
    )
    _add_column(
        "ALTER TABLE pedidos ADD COLUMN bloco VARCHAR(20) NULL",
        "ALTER TABLE pedidos ADD COLUMN bloco VARCHAR(20) NULL",
        "bloco",
    )
    _add_column(
        "ALTER TABLE pedidos ADD COLUMN torre VARCHAR(20) NULL",
        "ALTER TABLE pedidos ADD COLUMN torre VARCHAR(20) NULL",
        "torre",
    )
    _add_column(
        "ALTER TABLE pedidos ADD COLUMN andar VARCHAR(20) NULL",
        "ALTER TABLE pedidos ADD COLUMN andar VARCHAR(20) NULL",
        "andar",
    )
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: pedidos.tipo_local / nome_local / apartamento / bloco / torre / andar")
    print("=" * 60)
    with create_app().app_context():
        try:
            run()
        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise
    print("=" * 60)
