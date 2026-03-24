# -*- coding: utf-8 -*-
"""
Migration: adicionar token_rastreio, token_valido e status na tabela leads.

Regras:
- token_rastreio: índice não-único (remove índice único legado se existir)
- token_valido: booleano para resultado da validação de checksum
- status: estado operacional do lead
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def add_token_status_to_leads():
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        if "leads" not in existing_tables:
            print("[SKIP] Tabela leads não existe")
            return

        existing_columns = [col["name"] for col in inspector.get_columns("leads")]
        dialect = db.engine.dialect.name

        print("[MIGRATION] Atualizando tabela leads (token_rastreio/token_valido/status)...")

        if "token_rastreio" not in existing_columns:
            try:
                db.session.execute(
                    db.text("ALTER TABLE leads ADD COLUMN token_rastreio VARCHAR(64) NULL")
                )
                db.session.commit()
                print("[OK] Coluna 'token_rastreio' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Falha ao adicionar 'token_rastreio': {e}")
        else:
            print("[SKIP] Coluna 'token_rastreio' já existe")

        if "status" not in existing_columns:
            try:
                db.session.execute(db.text("ALTER TABLE leads ADD COLUMN status VARCHAR(50) NULL"))
                db.session.commit()
                print("[OK] Coluna 'status' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Falha ao adicionar 'status': {e}")
        else:
            print("[SKIP] Coluna 'status' já existe")

        if "token_valido" not in existing_columns:
            try:
                db.session.execute(
                    db.text("ALTER TABLE leads ADD COLUMN token_valido BOOLEAN NULL")
                )
                db.session.commit()
                print("[OK] Coluna 'token_valido' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Falha ao adicionar 'token_valido': {e}")
        else:
            print("[SKIP] Coluna 'token_valido' já existe")

        try:
            db.session.execute(
                db.text("UPDATE leads SET status = 'pendente_whatsapp' WHERE status IS NULL")
            )
            db.session.execute(
                db.text("UPDATE leads SET token_valido = 0 WHERE token_valido IS NULL")
            )
            db.session.commit()
            print("[OK] Backfill de status/token_valido aplicado")
        except Exception as e:
            db.session.rollback()
            print(f"[ERRO] Falha ao aplicar backfill legado: {e}")

        # Índice de status
        try:
            if dialect == "sqlite":
                db.session.execute(
                    db.text("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
                )
            else:
                db.session.execute(db.text("CREATE INDEX idx_leads_status ON leads(status)"))
            db.session.commit()
            print("[OK] Índice de status garantido")
        except Exception as e:
            db.session.rollback()
            print(f"[WARN] Não foi possível criar índice de status (pode já existir): {e}")

        # Remover índice único legado (se existir) e garantir índice não-único.
        try:
            if dialect == "sqlite":
                db.session.execute(
                    db.text(
                        "DROP INDEX IF EXISTS uq_leads_token_rastreio"
                    )
                )
            else:
                db.session.execute(
                    db.text(
                        "DROP INDEX IF EXISTS uq_leads_token_rastreio"
                    )
                )
            db.session.commit()
            print("[OK] Índice único legado de token_rastreio removido (se existia)")
        except Exception as e:
            db.session.rollback()
            print(f"[WARN] Não foi possível remover índice único legado: {e}")

        try:
            if dialect == "sqlite":
                db.session.execute(
                    db.text(
                        "CREATE INDEX IF NOT EXISTS ix_leads_token_rastreio ON leads(token_rastreio)"
                    )
                )
            else:
                db.session.execute(
                    db.text("CREATE INDEX ix_leads_token_rastreio ON leads(token_rastreio)")
                )
            db.session.commit()
            print("[OK] Índice não-único de token_rastreio garantido")
        except Exception as e:
            db.session.rollback()
            print(f"[WARN] Não foi possível criar índice de token_rastreio (pode já existir): {e}")

        print("[OK] Migration concluída")


if __name__ == "__main__":
    add_token_status_to_leads()
