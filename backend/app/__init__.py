# -*- coding: utf-8 -*-
"""
Plante Uma Flor v3.0 - PWA
Sistema de Gerenciamento de Pedidos - Backend Flask API
"""
from flask import Flask

from app.extensions import db
from app.security import configure_security


def create_app(config=None):
    """
    Application Factory Pattern
    Cria e configura a aplicação Flask com CORS para PWA
    """
    # Criar aplicação Flask
    app = Flask(__name__)

    # Carregar configurações
    if config:
        app.config.update(config)
    else:
        from app.config import Config
        app.config.from_object(Config)

    # Configurações de segurança e CORS
    configure_security(app)

    # Inicializar extensões
    db.init_app(app)

    # Registrar Blueprints (apenas API REST)
    with app.app_context():
        from app.routes.api import api_bp
        from app.routes.clientes import clientes_bp
        from app.routes.frontend import register_frontend

        app.register_blueprint(api_bp)
        app.register_blueprint(clientes_bp)
        register_frontend(app)

        # Criar tabelas automaticamente
        db.create_all()

        print("[OK] Banco de dados inicializado")
        print(f"[OK] Tabelas criadas: {db.metadata.tables.keys()}")

    return app


__all__ = ["db", "create_app"]
