# -*- coding: utf-8 -*-
"""
Migration: adiciona followup_feito_em + followup_por em leads.

Objetivo
--------
Rastrear o último contato manual com um Lead Confirmado. NULL significa
"nunca foi feito followup"; preenchido vira "feito por X em Y". Permite
filtros tipo "confirmados sem followup há 7/15/30 dias" sem migrations
futuras (basta um WHERE no timestamp).

Backfill
--------
Todos os leads pré-existentes recebem followup_feito_em = NOW() para não
sujarem o histórico do filtro "sem followup há X dias". Leads novos (criados
após a migration) ficam NULL e entram no radar do followup imediatamente.

Idempotente
-----------
Não duplica colunas nem reescreve timestamps já preenchidos.

Uso
---
    docker compose exec backend python scripts/migrations/add_followup_to_leads.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db


def column_exists(table: str, col: str) -> bool:
    from sqlalchemy import inspect

    return col in [c["name"] for c in inspect(db.engine).get_columns(table)]


def migrate():
    print(f"[MIGRATION] add_followup_to_leads (banco: {db.engine.dialect.name})")

    if not column_exists("leads", "followup_feito_em"):
        db.session.execute(
            db.text("ALTER TABLE leads ADD COLUMN followup_feito_em TIMESTAMP NULL")
        )
        db.session.commit()
        print("[MIGRATION]   coluna leads.followup_feito_em adicionada.")
    else:
        print("[MIGRATION]   coluna leads.followup_feito_em já existe.")

    if not column_exists("leads", "followup_por"):
        db.session.execute(
            db.text(
                "ALTER TABLE leads ADD COLUMN followup_por INTEGER NULL "
                "REFERENCES users(id)"
            )
        )
        db.session.commit()
        print("[MIGRATION]   coluna leads.followup_por adicionada.")
    else:
        print("[MIGRATION]   coluna leads.followup_por já existe.")

    # Backfill em batches: leads pré-existentes ganham NOW() para não aparecerem
    # como "pendentes de followup". Idempotente — só toca rows com NULL.
    print("[MIGRATION]   backfilling followup_feito_em para leads pré-existentes...")
    batch = 500
    total = 0
    while True:
        result = db.session.execute(
            db.text(
                "UPDATE leads SET followup_feito_em = NOW() "
                "WHERE id IN ("
                "  SELECT id FROM leads WHERE followup_feito_em IS NULL "
                "  ORDER BY id ASC LIMIT :batch"
                ")"
            ),
            {"batch": batch},
        )
        affected = result.rowcount or 0
        db.session.commit()
        if affected == 0:
            break
        total += affected
        print(f"[MIGRATION]     batch concluído (acumulado: {total})")

    print(f"[MIGRATION]   backfill concluído: {total} leads atualizados.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
