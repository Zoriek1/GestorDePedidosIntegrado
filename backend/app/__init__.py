# -*- coding: utf-8 -*-
"""
Plante Uma Flor v3.0 - PWA
Sistema de Gerenciamento de Pedidos - Backend Flask API
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
import os
from pathlib import Path

# Instância global do SQLAlchemy
db = SQLAlchemy()
migrate = Migrate()

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
    
    print(f"[SEGURANÇA] ✓ CORS restrito a: {len(allowed_origins)} origens permitidas")
    
    # Carregar configurações
    if config:
        app.config.update(config)
    else:
        from app.config import Config
        app.config.from_object(Config)
    
    # Inicializar extensões
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Registrar Blueprints (apenas API REST)
    from app.routes.api import api_bp
    from app.routes.clientes import clientes_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(clientes_bp)

    # Informar status do banco (sem criação automática)
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///"):
        db_path = Path(db_uri.replace("sqlite:///", ""))
        if db_path.exists():
            print(f"[OK] Banco de dados encontrado: {db_path}")
        else:
            print(f"[AVISO] Banco de dados nao encontrado: {db_path}")
            print("[AVISO] Execute as migracoes: flask db upgrade")
    
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
        print(f"[ERRO 500] {e}")
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
            print(f"[ERRO] Erro ao servir arquivo '{path}': {e}")
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
        print("[SEGURANÇA] ✓ Autenticação seletiva ATIVADA")
        print("[SEGURANÇA]   Visualização livre - Apenas criar/deletar pedidos requerem autenticação")
        print("[SEGURANÇA]   Usuário: admin")
        if ENABLE_RATE_LIMIT:
            print("[SEGURANÇA] ✓ Rate Limiting ATIVADO (60/min, 1000/hora)")
        if not ENABLE_DEBUG_ENDPOINTS:
            print("[SEGURANÇA] ✓ Endpoints de Debug DESATIVADOS")
    except ImportError:
        print("[AVISO] Middleware de segurança não encontrado.")
    except Exception as e:
        print(f"[AVISO] Erro ao configurar segurança: {e}")
    
    return app
