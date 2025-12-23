# -*- coding: utf-8 -*-
"""
Application Factory - Criação e configuração da aplicação Flask
Orquestra a inicialização de todos os componentes da aplicação
"""
from flask import Flask
from app.extensions import init_extensions, init_database
from app.cors import setup_cors
from app.errors import register_error_handlers
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
        from app.config import Config
        app.config.from_object(Config)
    
    # 2. Extensões (ANTES de importar models)
    init_extensions(app)
    
    # 3. CORS (pode ser antes ou depois, mas antes das rotas)
    setup_cors(app)
    
    # 4. Blueprints e Database (dentro de app_context)
    with app.app_context():
        from app.routes.api import api_bp
        from app.routes.clientes import clientes_bp
        
        app.register_blueprint(api_bp)
        app.register_blueprint(clientes_bp)
        
        # Criar tabelas (APÓS todos os models serem importados)
        init_database(app)
    
    # 5. Error handlers (antes de static routes)
    register_error_handlers(app)
    
    # 6. Static routes (POR ÚLTIMO - catch-all)
    register_static_routes(app)
    
    # 7. Security/Middleware (pode ser a qualquer momento)
    setup_security(app)
    
    return app


def setup_security(app):
    """
    Configura segurança e middleware da aplicação
    
    Args:
        app: Instância da aplicação Flask
    """
    import os
    from app.middleware import setup_security_middleware
    
    ENABLE_AUTH = os.environ.get('ENABLE_AUTH', 'true').lower() == 'true'
    ENABLE_RATE_LIMIT = os.environ.get('ENABLE_RATE_LIMIT', 'true').lower() == 'true'
    ENABLE_DEBUG_ENDPOINTS = os.environ.get('ENABLE_DEBUG_ENDPOINTS', 'false').lower() == 'true'
    
    try:
        setup_security_middleware(
            app,
            enable_auth=False,  # Autenticação global desativada - apenas rotas específicas
            enable_rate_limit=ENABLE_RATE_LIMIT
        )
        print("[SEGURANCA] OK Autenticacao seletiva ATIVADA")
        print("[SEGURANCA]   Visualizacao livre - Apenas criar/deletar pedidos requerem autenticacao")
        print("[SEGURANCA]   Usuario: admin")
        if ENABLE_RATE_LIMIT:
            print("[SEGURANCA] OK Rate Limiting ATIVADO (60/min, 1000/hora)")
        if not ENABLE_DEBUG_ENDPOINTS:
            print("[SEGURANCA] OK Endpoints de Debug DESATIVADOS")
    except ImportError:
        print("[AVISO] Middleware de segurança não encontrado.")
    except Exception as e:
        print(f"[AVISO] Erro ao configurar segurança: {e}")

