# -*- coding: utf-8 -*-
"""
Configuração de segurança (CORS e middleware)
"""
import configparser
import os
import socket
from pathlib import Path

from app.extensions import cors


def configure_security(app):
    """
    Configura CORS e middleware de segurança.
    """
    # Habilitar CORS para permitir requisições do frontend PWA
    # SEGURANÇA: Apenas origens do próprio servidor (localhost + hostname configurado)
    try:
        config_file = Path(__file__).parent.parent / 'config_servidor.ini'
        if config_file.exists():
            parser = configparser.ConfigParser()
            parser.read(config_file, encoding='utf-8')
            hostname = parser.get('SERVIDOR', 'hostname', fallback='Gestor-pedidos.local')
        else:
            hostname = 'Gestor-pedidos.local'
    except Exception:
        hostname = 'Gestor-pedidos.local'

    # Descobrir IP local
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
    except Exception:
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

    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True
            }
        }
    )

    print(f"[SEGURANÇA] ✓ CORS restrito a: {len(allowed_origins)} origens permitidas")

    # ============================================
    # SEGURANÇA: Autenticação e Rate Limiting
    # ============================================
    # Segurança ATIVADA por padrão se arquivo .env existir
    # Para desativar, defina ENABLE_AUTH=false no .env
    enable_rate_limit = os.environ.get('ENABLE_RATE_LIMIT', 'true').lower() == 'true'
    enable_debug_endpoints = os.environ.get('ENABLE_DEBUG_ENDPOINTS', 'false').lower() == 'true'

    # Sempre configurar middleware (rate limiting sempre ativo)
    # Autenticação agora é seletiva - apenas rotas críticas exigem autenticação
    try:
        from app.middleware import setup_security_middleware
        setup_security_middleware(
            app,
            enable_auth=False,  # Autenticação global desativada - apenas rotas específicas
            enable_rate_limit=enable_rate_limit
        )
        print("[SEGURANÇA] ✓ Autenticação seletiva ATIVADA")
        print("[SEGURANÇA]   Visualização livre - Apenas criar/deletar pedidos requerem autenticação")
        print("[SEGURANÇA]   Usuário: admin")
        if enable_rate_limit:
            print("[SEGURANÇA] ✓ Rate Limiting ATIVADO (60/min, 1000/hora)")
        if not enable_debug_endpoints:
            print("[SEGURANÇA] ✓ Endpoints de Debug DESATIVADOS")
    except ImportError:
        print("[AVISO] Middleware de segurança não encontrado.")
    except Exception as exc:
        print(f"[AVISO] Erro ao configurar segurança: {exc}")
