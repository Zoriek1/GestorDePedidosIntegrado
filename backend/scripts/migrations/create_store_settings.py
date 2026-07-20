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


def migrate() -> None:
    StoreSetting.__table__.create(bind=db.engine, checkfirst=True)
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
