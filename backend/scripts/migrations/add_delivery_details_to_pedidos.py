# -*- coding: utf-8 -*-
"""
Migration: adiciona detalhes de local de entrega em pedidos.

Campos opcionais, sem backfill automatico:
  - tipo_local, nome_local, apto, bloco, torre, andar
  - quadra, lote, complemento
"""

from app import create_app, db


def column_exists(table: str, col: str) -> bool:
    from sqlalchemy import inspect

    return col in [c["name"] for c in inspect(db.engine).get_columns(table)]


def add_column_if_missing(col_name: str, col_type: str) -> None:
    if column_exists("pedidos", col_name):
        print(f"[OK] Coluna '{col_name}' ja existe - pulando.")
        return

    sql = f"ALTER TABLE pedidos ADD COLUMN {col_name} {col_type} NULL"
    print(f"[INFO] Executando: {sql}")
    db.session.execute(db.text(sql))
    db.session.commit()
    print(f"[OK] Coluna '{col_name}' adicionada.")


def run() -> bool:
    print(f"[INFO] Dialeto: {db.engine.dialect.name}")
    columns = [
        ("tipo_local", "VARCHAR(20)"),
        ("nome_local", "VARCHAR(120)"),
        ("apto", "VARCHAR(50)"),
        ("bloco", "VARCHAR(50)"),
        ("torre", "VARCHAR(50)"),
        ("andar", "VARCHAR(50)"),
        ("quadra", "VARCHAR(50)"),
        ("lote", "VARCHAR(50)"),
        ("complemento", "VARCHAR(100)"),
    ]
    for col_name, col_type in columns:
        add_column_if_missing(col_name, col_type)
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: pedidos delivery details")
    print("=" * 60)
    with create_app().app_context():
        try:
            run()
        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise
    print("=" * 60)
