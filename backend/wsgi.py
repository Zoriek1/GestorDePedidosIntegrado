# -*- coding: utf-8 -*-
"""
WSGI entry point para produção com Waitress
"""
import os
import sys
from pathlib import Path

# Configurar encoding UTF-8 para evitar erros no Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Carregar variáveis de ambiente do arquivo .env
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from app import create_app
from app.config import config

# Determinar ambiente (padrão: production)
env = os.environ.get('FLASK_ENV', 'production')

# Obter configuração apropriada
app_config = config.get(env, config['default'])

# Criar aplicação Flask
app = create_app(config={
    'SECRET_KEY': app_config.SECRET_KEY,
    'SQLALCHEMY_DATABASE_URI': app_config.SQLALCHEMY_DATABASE_URI,
    'SQLALCHEMY_TRACK_MODIFICATIONS': app_config.SQLALCHEMY_TRACK_MODIFICATIONS,
    'JSON_AS_ASCII': app_config.JSON_AS_ASCII,
    'JSON_SORT_KEYS': app_config.JSON_SORT_KEYS
})

# Para execução direta (python wsgi.py)
if __name__ == '__main__':
    try:
        from waitress import serve
        
        host = os.environ.get('HOST', '0.0.0.0')
        port = int(os.environ.get('PORT', 5000))
        threads = int(os.environ.get('THREADS', 4))
        
        print("\n" + "="*60)
        print("PLANTE UMA FLOR - PWA v3.0 (PRODUÇÃO)")
        print("="*60)
        print(f"Ambiente: {env}")
        print(f"Servidor: Waitress (WSGI)")
        print(f"Host: {host}")
        print(f"Porta: {port}")
        print(f"Threads: {threads}")
        print(f"Banco de dados: {app_config.DATABASE_PATH}")
        print("\nServidor acessível em:")
        print(f"   Local:    http://localhost:{port}")
        print(f"   Rede:     http://{host}:{port}")
        print("\n[OK] Servidor de produção iniciado!")
        print("="*60 + "\n")
        
        serve(app, host=host, port=port, threads=threads)
    except ImportError:
        print("\n[ERRO] Waitress não está instalado!")
        print("   Execute: pip install waitress\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Servidor encerrado pelo usuário")
        print("[OK] Obrigado por usar Plante Uma Flor!\n")
