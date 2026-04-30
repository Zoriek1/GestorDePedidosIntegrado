# -*- coding: utf-8 -*-
"""
Migration: cria tabela lead_touchpoints + adiciona first_touch_id/last_touch_id em leads.

Objetivo
--------
Permitir atribuição last non-direct (cada hit em /api/leads vira uma linha em
lead_touchpoints; lead.utm_* passa a refletir o último toque pago). Histórico
completo fica preservado para drill-down.

Backfill
--------
Cada lead existente recebe 1 touchpoint com seus utm_* atuais e created_at do
próprio lead. first_touch_id == last_touch_id == touchpoint.id (é o único toque
conhecido pré-migração). is_paid é derivado pelo helper do modelo.

Idempotente
-----------
Pula leads que já têm first_touch_id setado. Pode rodar várias vezes sem
duplicar touchpoints.

Uso
---
    cd backend && python scripts/migrations/add_lead_touchpoints.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db
from app.models.lead import Lead
from app.models.lead_touchpoint import LeadTouchpoint, derive_is_paid


def column_exists(table: str, col: str) -> bool:
    from sqlalchemy import inspect

    return col in [c["name"] for c in inspect(db.engine).get_columns(table)]


def table_exists(name: str) -> bool:
    from sqlalchemy import inspect

    return name in inspect(db.engine).get_table_names()


def migrate():
    print(f"[MIGRATION] add_lead_touchpoints (banco: {db.engine.dialect.name})")

    if not table_exists("lead_touchpoints"):
        LeadTouchpoint.__table__.create(db.engine)
        print("[MIGRATION]   tabela lead_touchpoints criada.")
    else:
        print("[MIGRATION]   tabela lead_touchpoints já existe.")

    for col in ("first_touch_id", "last_touch_id"):
        if not column_exists("leads", col):
            db.session.execute(
                db.text(
                    f"ALTER TABLE leads ADD COLUMN {col} INTEGER "
                    f"REFERENCES lead_touchpoints(id)"
                )
            )
            db.session.commit()
            print(f"[MIGRATION]   coluna leads.{col} adicionada.")
        else:
            print(f"[MIGRATION]   coluna leads.{col} já existe.")

    print("[MIGRATION]   backfilling touchpoints...")
    batch = 500
    total_filled = 0
    while True:
        leads = (
            Lead.query.filter(Lead.first_touch_id.is_(None))
            .order_by(Lead.id.asc())
            .limit(batch)
            .all()
        )
        if not leads:
            break

        for lead in leads:
            tp = LeadTouchpoint(
                lead_id=lead.id,
                utm_source=lead.utm_source,
                utm_medium=lead.utm_medium,
                utm_campaign=lead.utm_campaign,
                utm_content=lead.utm_content,
                utm_term=lead.utm_term,
                src=lead.src,
                sck=lead.sck,
                fbclid=lead.fbclid,
                fbp=lead.fbp,
                referrer=lead.referrer,
                url=lead.url,
                ip_address=lead.ip_address,
                client_user_agent=lead.client_user_agent,
                is_paid=derive_is_paid(utm_medium=lead.utm_medium, fbclid=lead.fbclid, utm_id=None),
                created_at=lead.created_at,
            )
            db.session.add(tp)
            db.session.flush()
            lead.first_touch_id = tp.id
            lead.last_touch_id = tp.id
            total_filled += 1

        db.session.commit()
        print(f"[MIGRATION]     batch concluído (acumulado: {total_filled})")

    print(f"[MIGRATION]   backfill concluído: {total_filled} leads atualizados.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
