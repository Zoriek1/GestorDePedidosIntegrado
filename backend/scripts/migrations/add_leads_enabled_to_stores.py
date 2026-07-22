# -*- coding: utf-8 -*-
"""Adiciona `stores.leads_enabled` — módulo de Leads habilitado por loja.

A captação pública de leads ainda resolve sempre a loja `default`
(`resolve_public_store_id` em app/services/auth_context.py), porque não existe
mapeamento domínio→loja. Enquanto isso, um lead da landing page de outro cliente
cairia na loja 1.

Em vez de deixar essa armadilha ligada, o módulo de Leads passa a ser explícito
por loja: desligado por padrão, ligado apenas na `default`. Assim "todo lead vai
para a loja 1" deixa de ser um defeito e vira a regra vigente. Quando o
mapeamento existir, basta um UPDATE para liberar o módulo a outras lojas.

Idempotente: rodar várias vezes é seguro.
"""

import sys
from pathlib import Path

from sqlalchemy import inspect, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402

TABLE = "stores"
COLUMN = "leads_enabled"
DEFAULT_SLUG = "default"


def _migrate_connection(connection) -> None:
    if TABLE not in set(inspect(connection).get_table_names()):
        raise RuntimeError(f"Tabela {TABLE} ausente; rode add_store_foundation.py antes")

    columns = {column["name"] for column in inspect(connection).get_columns(TABLE)}
    if COLUMN in columns:
        print(f"[SKIP] {TABLE}.{COLUMN} já existe")
        return

    # DEFAULT false no ALTER garante que as linhas existentes nasçam desligadas
    # sem uma segunda passada de UPDATE.
    connection.execute(
        text(f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} BOOLEAN NOT NULL DEFAULT FALSE")
    )
    print(f"[MIGRATE] {TABLE}.{COLUMN} criada (padrão: desligado)")

    result = connection.execute(
        text(f"UPDATE {TABLE} SET {COLUMN} = TRUE WHERE slug = :slug"),
        {"slug": DEFAULT_SLUG},
    )
    if result.rowcount:
        print(f"[MIGRATE] Loja '{DEFAULT_SLUG}' -> {COLUMN}=true")
    else:
        print(f"[AVISO] Loja '{DEFAULT_SLUG}' não encontrada; nenhuma loja com Leads ativo")


def migrate() -> None:
    if db.engine.dialect.name == "sqlite":
        with db.engine.connect() as connection:
            with connection.begin():
                _migrate_connection(connection)
    else:
        with db.engine.begin() as connection:
            _migrate_connection(connection)
    print("[SUCCESS] stores.leads_enabled aplicado")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
