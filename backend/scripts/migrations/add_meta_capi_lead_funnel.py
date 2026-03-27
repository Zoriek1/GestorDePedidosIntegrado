# -*- coding: utf-8 -*-
"""
Migration: colunas Meta no lead + tabela meta_capi_lead_outbox.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def migrate():
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        if "leads" in tables:
            cols = {c["name"] for c in inspector.get_columns("leads")}
            stmts = []
            if "meta_event_id_contact" not in cols:
                stmts.append("ALTER TABLE leads ADD COLUMN meta_event_id_contact VARCHAR(100) NULL")
            if "meta_event_id_lead" not in cols:
                stmts.append("ALTER TABLE leads ADD COLUMN meta_event_id_lead VARCHAR(100) NULL")
            if "client_user_agent" not in cols:
                stmts.append("ALTER TABLE leads ADD COLUMN client_user_agent VARCHAR(512) NULL")
            for sql in stmts:
                print(f"[MIGRATION] {sql}")
                db.session.execute(db.text(sql))
            if stmts:
                db.session.commit()
                print("[OK] Colunas leads atualizadas")
            else:
                print("[SKIP] Colunas Meta em leads já existem")
        else:
            print("[SKIP] Tabela leads não existe")

        if "meta_capi_lead_outbox" in tables:
            print("[SKIP] Tabela meta_capi_lead_outbox já existe")
        else:
            print("[CREATE] meta_capi_lead_outbox...")
            from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox

            MetaCapiLeadOutbox.__table__.create(db.engine)
            print(f"[OK] Tabela criada ({db.engine.dialect.name})")


if __name__ == "__main__":
    migrate()
