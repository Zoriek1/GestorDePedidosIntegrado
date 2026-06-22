# -*- coding: utf-8 -*-
"""Adiciona CPF/CNPJ e UF usados pelo cadastro fiscal no Bling."""

from sqlalchemy import inspect

from app import create_app, db


def add_column_if_missing(table: str, column: str, definition: str) -> None:
    existing = {item["name"] for item in inspect(db.engine).get_columns(table)}
    if column in existing:
        print(f"[SKIP] {table}.{column} ja existe")
        return

    sql = f"ALTER TABLE {table} ADD COLUMN {column} {definition} NULL"
    db.session.execute(db.text(sql))
    db.session.commit()
    print(f"[OK] {table}.{column} adicionada")


def run() -> bool:
    add_column_if_missing("clientes", "cpf_cnpj", "VARCHAR(14)")
    add_column_if_missing("pedidos", "cpf_cnpj", "VARCHAR(14)")
    add_column_if_missing("pedidos", "uf", "VARCHAR(2)")
    return True


if __name__ == "__main__":
    with create_app().app_context():
        try:
            run()
        except Exception:
            db.session.rollback()
            raise
