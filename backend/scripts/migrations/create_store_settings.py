# -*- coding: utf-8 -*-
"""Cria store_settings e importa a configuracao legada do tenant default."""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402
from app.models.store_setting import StoreSetting  # noqa: E402
from app.services.integration_settings_service import (  # noqa: E402
    default_store,
    settings_from_environment,
)


def _ensure_columns() -> None:
    """Adiciona colunas que o ORM define mas que a tabela ainda não tem.

    Cobre deploys onde a tabela já existia de uma versão anterior sem certas
    colunas (ex: mercado_pago_*, taxa_cartao_*, endereco_floricultura, loja_cep).
    """
    from sqlalchemy import inspect, text

    table_name = StoreSetting.__tablename__
    inspector = inspect(db.engine)
    existing = {col["name"] for col in inspector.get_columns(table_name)}

    added = 0
    for col in StoreSetting.__table__.columns:
        if col.name not in existing:
            # Determina DEFAULT SQL a partir do Python default
            python_default = col.default.arg if col.default else None
            col_type = col.type.compile(db.engine.dialect)
            parts = [f"ADD COLUMN {col.name} {col_type}"]
            if col.nullable:
                parts.append("NULL")
            else:
                parts.append("NOT NULL")
                if python_default is not None:
                    if isinstance(python_default, bool):
                        parts.append(f"DEFAULT {'TRUE' if python_default else 'FALSE'}")
                    elif isinstance(python_default, (int, float)):
                        parts.append(f"DEFAULT {python_default}")
                else:
                    # Sem default e NOT NULL — colunas novas recebem valor sentinela
                    if "String" in col_type or "Text" in col_type:
                        parts.append("DEFAULT ''")
                    elif "Boolean" in col_type:
                        parts.append("DEFAULT FALSE")
                    elif "Float" in col_type or "Integer" in col_type:
                        parts.append("DEFAULT 0")
            ddl = f"ALTER TABLE {table_name} {' '.join(parts)}"
            db.session.execute(text(ddl))
            added += 1
            print(f"[MIGRATE] {table_name}.{col.name} adicionada")

    if added:
        db.session.commit()
        print(f"[MIGRATE] {table_name}: {added} coluna(s) adicionada(s)")


def migrate() -> None:
    StoreSetting.__table__.create(bind=db.engine, checkfirst=True)
    _ensure_columns()
    store = default_store()
    existing = StoreSetting.query.filter_by(store_ref_id=store.id).first()
    if existing:
        print("[SKIP] store_settings do tenant default")
        return
    try:
        db.session.add(settings_from_environment(store.id))
        db.session.commit()
        print("[ADD] store_settings do tenant default importada do ambiente")
    except Exception:
        db.session.rollback()
        raise


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()
