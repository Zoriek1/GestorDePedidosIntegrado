# -*- coding: utf-8 -*-
"""
Configurações da Aplicação Flask

Centraliza todas as variáveis de ambiente e configurações da aplicação.
"""
import json
import os
import time
from pathlib import Path


# #region agent log
def log_debug(msg, data):
    """Log de debug apenas em modo desenvolvimento"""
    env = os.environ.get("FLASK_ENV", "development")
    if env != "production":
        try:
            with open(
                r"c:\Gestor de Pedidos Plante uma flor\.cursor\debug.log",
                "a",
                encoding="utf-8",
            ) as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "timestamp": int(time.time() * 1000),
                            "location": "config.py",
                            "message": msg,
                            "data": data,
                        }
                    )
                    + "\n"
                )
        except Exception:
            # Silenciar erros de log em produção
            pass


# #endregion


class BaseConfig:
    """Configurações base da aplicação"""

    # Diretório base do backend
    BASE_DIR = Path(__file__).parent.parent

    # Diretório instance (dados de runtime não versionados)
    INSTANCE_DIR = BASE_DIR / "instance"
    # Garantir que instance/ existe
    INSTANCE_DIR.mkdir(exist_ok=True)

    # Diretório externo para o banco de dados (fora do repositório)
    _HOME_DIR = Path(os.path.expanduser("~"))
    _DB_EXTERNAL_DIR = _HOME_DIR / "var" / "lib" / "database"
    _DB_EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    # Diretório do Google Drive Desktop para backups encriptados
    # Padrão: C:\Users\<USER>\Meu Drive\Plante Uma Flor Confidential\Database - Pedidos Gestor
    GDRIVE_BACKUP_DIR = Path(
        os.environ.get("GDRIVE_BACKUP_DIR")
        or _HOME_DIR / "Meu Drive" / "Plante Uma Flor Confidential" / "Database - Pedidos Gestor"
    )
    # Criar diretório automaticamente se não existir
    GDRIVE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Diretório secundário para backups (P1.4) - opcional
    BACKUP_SECONDARY_DIR = (
        Path(os.environ.get("BACKUP_SECONDARY_DIR"))
        if os.environ.get("BACKUP_SECONDARY_DIR")
        else None
    )

    # Secret key para sessões
    SECRET_KEY = os.environ.get("SECRET_KEY") or "plante-uma-flor-pwa-secret-key-2024"

    # Banco de dados
    # PostgreSQL: use DATABASE_URL (ex: postgresql://user:pass@host:port/dbname)
    # SQLite: default %USERPROFILE%/var/lib/database/database.db
    DATABASE_PATH = _DB_EXTERNAL_DIR / "database.db"
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or f"sqlite:///{DATABASE_PATH.as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Frontend (path do dist para servir SPA)
    FRONTEND_DIST_PATH = (
        Path(os.environ["FRONTEND_DIST_PATH"]) if os.environ.get("FRONTEND_DIST_PATH") else None
    )

    # Configurações gerais
    JSON_AS_ASCII = False  # Suporte a caracteres UTF-8 em JSON
    JSON_SORT_KEYS = False  # Manter ordem dos campos

    # Servidor
    HOST = os.environ.get("HOST") or "0.0.0.0"
    PORT = int(os.environ.get("PORT") or 5000)
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

    # Autenticação
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or "plante1998"

    # APIs Externas
    GRAPHHOPPER_API_KEY = os.environ.get("GRAPHHOPPER_API_KEY") or ""
    OPENROUTE_API_KEY = os.environ.get("OPENROUTE_API_KEY") or ""
    ENDERECO_FLORICULTURA = os.environ.get("ENDERECO_FLORICULTURA") or ""

    # Meta Conversions API
    META_PIXEL_ID = os.environ.get("META_PIXEL_ID") or ""
    META_CAPI_ACCESS_TOKEN = os.environ.get("META_CAPI_ACCESS_TOKEN") or ""
    META_CAPI_API_VERSION = os.environ.get("META_CAPI_API_VERSION", "v21.0")
    META_TEST_EVENT_CODE = os.environ.get("META_TEST_EVENT_CODE") or ""
    # Conversions API Gateway (opcional - melhora visualização e métricas)
    META_CAPI_USE_GATEWAY = os.environ.get("META_CAPI_USE_GATEWAY", "false").lower() == "true"
    META_CAPI_GATEWAY_DOMAIN = (
        os.environ.get("META_CAPI_GATEWAY_DOMAIN") or "gestaopedidos.planteumaflor.online"
    )
    # Endpoint completo do Gateway (opcional - se fornecido, usa este ao invés de construir)
    META_CAPI_GATEWAY_ENDPOINT = os.environ.get("META_CAPI_GATEWAY_ENDPOINT") or ""

    # Segurança e Middleware
    ENABLE_AUTH = os.environ.get("ENABLE_AUTH", "true").lower() == "true"
    ENABLE_RATE_LIMIT = os.environ.get("ENABLE_RATE_LIMIT", "true").lower() == "true"
    ENABLE_DEBUG_ENDPOINTS = os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true"

    # Push Notifications (VAPID / Web Push)
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY") or ""
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY") or ""
    VAPID_CLAIMS_EMAIL = (
        os.environ.get("VAPID_CLAIMS_EMAIL") or "mailto:contato@planteumaflor.com.br"
    )

    # Nuvemshop (OAuth + Webhooks)
    NUVEMSHOP_APP_ID = os.environ.get("NUVEMSHOP_APP_ID") or ""
    NUVEMSHOP_CLIENT_SECRET = os.environ.get("NUVEMSHOP_CLIENT_SECRET") or ""
    NUVEMSHOP_USER_AGENT = os.environ.get("NUVEMSHOP_USER_AGENT") or ""
    NUVEMSHOP_PUBLIC_BASE_URL = os.environ.get("NUVEMSHOP_PUBLIC_BASE_URL") or ""

    # Ambiente
    FLASK_ENV = os.environ.get("FLASK_ENV") or os.environ.get("ENVIRONMENT") or "development"
    APP_ENV = os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development"

    # Servidor (opções)
    USE_HTTPS = os.environ.get("USE_HTTPS", "false").lower() == "true"
    NO_RELOAD = os.environ.get("NO_RELOAD", "false").lower() == "true"
    FORCE_START = os.environ.get("FORCE_START", "false").lower() == "true"

    # Database (SQLite)
    SQLITE_SYNCHRONOUS = os.environ.get("SQLITE_SYNCHRONOUS", "FULL")
    ALLOW_DB_BOOTSTRAP = os.environ.get("ALLOW_DB_BOOTSTRAP", "false").lower() == "true"

    # Google Services
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or ""
    GOOGLE_CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH") or ""
    GDRIVE_BACKUP_FOLDER_ID = os.environ.get("GDRIVE_BACKUP_FOLDER_ID") or ""

    # Schema Version (P1.1)
    APP_SCHEMA_VERSION = "1.0"

    @staticmethod
    def init_app(app):
        """Inicialização adicional da aplicação"""
        # Do not log secrets (password). Only log non-sensitive diagnostics.
        log_debug(
            "BaseConfig.init_app",
            {
                "DATABASE_PATH": str(BaseConfig.DATABASE_PATH),
                "ADMIN_PASSWORD_LEN": len(BaseConfig.ADMIN_PASSWORD)
                if BaseConfig.ADMIN_PASSWORD
                else 0,
                "ADMIN_PASSWORD_IS_LOWER": bool(BaseConfig.ADMIN_PASSWORD)
                and BaseConfig.ADMIN_PASSWORD == BaseConfig.ADMIN_PASSWORD.lower(),
            },
        )


# Backwards-compat alias:
# Some modules import `Config` (e.g. `from app.config import Config`) expecting a class
# with static paths like `INSTANCE_DIR`. Keep compatibility without refactoring callers.
Config = BaseConfig


class DevelopmentConfig(BaseConfig):
    """Configurações de desenvolvimento"""

    # DEBUG desativado por padrão para estabilidade com múltiplos clientes
    # Use --no-reload para garantir modo estável
    DEBUG = False
    FLASK_ENV = "development"
    APP_ENV = "development"


class ProductionConfig(BaseConfig):
    """Configurações de produção"""

    DEBUG = False
    FLASK_ENV = "production"
    APP_ENV = "production"

    # Em produção, usar secret key da variável de ambiente
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change-this-in-production-please"

    @staticmethod
    def init_app(app):
        # Validar SECRET_KEY apenas quando a app for iniciada
        if app.config.get("SECRET_KEY") == "change-this-in-production-please":
            import warnings

            warnings.warn(
                "SECRET_KEY não definida! Configure a variável de ambiente SECRET_KEY em produção.",
                stacklevel=2,
            )


class TestingConfig(BaseConfig):
    """Configurações para testes"""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False


# Dicionário de configurações disponíveis
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
