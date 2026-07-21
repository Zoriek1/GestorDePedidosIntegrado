# -*- coding: utf-8 -*-
"""F6/E0: cria integration_validation_log para o grid de Integracoes.

Tabela que armazena o historico de validacoes por canal/campo da loja
autenticada. Cada PATCH num campo apaga o log daquele canal (forca o status
a voltar para "salvo mas nao validado" ate nova chamada de validate).

Idempotente: cria a tabela/indices/FKs apenas quando nao existem.
"""

import sys
from pathlib import Path

from sqlalchemy import inspect, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.integration_validation_log import (  # noqa: E402
    IntegrationValidationLog,
)

TABLE = "integration_validation_log"


def _postgres_fk(connection) -> None:
    fks = inspect(connection).get_foreign_keys(TABLE)
    if any(fk.get("constrained_columns") == ["store_ref_id"] for fk in fks):
        return
    connection.execute(
        text(
            f"ALTER TABLE {TABLE} ADD CONSTRAINT fk_{TABLE}_store_ref_id_stores "
            "FOREIGN KEY (store_ref_id) REFERENCES stores(id) ON DELETE CASCADE"
        )
    )


def _sqlite_rebuild_if_needed(connection) -> None:
    fks = inspect(connection).get_foreign_keys(TABLE)
    if any(fk.get("constrained_columns") == ["store_ref_id"] for fk in fks):
        return

    indexes = [
        index
        for index in inspect(connection).get_indexes(TABLE)
        if index.get("name") and index.get("column_names")
    ]
    old = f"{TABLE}__e0_legacy"
    connection.execute(text(f"ALTER TABLE {TABLE} RENAME TO {old}"))
    for index in indexes:
        connection.execute(text(f'DROP INDEX IF EXISTS "{index["name"]}"'))

    IntegrationValidationLog.__table__.create(connection, checkfirst=False)
    old_columns = {column["name"] for column in inspect(connection).get_columns(old)}
    columns = [c.name for c in IntegrationValidationLog.__table__.columns if c.name in old_columns]
    joined = ", ".join(columns)
    connection.execute(text(f"INSERT INTO {TABLE} ({joined}) SELECT {joined} FROM {old}"))
    connection.execute(text(f"DROP TABLE {old}"))

    current_names = {index.get("name") for index in inspect(connection).get_indexes(TABLE)}
    for index in indexes:
        name = index["name"]
        if name in current_names:
            continue
        columns_sql = ", ".join(f'"{column}"' for column in index["column_names"])
        unique = "UNIQUE " if index.get("unique") else ""
        connection.execute(text(f'CREATE {unique}INDEX "{name}" ON {TABLE} ({columns_sql})'))


def _migrate_connection(connection) -> None:
    existing = set(inspect(connection).get_table_names())
    if "stores" not in existing:
        raise RuntimeError("Tabela 'stores' ausente; execute add_store_foundation.py antes.")

    if TABLE in existing:
        # Tabela ja existe; garante indices/FKs e sai.
        connection.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_store_ref_id " f"ON {TABLE} (store_ref_id)"
            )
        )
        connection.execute(
            text(f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_channel " f"ON {TABLE} (channel)")
        )
        connection.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_validated_at " f"ON {TABLE} (validated_at)"
            )
        )
        connection.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_store_channel_time "
                f"ON {TABLE} (store_ref_id, channel, validated_at DESC)"
            )
        )
    else:
        IntegrationValidationLog.__table__.create(connection, checkfirst=True)
        connection.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_store_channel_time "
                f"ON {TABLE} (store_ref_id, channel, validated_at DESC)"
            )
        )

    if connection.dialect.name == "postgresql":
        _postgres_fk(connection)
    elif connection.dialect.name == "sqlite":
        _sqlite_rebuild_if_needed(connection)


def migrate() -> None:
    if db.engine.dialect.name == "sqlite":
        with db.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.exec_driver_sql("PRAGMA legacy_alter_table=ON")
            connection.commit()
            with connection.begin():
                _migrate_connection(connection)
            connection.exec_driver_sql("PRAGMA legacy_alter_table=OFF")
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
    else:
        with db.engine.begin() as connection:
            _migrate_connection(connection)
    print("[SUCCESS] integration_validation_log pronta")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
