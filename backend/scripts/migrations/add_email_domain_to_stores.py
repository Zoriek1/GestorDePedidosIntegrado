# -*- coding: utf-8 -*-
"""Adiciona `stores.email_domain` — o domínio que resolve o tenant no login.

No multi-tenant o login precisa saber a loja ANTES de procurar o usuário, senão
dois tenants com o mesmo e-mail logariam na conta errada. A regra escolhida é
resolver pelo domínio: `maria@floriculturax.com` -> loja com esse `email_domain`.

Backfill: a loja `default` recebe o domínio dominante entre seus usuários ATIVOS
(hoje `planteumaflor.com`), para que todos os logins existentes continuem
funcionando sem intervenção. Se os ativos tiverem domínios divergentes, a coluna
fica NULL e o login segue no caminho de compatibilidade (busca global).

Idempotente: rodar várias vezes é seguro.
"""

import sys
from pathlib import Path

from sqlalchemy import inspect, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402

TABLE = "stores"
COLUMN = "email_domain"
INDEX = "ix_stores_email_domain"
DEFAULT_SLUG = "default"


def _dominant_active_domain(connection) -> str | None:
    """Domínio dos usuários ativos da loja default, se for único."""
    rows = connection.execute(
        text(
            "SELECT DISTINCT LOWER(SUBSTR(email, INSTR(email, '@') + 1)) FROM users "
            "WHERE is_active AND store_ref_id = (SELECT id FROM stores WHERE slug = :slug)"
        )
        if connection.dialect.name == "sqlite"
        else text(
            "SELECT DISTINCT LOWER(SPLIT_PART(email, '@', 2)) FROM users "
            "WHERE is_active AND store_ref_id = (SELECT id FROM stores WHERE slug = :slug)"
        ),
        {"slug": DEFAULT_SLUG},
    ).fetchall()
    domains = [row[0] for row in rows if row[0]]
    if len(domains) == 1:
        return domains[0]
    if len(domains) > 1:
        print(f"[SKIP] Backfill: loja default tem domínios divergentes ({', '.join(domains)})")
    return None


def _migrate_connection(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    if TABLE not in existing:
        raise RuntimeError(f"Tabela {TABLE} ausente; rode add_store_foundation.py antes")

    columns = {column["name"] for column in inspect(connection).get_columns(TABLE)}
    if COLUMN not in columns:
        connection.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} VARCHAR(120)"))
        print(f"[MIGRATE] {TABLE}.{COLUMN} criada")
    else:
        print(f"[SKIP] {TABLE}.{COLUMN} já existe")

    connection.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX} ON {TABLE} ({COLUMN})"))

    if "users" not in existing:
        return

    already = connection.execute(
        text(f"SELECT {COLUMN} FROM {TABLE} WHERE slug = :slug"), {"slug": DEFAULT_SLUG}
    ).scalar_one_or_none()
    if already:
        print(f"[SKIP] Loja default já tem {COLUMN}={already}")
        return

    domain = _dominant_active_domain(connection)
    if not domain:
        return

    connection.execute(
        text(f"UPDATE {TABLE} SET {COLUMN} = :domain WHERE slug = :slug"),
        {"domain": domain, "slug": DEFAULT_SLUG},
    )
    print(f"[MIGRATE] Loja default -> {COLUMN}={domain}")


def migrate() -> None:
    if db.engine.dialect.name == "sqlite":
        with db.engine.connect() as connection:
            with connection.begin():
                _migrate_connection(connection)
    else:
        with db.engine.begin() as connection:
            _migrate_connection(connection)
    print("[SUCCESS] stores.email_domain aplicado")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
