# -*- coding: utf-8 -*-
"""
Configurações da Aplicação Flask

Centraliza todas as variáveis de ambiente e configurações da aplicação.
"""
import os
from pathlib import Path


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
    SECRET_KEY = os.environ.get("SECRET_KEY") or ""

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
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or ""

    # JWT (módulo Recebíveis)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS") or 24)
    AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "false").lower() == "true"
    BCRYPT_LOG_ROUNDS = int(os.environ.get("BCRYPT_LOG_ROUNDS") or 12)

    # APIs Externas
    GRAPHHOPPER_API_KEY = os.environ.get("GRAPHHOPPER_API_KEY") or ""
    OPENROUTE_API_KEY = os.environ.get("OPENROUTE_API_KEY") or ""
    ENDERECO_FLORICULTURA = os.environ.get("ENDERECO_FLORICULTURA") or ""
    LOJA_CEP = os.environ.get("LOJA_CEP") or ""

    # Google Maps Platform (Geocoding + Address Validation)
    GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY") or ""

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

    # Conversoes de vendas originadas no clique de WhatsApp da loja.
    MARKETING_DISPATCH_ENABLED = (
        os.environ.get("MARKETING_DISPATCH_ENABLED", "false").lower() == "true"
    )
    GA4_MEASUREMENT_ID = os.environ.get("GA4_MEASUREMENT_ID") or ""
    GA4_API_SECRET = os.environ.get("GA4_API_SECRET") or ""
    GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY = (
        os.environ.get("GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY", "false").lower() == "true"
    )
    GOOGLE_DATAMANAGER_ENABLED = (
        os.environ.get("GOOGLE_DATAMANAGER_ENABLED", "false").lower() == "true"
    )
    GOOGLE_DATAMANAGER_VALIDATE_ONLY = (
        os.environ.get("GOOGLE_DATAMANAGER_VALIDATE_ONLY", "true").lower() == "true"
    )
    GOOGLE_CLOUD_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT_ID") or ""
    GOOGLE_ADS_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID") or ""
    GOOGLE_ADS_CONVERSION_ACTION_ID = os.environ.get("GOOGLE_ADS_CONVERSION_ACTION_ID") or ""
    GOOGLE_DATAMANAGER_CREDENTIALS_JSON = (
        os.environ.get("GOOGLE_DATAMANAGER_CREDENTIALS_JSON") or ""
    )

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

    # Bling API v3 (OAuth + pedidos/financeiro)
    BLING_ENABLED = os.environ.get("BLING_ENABLED", "false").lower() == "true"
    BLING_CLIENT_ID = os.environ.get("BLING_CLIENT_ID") or ""
    BLING_CLIENT_SECRET = os.environ.get("BLING_CLIENT_SECRET") or ""
    BLING_REDIRECT_URI = os.environ.get("BLING_REDIRECT_URI") or ""
    BLING_API_BASE_URL = os.environ.get(
        "BLING_API_BASE_URL", "https://api.bling.com.br/Api/v3"
    ).rstrip("/")
    BLING_AUTH_BASE_URL = os.environ.get(
        "BLING_AUTH_BASE_URL", "https://www.bling.com.br/Api/v3/oauth"
    ).rstrip("/")
    BLING_TIMEOUT_SECONDS = int(os.environ.get("BLING_TIMEOUT_SECONDS") or 20)
    BLING_DEFAULT_PRODUCT_CODE = os.environ.get("BLING_DEFAULT_PRODUCT_CODE", "PEDIDO-FLORICULTURA")
    BLING_DEFAULT_PRODUCT_NAME = os.environ.get("BLING_DEFAULT_PRODUCT_NAME", "Pedido Floricultura")
    # Bling v3 exige contato.id na venda. Por padrao o app cria/usa um contato
    # com o nome do cliente do pedido; defina aqui para forcar um contato fixo.
    BLING_DEFAULT_CONTACT_ID = os.environ.get("BLING_DEFAULT_CONTACT_ID") or ""
    # Tipo de contato "Cliente" (papel) marcado ao criar contatos. Vazio = o app
    # resolve automaticamente via /contatos/tipos procurando "Cliente".
    BLING_CONTACT_TYPE_ID = os.environ.get("BLING_CONTACT_TYPE_ID") or ""
    BLING_STORE_ID = os.environ.get("BLING_STORE_ID", "default")
    # Teto de paginas ao varrer /contas/receber procurando as contas do pedido.
    BLING_RECEIVABLE_SEARCH_PAGES = int(os.environ.get("BLING_RECEIVABLE_SEARCH_PAGES") or 10)

    # Multi-tenant: força o modo estrito (OAuth state/callback por loja, sem
    # fallbacks single-tenant) mesmo com uma única loja. Por padrão o modo é
    # data-driven (ativa sozinho quando existe mais de uma loja ATIVA); este flag
    # serve para validar o comportamento em staging antes de criar a 2ª loja.
    FORCE_MULTI_TENANT = os.environ.get("FORCE_MULTI_TENANT", "false").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    # UTMify API (vendas WhatsApp / manual — Integrações > Credenciais de API)
    UTMIFY_ENABLED = os.environ.get("UTMIFY_ENABLED", "false").lower() == "true"
    UTMIFY_API_TOKEN = os.environ.get("UTMIFY_API_TOKEN", "").strip()
    UTMIFY_POSTBACK_URL = os.environ.get(
        "UTMIFY_POSTBACK_URL", "https://api.utmify.com.br/api-credentials/orders"
    ).strip()
    UTMIFY_PLATFORM = os.environ.get("UTMIFY_PLATFORM", "WhatsAppManual").strip()
    UTMIFY_TIMEOUT_SECONDS = float(os.environ.get("UTMIFY_TIMEOUT_SECONDS", "5"))
    UTMIFY_IS_TEST = os.environ.get("UTMIFY_IS_TEST", "false").lower() == "true"

    # Per-integration env fallback flag
    INTEGRATION_ENV_FALLBACK = [
        s.strip() for s in os.environ.get("INTEGRATION_ENV_FALLBACK", "").split(",") if s.strip()
    ]

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
        pass


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

    pass


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
