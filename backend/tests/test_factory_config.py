# -*- coding: utf-8 -*-
import os
import tempfile


def test_create_app_partial_config_preserves_base_integration_config(monkeypatch):
    from app import create_app, db
    from app.config import BaseConfig

    db_fd, db_path = tempfile.mkstemp()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setattr(BaseConfig, "BLING_ENABLED", True)
    monkeypatch.setattr(BaseConfig, "BLING_CLIENT_ID", "client-id")
    monkeypatch.setattr(BaseConfig, "BLING_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(BaseConfig, "BLING_REDIRECT_URI", "https://example.test/callback")

    app = create_app(
        config={
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )

    try:
        assert app.config["BLING_ENABLED"] is True
        assert app.config["BLING_CLIENT_ID"] == "client-id"
        assert app.config["BLING_CLIENT_SECRET"] == "client-secret"
        assert app.config["BLING_REDIRECT_URI"] == "https://example.test/callback"
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        os.close(db_fd)
        try:
            os.unlink(db_path)
        except (FileNotFoundError, PermissionError):
            pass
