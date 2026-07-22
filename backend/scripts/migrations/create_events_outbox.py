# -*- coding: utf-8 -*-
"""Cria a tabela events_outbox (outbox unificado de eventos de marketing)."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

try:
    from app import create_app
    from app.config import config

    env = os.environ.get("FLASK_ENV", "production")
    app_config = config.get(env, config["default"])
    app = create_app(
        config={
            "SECRET_KEY": app_config.SECRET_KEY,
            "SQLALCHEMY_DATABASE_URI": app_config.SQLALCHEMY_DATABASE_URI,
            "SQLALCHEMY_TRACK_MODIFICATIONS": app_config.SQLALCHEMY_TRACK_MODIFICATIONS,
            "JSON_AS_ASCII": app_config.JSON_AS_ASCII,
            "JSON_SORT_KEYS": app_config.JSON_SORT_KEYS,
        }
    )
    with app.app_context():
        from app import db

        sql_path = Path(__file__).with_suffix(".sql")
        sql = sql_path.read_text(encoding="utf-8")
        db.session.execute(db.text(sql))
        db.session.commit()
        print("[OK] Tabela events_outbox criada com sucesso.")
except Exception as e:
    print(f"[ERRO] {e}", file=sys.stderr)
    sys.exit(1)
