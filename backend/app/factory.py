# -*- coding: utf-8 -*-
"""
Application Factory - Criação e configuração da aplicação Flask
Orquestra a inicialização de todos os componentes da aplicação
"""
import os

from flask import Flask

from app.cors import setup_cors
from app.errors import register_error_handlers
from app.extensions import init_database, init_extensions
from app.static import register_static_routes


def create_app(config=None):
    """
    Application Factory - cria e configura aplicação Flask

    Esta função orquestra a inicialização de todos os componentes
    da aplicação na ordem correta:
    1. Configuração
    2. Extensões (db)
    3. CORS
    4. Blueprints e Database
    5. Error Handlers
    6. Static Routes
    7. Security/Middleware

    Args:
        config: Dicionário com configurações opcionais

    Returns:
        Flask: Instância configurada da aplicação Flask
    """
    # Criar aplicação Flask
    app = Flask(__name__)

    # 1. Configuração (PRIMEIRO)
    if config:
        app.config.update(config)
    else:
        from app.config import BaseConfig

        app.config.from_object(BaseConfig)

    # 1.1 Validar SECRET_KEY obrigatória (falha rápida antes de qualquer inicialização)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY não configurada.\n"
            "Gere uma chave segura: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    # 1.2 Credenciais Google (escreve arquivo a partir de env var se necessário)
    _setup_google_credentials(app)

    # 2. Extensões (ANTES de importar models)
    init_extensions(app)

    # 3. CORS (pode ser antes ou depois, mas antes das rotas)
    setup_cors(app)

    # 4. Blueprints e Database (dentro de app_context)
    with app.app_context():
        from app.routes.auth import auth_bp
        from app.routes.backup_admin import backup_admin_bp
        from app.routes.clientes import clientes_bp
        from app.routes.config import config_bp
        from app.routes.core import core_bp
        from app.routes.fontes import fontes_bp
        from app.routes.leads import leads_bp
        from app.routes.ledger_routes import ledger_bp
        from app.routes.meta_gateway import meta_gateway_bp
        from app.routes.notifications import notifications_bp
        from app.routes.nuvemshop import nuvemshop_bp
        from app.routes.pedidos import pedidos_bp
        from app.routes.rotas import rotas_bp
        from app.routes.storefront import storefront_bp
        from app.routes.user_routes import users_bp

        # Importar novos models para garantir que as tabelas sejam criadas
        from app.models.user import User  # noqa: F401
        from app.models.ledger_entry import LedgerEntry  # noqa: F401

        # Blueprints por domínio
        app.register_blueprint(pedidos_bp)
        app.register_blueprint(rotas_bp)
        app.register_blueprint(clientes_bp)
        app.register_blueprint(fontes_bp)
        app.register_blueprint(core_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(config_bp)
        app.register_blueprint(backup_admin_bp)
        app.register_blueprint(nuvemshop_bp)
        app.register_blueprint(notifications_bp)
        app.register_blueprint(leads_bp)

        # Módulo Recebíveis (Auth JWT + Ledger + Users)
        app.register_blueprint(users_bp)
        app.register_blueprint(ledger_bp)

        # Meta Gateway (antes das rotas estáticas)
        app.register_blueprint(meta_gateway_bp)

        # Storefront: endpoints públicos para scripts Nuvemshop (CORS *)
        app.register_blueprint(storefront_bp)

        # Debug endpoints: só registrar se ENABLE_DEBUG_ENDPOINTS=true
        if os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true":
            from app.routes.debug import debug_bp

            app.register_blueprint(debug_bp)

        # Criar tabelas (APÓS todos os models serem importados)
        init_database(app)

    # 5. Error handlers (antes de static routes)
    register_error_handlers(app)

    # 6. OpenAPI/Swagger (ANTES das rotas estáticas para não ser interceptado pelo catch-all)
    try:
        from app.openapi import init_openapi

        init_openapi(app)
        print("[OPENAPI] Swagger UI disponível em /docs/swagger")
    except ImportError:
        # flask-smorest não instalado, continuar sem documentação
        print("[AVISO] flask-smorest não instalado. Swagger UI não estará disponível.")
    except Exception as e:
        # Erro ao inicializar OpenAPI, continuar sem documentação
        print(f"[AVISO] Erro ao inicializar OpenAPI: {e}")
        print("[AVISO] Swagger UI não estará disponível, mas a API continua funcionando")

    # 7. Static routes (POR ÚLTIMO - catch-all)
    register_static_routes(app)

    # 8. Security/Middleware (pode ser a qualquer momento)
    setup_security(app)

    # 9. Registrar comandos CLI
    register_cli_commands(app)

    # 10. Fila: após cálculo de distância, calcular taxa em background
    try:
        from app.services.fila_taxa_entrega import start_worker

        start_worker(app)
    except Exception as e:
        print(f"[AVISO] Fila de taxa de entrega não iniciada: {e}")

    return app


def _setup_google_credentials(app):
    """
    Escreve google_credentials.json a partir da variável de ambiente GOOGLE_CREDENTIALS_JSON.

    Útil no Docker/VPS onde o arquivo não está no repositório (gitignore).
    Se GOOGLE_CREDENTIALS_JSON estiver definida e o arquivo não existir, cria-o.
    """
    import json
    import os
    from pathlib import Path

    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    if not creds_json:
        return

    creds_path_str = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not creds_path_str:
        creds_path = Path(app.root_path).parent / "user" / "config" / "google_credentials.json"
    else:
        creds_path = Path(creds_path_str)

    if creds_path.exists():
        return  # Arquivo já existe, não sobrescrever

    try:
        parsed = json.loads(creds_json)
        creds_path.parent.mkdir(parents=True, exist_ok=True)
        creds_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        if os.name != "nt":
            creds_path.chmod(0o600)
        print(f"[GOOGLE] google_credentials.json criado em {creds_path}")
    except Exception as e:
        print(
            f"[AVISO] Falha ao criar google_credentials.json a partir de GOOGLE_CREDENTIALS_JSON: {e}"
        )


def register_cli_commands(app):
    """
    Registra comandos CLI na aplicação

    Args:
        app: Instância da aplicação Flask
    """
    try:
        from app.cli import register_commands

        register_commands(app)
    except ImportError:
        # CLI não disponível (pode acontecer durante setup inicial)
        pass


def setup_security(app):
    """
    Configura segurança e middleware da aplicação

    Args:
        app: Instância da aplicação Flask
    """
    import os

    from app.middleware import setup_security_middleware

    ENABLE_RATE_LIMIT = os.environ.get("ENABLE_RATE_LIMIT", "true").lower() == "true"
    ENABLE_DEBUG_ENDPOINTS = os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true"

    try:
        setup_security_middleware(
            app,
            enable_auth=False,  # Autenticação global desativada - apenas rotas específicas
            enable_rate_limit=ENABLE_RATE_LIMIT,
        )
        print("[SEGURANCA] OK Autenticacao seletiva ATIVADA")
        print(
            "[SEGURANCA]   Visualizacao livre - Apenas criar/deletar pedidos requerem autenticacao"
        )
        print("[SEGURANCA]   Usuario: admin")
        if ENABLE_RATE_LIMIT:
            print("[SEGURANCA] OK Rate Limiting ATIVADO (60/min, 1000/hora)")
        if not ENABLE_DEBUG_ENDPOINTS:
            print("[SEGURANCA] OK Endpoints de Debug DESATIVADOS")
    except ImportError:
        print("[AVISO] Middleware de segurança não encontrado.")
    except Exception as e:
        print(f"[AVISO] Erro ao configurar segurança: {e}")
