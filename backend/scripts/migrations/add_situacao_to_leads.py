# -*- coding: utf-8 -*-
"""
Migration: adiciona a coluna `situacao` em leads (funil por situação).

Objetivo
--------
`situacao` é um subestado operacional do lead **confirmado**
(`status='whatsapp_iniciado'`), marcado pelo operador:
`aguardando_resposta` | `orcamento_enviado` | `sem_resposta`.

Mora numa coluna separada de propósito: `status` continua intocado, então o
disparo do evento Meta `Lead` e o `_aggregate_lead_stats` (que dependem de
`status='whatsapp_iniciado'`) ficam protegidos. `situacao` nunca enfileira
nada no MetaCapiLeadOutbox.

Backfill
--------
Leads já confirmados (`status='whatsapp_iniciado'` sem `situacao`) recebem o
default `aguardando_resposta`, para entrarem no grupo "Em conversa" do painel.

Idempotente
-----------
Não duplica coluna/índice nem sobrescreve `situacao` já preenchida.

Uso
---
    docker compose exec backend python scripts/migrations/add_situacao_to_leads.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db


def column_exists(table: str, col: str) -> bool:
    from sqlalchemy import inspect

    return col in [c["name"] for c in inspect(db.engine).get_columns(table)]


def migrate():
    print(f"[MIGRATION] add_situacao_to_leads (banco: {db.engine.dialect.name})")

    if not column_exists("leads", "situacao"):
        db.session.execute(db.text("ALTER TABLE leads ADD COLUMN situacao VARCHAR(30) NULL"))
        db.session.commit()
        print("[MIGRATION]   coluna leads.situacao adicionada.")
    else:
        print("[MIGRATION]   coluna leads.situacao já existe.")

    # Índice (CREATE INDEX IF NOT EXISTS funciona em SQLite e Postgres 9.5+).
    try:
        db.session.execute(
            db.text("CREATE INDEX IF NOT EXISTS ix_leads_situacao ON leads(situacao)")
        )
        db.session.commit()
        print("[MIGRATION]   índice ix_leads_situacao garantido.")
    except Exception as e:  # pragma: no cover - defensivo
        db.session.rollback()
        print(f"[MIGRATION]   [WARN] não foi possível criar ix_leads_situacao: {e}")

    # Backfill idempotente: confirmados sem situação entram em "aguardando_resposta".
    result = db.session.execute(
        db.text(
            "UPDATE leads SET situacao = 'aguardando_resposta' "
            "WHERE status = 'whatsapp_iniciado' AND situacao IS NULL"
        )
    )
    db.session.commit()
    print(f"[MIGRATION]   backfill concluído: {result.rowcount or 0} leads confirmados atualizados.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
