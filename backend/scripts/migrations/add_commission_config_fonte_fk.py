# -*- coding: utf-8 -*-
"""
Migration: adiciona commission_config.fonte_pedido_id e backfill de source legado.

Uso:
  cd backend
  python scripts/migrations/add_commission_config_fonte_fk.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def column_exists(table: str, col: str) -> bool:
    from app import db
    from sqlalchemy import inspect as sa_inspect

    return col in [c["name"] for c in sa_inspect(db.engine).get_columns(table)]


def table_exists(table: str) -> bool:
    from app import db
    from sqlalchemy import inspect as sa_inspect

    return table in sa_inspect(db.engine).get_table_names()


def migrate():
    from app import db
    from app.models.fonte_pedido import FontePedido
    from app.models.user import CommissionConfig
    from app.services.commission_service import map_fonte_to_source

    print("[MIGRATION] add_commission_config_fonte_fk")

    if not table_exists("commission_config"):
        print("[MIGRATION] Tabela commission_config não encontrada. Nada a fazer.")
        return

    dialect = db.engine.dialect.name

    # 1) Schema: adicionar coluna
    if not column_exists("commission_config", "fonte_pedido_id"):
        print("[MIGRATION] Adicionando coluna fonte_pedido_id...")
        if dialect == "postgresql":
            db.session.execute(
                db.text(
                    """
                    ALTER TABLE commission_config
                    ADD COLUMN IF NOT EXISTS fonte_pedido_id INTEGER
                    REFERENCES fontes_pedido(id)
                    """
                )
            )
        else:
            # SQLite: FK em ALTER é limitado; mantemos coluna e relacionamento lógico.
            db.session.execute(
                db.text("ALTER TABLE commission_config ADD COLUMN fonte_pedido_id INTEGER")
            )
        db.session.commit()
        print("[MIGRATION] Coluna adicionada.")
    else:
        print("[MIGRATION] Coluna fonte_pedido_id já existe.")

    # 2) Índice
    try:
        db.session.execute(
            db.text(
                "CREATE INDEX IF NOT EXISTS ix_commission_config_fonte_pedido_id "
                "ON commission_config(fonte_pedido_id)"
            )
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[MIGRATION] Aviso ao criar índice: {e}")

    # 3) Backfill source -> fonte_pedido_id
    fontes = FontePedido.query.filter_by(ativo=True).all()
    slug_to_id = {}
    for fonte in fontes:
        slug = map_fonte_to_source(fonte.nome or "")
        if slug:
            slug_to_id[slug] = fonte.id

    updated = 0
    warnings = []
    configs = CommissionConfig.query.filter(CommissionConfig.fonte_pedido_id.is_(None)).all()
    for cfg in configs:
        slug = map_fonte_to_source(cfg.source or "")
        fonte_id = slug_to_id.get(slug)
        if fonte_id:
            cfg.fonte_pedido_id = fonte_id
            updated += 1
        else:
            warnings.append(
                f"[MIGRATION][WARN] Sem mapeamento para source='{cfg.source}' (config_id={cfg.id}, user_id={cfg.user_id})"
            )

    db.session.commit()
    print(f"[MIGRATION] Backfill concluído. {updated} config(s) atualizadas.")
    if warnings:
        print(f"[MIGRATION] {len(warnings)} aviso(s) de mapeamento legado não resolvido:")
        for msg in warnings:
            print(msg)


if __name__ == "__main__":
    from app import create_app, db

    app = create_app()
    with app.app_context():
        migrate()
