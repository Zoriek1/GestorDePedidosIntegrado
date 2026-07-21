# -*- coding: utf-8 -*-
"""
Configuração de CORS - Cross-Origin Resource Sharing
Gerencia descoberta de hostname/IP e configuração de CORS para PWA
"""
import configparser
import os
import socket
from pathlib import Path

from flask import request
from flask_cors import CORS


def get_server_info():
    """
    Descobre informações do servidor (hostname e IP local)

    Returns:
        tuple: (hostname, local_ip)
    """
    # Descobrir hostname configurado
    try:
        config_file = Path(__file__).parent.parent / "config" / "config_servidor.ini"
        if config_file.exists():
            parser = configparser.ConfigParser()
            parser.read(config_file, encoding="utf-8")
            hostname = parser.get("SERVIDOR", "hostname", fallback="Gestor-pedidos.local")
        else:
            hostname = "Gestor-pedidos.local"
    except Exception:
        hostname = "Gestor-pedidos.local"

    # Descobrir IP local
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "192.168.1.148"  # Fallback

    return hostname, local_ip


def get_allowed_origins():
    """
    Gera lista de origens permitidas para CORS

    Returns:
        list: Lista de URLs permitidas
    """
    hostname, local_ip = get_server_info()

    # Lista de origens permitidas (apenas HTTPS do próprio servidor)
    allowed_origins = [
        "https://localhost:5000",
        "https://127.0.0.1:5000",
        f"https://{hostname}:5000",
        f"https://{local_ip}:5000",
        # Frontend V2 (estático) - porta 3000
        "https://localhost:3000",
        "https://127.0.0.1:3000",
        f"https://{hostname}:3000",
        f"https://{local_ip}:3000",
        # Cloudflare Tunnel (produção)
        "https://gestaopedidos.planteumaflor.online",
        # Landing page (leads UTM) — apex e www. O POST de lead é "simple request"
        # (passa sem CORS), mas leituras de resposta exigem o Origin na allowlist.
        "https://lpb.planteumaflor.com",
        "https://www.lpb.planteumaflor.com",
        # Loja Nuvemshop principal (botao WhatsApp instrumentado no tema).
        "https://planteumaflor.com",
        "https://www.planteumaflor.com",
    ]

    # Permitir HTTP apenas para localhost (desenvolvimento)
    if os.environ.get("FLASK_ENV") == "development":
        allowed_origins.extend(
            [
                "http://localhost:5000",
                "http://127.0.0.1:5000",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                f"http://{hostname}:3000",
                f"http://{local_ip}:3000",
            ]
        )

    return allowed_origins


def setup_cors(app):
    """
    Configura CORS na aplicação Flask

    SEGURANÇA: Apenas origens do próprio servidor (localhost + hostname configurado)
    são permitidas para evitar requisições de origens não autorizadas.
    Usa after_request para refletir sempre o Origin da requisição (evita CORS
    errado quando atrás de proxy/Cloudflare que altera headers).
    """
    allowed_origins = get_allowed_origins()

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True,
                "max_age": 3600,
            }
        },
    )

    @app.after_request
    def _cors_reflect_origin(response):
        """Reflete o Origin da requisição na resposta para /api/* (evita proxy/Cloudflare)."""
        if not request.path.startswith("/api/"):
            return response
        origin = getattr(request, "origin", None) or request.headers.get("Origin")
        if origin:
            origin = origin.strip()
            if origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
        return response

    print(f"[SEGURANCA] OK CORS restrito a: {len(allowed_origins)} origens permitidas")
