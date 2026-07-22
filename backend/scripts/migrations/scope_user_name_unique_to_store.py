# -*- coding: utf-8 -*-
"""Troca a unicidade global de users.name por unicidade POR LOJA.

O índice antigo (`ux_users_name_active_ci`) era UNIQUE sobre LOWER(name) entre
usuários ativos, sem considerar a loja. No multi-tenant isso impede que duas
lojas tenham, cada uma, uma "Maria" ativa — o cadastro da segunda falha.

Esta migration apenas REMOVE o índice antigo. O novo, com escopo por loja
(`ux_users_store_name_active_ci`), é criado no boot por
`app/extensions.py::_ensure_user_name_unique_index`, que já traz a pré-checagem
de duplicados e o comportamento fail-safe.

Idempotente: rodar várias vezes é seguro.
"""

import sys
from pathlib import Path

from sqlalchemy import inspect, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402

TABLE = "users"
OLD_INDEX = "ux_users_name_active_ci"


def _migrate_connection(connection) -> None:
    if TABLE not in set(inspect(connection).get_table_names()):
        print(f"[SKIP] Tabela {TABLE} ausente")
        return

    existing = {index.get("name") for index in inspect(connection).get_indexes(TABLE)}
    if OLD_INDEX not in existing:
        print(f"[SKIP] {OLD_INDEX} já removido")
        return

    connection.execute(text(f'DROP INDEX IF EXISTS "{OLD_INDEX}"'))
    print(f"[MIGRATE] {OLD_INDEX} removido (unicidade de nome passa a ser por loja)")


def migrate() -> None:
    if db.engine.dialect.name == "sqlite":
        with db.engine.connect() as connection:
            with connection.begin():
                _migrate_connection(connection)
    else:
        with db.engine.begin() as connection:
            _migrate_connection(connection)
    print("[SUCCESS] unicidade de nome escopada por loja")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
