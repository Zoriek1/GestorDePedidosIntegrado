# -*- coding: utf-8 -*-
"""
Migration: limpar token/status de leads que não são evento WhatsApp.

Motivação:
- token_rastreio/token_valido só fazem sentido para `event = whatsapp_click`
- registros antigos de outros eventos podem ter ficado como inválidos/pendentes
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def normalize_non_whatsapp_leads_tokens():
    with app.app_context():
        inspector = db.inspect(db.engine)
        if "leads" not in inspector.get_table_names():
            print("[SKIP] Tabela leads não existe")
            return

        try:
            result_tokens = db.session.execute(
                db.text(
                    """
                    UPDATE leads
                       SET token_rastreio = NULL,
                           token_valido = NULL
                     WHERE COALESCE(event, '') <> 'whatsapp_click'
                       AND (token_rastreio IS NOT NULL OR token_valido IS NOT NULL)
                    """
                )
            )
            result_status = db.session.execute(
                db.text(
                    """
                    UPDATE leads
                       SET status = NULL
                     WHERE COALESCE(event, '') <> 'whatsapp_click'
                       AND status = 'pendente_whatsapp'
                    """
                )
            )
            db.session.commit()
            print(
                "[OK] Limpeza aplicada: "
                f"tokens={result_tokens.rowcount}, status={result_status.rowcount}"
            )
        except Exception as e:
            db.session.rollback()
            print(f"[ERRO] Falha ao normalizar leads não-WhatsApp: {e}")


if __name__ == "__main__":
    normalize_non_whatsapp_leads_tokens()
