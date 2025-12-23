# -*- coding: utf-8 -*-
"""
Configuração de CORS - Cross-Origin Resource Sharing
Gerencia descoberta de hostname/IP e configuração de CORS para PWA
"""
import os
import socket
import configparser
from pathlib import Path
from flask_cors import CORS


def get_server_info():
    """
    Descobre informações do servidor (hostname e IP local)
    
    Returns:
        tuple: (hostname, local_ip)
    """
    # Descobrir hostname configurado
    try:
        config_file = Path(__file__).parent.parent / 'config' / 'config_servidor.ini'
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
        f"https://{local_ip}:5000"
    ]
    
    # Permitir HTTP apenas para localhost (desenvolvimento)
    if os.environ.get('FLASK_ENV') == 'development':
        allowed_origins.extend([
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ])
    
    return allowed_origins


def setup_cors(app):
    """
    Configura CORS na aplicação Flask
    
    SEGURANÇA: Apenas origens do próprio servidor (localhost + hostname configurado)
    são permitidas para evitar requisições de origens não autorizadas.
    
    Args:
        app: Instância da aplicação Flask
    """
    allowed_origins = get_allowed_origins()
    
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    print(f"[SEGURANCA] OK CORS restrito a: {len(allowed_origins)} origens permitidas")

