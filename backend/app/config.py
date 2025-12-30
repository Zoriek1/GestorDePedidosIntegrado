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
    INSTANCE_DIR = BASE_DIR / 'instance'
    # Garantir que instance/ existe
    INSTANCE_DIR.mkdir(exist_ok=True)

    # Diretório externo para o banco de dados (fora do repositório)
    _HOME_DIR = Path(os.path.expanduser("~"))
    _DB_EXTERNAL_DIR = _HOME_DIR / "var" / "lib" / "database"
    _DB_EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    # Diretório do Google Drive Desktop para backups encriptados
    # Padrão: C:\Users\<USER>\Meu Drive\Plante Uma Flor Confidential\Database - Pedidos Gestor
    GDRIVE_BACKUP_DIR = Path(
        os.environ.get('GDRIVE_BACKUP_DIR') or 
        _HOME_DIR / "Meu Drive" / "Plante Uma Flor Confidential" / "Database - Pedidos Gestor"
    )
    # Criar diretório automaticamente se não existir
    GDRIVE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Secret key para sessões
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'plante-uma-flor-pwa-secret-key-2024'
    
    # Banco de dados SQLite
    # Novo local: %USERPROFILE%/var/lib/database/database.db (fora do repositório)
    DATABASE_PATH = _DB_EXTERNAL_DIR / 'database.db'
    # Formatar caminho para SQLite (Windows precisa de barras normais ou r'')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH.as_posix()}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações gerais
    JSON_AS_ASCII = False  # Suporte a caracteres UTF-8 em JSON
    JSON_SORT_KEYS = False  # Manter ordem dos campos
    
    # Servidor
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Autenticação
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'plante1998'
    
    # APIs Externas
    GRAPHHOPPER_API_KEY = os.environ.get('GRAPHHOPPER_API_KEY') or ''
    OPENROUTE_API_KEY = os.environ.get('OPENROUTE_API_KEY') or ''
    ENDERECO_FLORICULTURA = os.environ.get('ENDERECO_FLORICULTURA') or ''
    
    # Segurança e Middleware
    ENABLE_AUTH = os.environ.get('ENABLE_AUTH', 'true').lower() == 'true'
    ENABLE_RATE_LIMIT = os.environ.get('ENABLE_RATE_LIMIT', 'true').lower() == 'true'
    ENABLE_DEBUG_ENDPOINTS = os.environ.get('ENABLE_DEBUG_ENDPOINTS', 'false').lower() == 'true'
    
    # Ambiente
    FLASK_ENV = os.environ.get('FLASK_ENV') or os.environ.get('ENVIRONMENT') or 'development'
    APP_ENV = os.environ.get('APP_ENV') or os.environ.get('ENVIRONMENT') or 'development'
    
    # Servidor (opções)
    USE_HTTPS = os.environ.get('USE_HTTPS', 'false').lower() == 'true'
    NO_RELOAD = os.environ.get('NO_RELOAD', 'false').lower() == 'true'
    FORCE_START = os.environ.get('FORCE_START', 'false').lower() == 'true'
    
    # Database (SQLite)
    SQLITE_SYNCHRONOUS = os.environ.get('SQLITE_SYNCHRONOUS', 'FULL')
    ALLOW_DB_BOOTSTRAP = os.environ.get('ALLOW_DB_BOOTSTRAP', 'false').lower() == 'true'
    
    # Google Services
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or ''
    GOOGLE_CREDENTIALS_PATH = os.environ.get('GOOGLE_CREDENTIALS_PATH') or ''
    GDRIVE_BACKUP_FOLDER_ID = os.environ.get('GDRIVE_BACKUP_FOLDER_ID') or ''
    
    @staticmethod
    def init_app(app):
        """Inicialização adicional da aplicação"""
        pass


class DevelopmentConfig(BaseConfig):
    """Configurações de desenvolvimento"""
    # DEBUG desativado por padrão para estabilidade com múltiplos clientes
    # Use --no-reload para garantir modo estável
    DEBUG = False
    FLASK_ENV = 'development'
    APP_ENV = 'development'


class ProductionConfig(BaseConfig):
    """Configurações de produção"""
    DEBUG = False
    FLASK_ENV = 'production'
    APP_ENV = 'production'
    
    # Em produção, usar secret key da variável de ambiente
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production-please'
    
    @staticmethod
    def init_app(app):
        # Validar SECRET_KEY apenas quando a app for iniciada
        if app.config.get('SECRET_KEY') == 'change-this-in-production-please':
            import warnings
            warnings.warn('SECRET_KEY não definida! Configure a variável de ambiente SECRET_KEY em produção.')


class TestingConfig(BaseConfig):
    """Configurações para testes"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False


# Dicionário de configurações disponíveis
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
