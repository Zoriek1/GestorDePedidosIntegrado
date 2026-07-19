# -*- coding: utf-8 -*-
"""Adiciona atribuição Google/GA4 e o outbox de conversões (idempotente)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import inspect

from app import create_app, db
from app.models.lead import Lead
from app.models.lead_touchpoint import LeadTouchpoint
from app.models.marketing_conversion_outbox import MarketingConversionOutbox


def _columns(table: str) -> set[str]:
    return {column["name"] for column in inspect(db.engine).get_columns(table)}


def _add_missing_columns(table: str, model, names: list[str]) -> None:
    existing = _columns(table)
    for name in names:
        if name in existing:
            continue
        column = model.__table__.columns[name]
        type_sql = column.type.compile(dialect=db.engine.dialect)
        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {name} {type_sql}"))
        db.session.commit()
        print(f"[MIGRATION]   {table}.{name} adicionada")


def migrate() -> None:
    tables = set(inspect(db.engine).get_table_names())
    if "leads" in tables:
        _add_missing_columns(
            "leads",
            Lead,
            [
                "gclid",
                "gbraid",
                "wbraid",
                "ga_client_id",
                "ga_session_id",
                "ga_session_started_at",
                "first_landing_url",
                "session_referrer",
                "cta_location",
                "product_id",
                "product_name",
            ],
        )
        for name, column in (
            ("ix_leads_gclid", "gclid"),
            ("ix_leads_gbraid", "gbraid"),
            ("ix_leads_wbraid", "wbraid"),
            ("ix_leads_ga_client_id", "ga_client_id"),
        ):
            db.session.execute(
                db.text(f"CREATE INDEX IF NOT EXISTS {name} ON leads ({column})")
            )
        db.session.commit()
    if "lead_touchpoints" in tables:
        _add_missing_columns(
            "lead_touchpoints",
            LeadTouchpoint,
            [
                "gclid",
                "gbraid",
                "wbraid",
                "ga_client_id",
                "ga_session_id",
                "ga_session_started_at",
                "cta_location",
                "product_id",
                "product_name",
            ],
        )
    MarketingConversionOutbox.__table__.create(db.engine, checkfirst=True)
    _add_missing_columns(
        "marketing_conversion_outbox",
        MarketingConversionOutbox,
        [
            "validation_only",
            "status_check_attempts",
            "last_status_check_at",
            "next_status_check_at",
        ],
    )
    db.session.execute(
        db.text(
            "UPDATE marketing_conversion_outbox "
            "SET validation_only = COALESCE(validation_only, false), "
            "status_check_attempts = COALESCE(status_check_attempts, 0)"
        )
    )
    db.session.execute(
        db.text(
            "CREATE INDEX IF NOT EXISTS ix_marketing_conversion_outbox_next_status_check_at "
            "ON marketing_conversion_outbox (next_status_check_at)"
        )
    )
    db.session.commit()
    print("[MIGRATION]   marketing_conversion_outbox pronta")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
