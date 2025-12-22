# -*- coding: utf-8 -*-
"""
Plante Uma Flor v3.0 - PWA
Sistema de Gerenciamento de Pedidos - Backend Flask API
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from pathlib import Path

from app.utils.logger import configure_logging, get_logger

# Instância global do SQLAlchemy
db = SQLAlchemy()

def create_app(config=None):
    """
    Application Factory Pattern
    Cria e configura a aplicação Flask com CORS para PWA
    """
    # Criar aplicação Flask
    app = Flask(__name__)
    
    # Habilitar CORS para permitir requisições do frontend PWA
    # SEGURANÇA: Apenas origens do próprio servidor (localhost + hostname configurado)
    import socket
    import configparser
    
    # Descobrir hostname configurado
    try:
        config_file = Path(__file__).parent.parent / 'config_servidor.ini'
        if config_file.exists():
            parser = configparser.ConfigParser()
            parser.read(config_file, encoding='utf-8')
            hostname = parser.get('SERVIDOR', 'hostname', fallback='Gestor-pedidos.local')
        else:
            hostname = 'Gestor-pedidos.local'
    except:
        hostname = 'Gestor-pedidos.local'
    
    # Descobrir IP local
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "192.168.1.148"
    
    # Lista de origens permitidas (apenas HTTPS do próprio servidor)
    allowed_origins = [
        "https://localhost:5000",
        "https://127.0.0.1:5000",
        f"https://{hostname}:5000",
        f"https://{local_ip}:5000"
    ]
    
    # Permitir HTTP apenas para localhost (desenvolvimento)
    if os.environ.get('FLASK_ENV') == 'development':
        allowed_origins.extend([
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ])
    
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # Carregar configurações
    if config:
        app.config.update(config)
    else:
        from app.config import Config
        app.config.from_object(Config)

    # Inicializar logging
    configure_logging(app.config.get("DEBUG"))
    logger = get_logger(__name__)

    logger.info("✓ CORS restrito a: %s origens permitidas", len(allowed_origins))
    
    # Inicializar extensões
    db.init_app(app)
    
    # Registrar Blueprints (apenas API REST)
    with app.app_context():
        from app.routes.api import api_bp
        from app.routes.clientes import clientes_bp
        
        app.register_blueprint(api_bp)
        app.register_blueprint(clientes_bp)
        
        # Criar tabelas automaticamente
        db.create_all()
        
        logger.info("Banco de dados inicializado")
        logger.info("Tabelas criadas: %s", db.metadata.tables.keys())
    
    # Configurar tratamento de erros
    @app.errorhandler(404)
    def not_found(e):
        """Redireciona 404 para index.html (SPA)"""
        from flask import send_from_directory
        frontend_dir = Path(__file__).parent.parent.parent / 'frontend'
        return send_from_directory(str(frontend_dir), 'index.html')
    
    @app.errorhandler(500)
    def internal_error(e):
        """Tratamento de erro 500"""
        logger.error("ERRO 500: %s", e)
        return {"error": "Erro interno do servidor"}, 500
    
    # Servir arquivos estáticos do frontend PWA
    @app.route('/')
    @app.route('/<path:path>')
    def serve_frontend(path='index.html'):
        """Serve arquivos do frontend PWA"""
        from flask import send_from_directory, abort
        try:
            frontend_dir = Path(__file__).parent.parent.parent / 'frontend'
            
            # Normalizar o path para evitar problemas
            if path == '' or path is None:
                path = 'index.html'
            
            # Se o arquivo existe, serve ele
            file_path = frontend_dir / path
            if file_path.exists() and file_path.is_file():
                return send_from_directory(str(frontend_dir), path)
            
            # Caso contrário, serve o index.html (SPA routing)
            return send_from_directory(str(frontend_dir), 'index.html')
        except Exception as e:
            logger.error("Erro ao servir arquivo '%s': %s", path, e)
            # Tentar servir o index.html como fallback
            try:
                return send_from_directory(str(frontend_dir), 'index.html')
            except:
                abort(404)
    
    # ============================================
    # SEGURANÇA: Autenticação e Rate Limiting
    # ============================================
    # Segurança ATIVADA por padrão se arquivo .env existir
    # Para desativar, defina ENABLE_AUTH=false no .env
    ENABLE_AUTH = os.environ.get('ENABLE_AUTH', 'true').lower() == 'true'
    ENABLE_RATE_LIMIT = os.environ.get('ENABLE_RATE_LIMIT', 'true').lower() == 'true'
    ENABLE_DEBUG_ENDPOINTS = os.environ.get('ENABLE_DEBUG_ENDPOINTS', 'false').lower() == 'true'
    
    # Sempre configurar middleware (rate limiting sempre ativo)
    # Autenticação agora é seletiva - apenas rotas críticas exigem autenticação
    try:
        from app.middleware import setup_security_middleware
        setup_security_middleware(
            app,
            enable_auth=False,  # Autenticação global desativada - apenas rotas específicas
            enable_rate_limit=ENABLE_RATE_LIMIT
        )
        logger.info("✓ Autenticação seletiva ATIVADA")
        logger.info("  Visualização livre - Apenas criar/deletar pedidos requerem autenticação")
        logger.info("  Usuário: admin")
        if ENABLE_RATE_LIMIT:
            logger.info("✓ Rate Limiting ATIVADO (60/min, 1000/hora)")
        if not ENABLE_DEBUG_ENDPOINTS:
            logger.info("✓ Endpoints de Debug DESATIVADOS")
    except ImportError:
        logger.warning("Middleware de segurança não encontrado.")
    except Exception as e:
        logger.warning("Erro ao configurar segurança: %s", e)
    
    return app
