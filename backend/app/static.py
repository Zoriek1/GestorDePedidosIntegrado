# -*- coding: utf-8 -*-
"""
Static Routes - Servir arquivos estáticos do frontend
Gerencia rotas para servir arquivos do frontend PWA
"""
from flask import send_from_directory, abort
from pathlib import Path


def register_static_routes(app):
    """
    Registra rotas para servir arquivos estáticos do frontend PWA
    
    As rotas são registradas por último (catch-all) para que todas as
    rotas não mapeadas sejam direcionadas para o frontend, permitindo
    que o SPA routing funcione corretamente.
    
    Args:
        app: Instância da aplicação Flask
    """
    @app.route('/')
    @app.route('/<path:path>')
    def serve_frontend(path='index.html'):
        """
        Serve arquivos do frontend PWA
        
        Tenta servir o arquivo solicitado. Se não existir, serve o
        index.html para permitir que o roteamento do SPA funcione.
        
        IMPORTANTE: Esta rota NÃO deve interceptar rotas da API (/api/*)
        pois essas são tratadas pelos blueprints registrados anteriormente.
        
        Args:
            path: Caminho do arquivo solicitado
            
        Returns:
            Response: Arquivo solicitado ou index.html como fallback
        """
        try:
            # NUNCA interceptar rotas da API - deixar Flask retornar 404 se não existir
            # As rotas da API são registradas antes desta rota catch-all
            if path.startswith('api/'):
                abort(404)
            
            frontend_dir = Path(__file__).parent.parent.parent / 'frontend'
            
            # Normalizar o path para evitar problemas
            if path == '' or path is None:
                path = 'index.html'
            
            # Se o arquivo existe, serve ele
            file_path = frontend_dir / path
            if file_path.exists() and file_path.is_file():
                response = send_from_directory(str(frontend_dir), path)
                
                # Service Worker deve ser servido com no-cache para garantir updates
                # Isso evita que o navegador cacheie o SW e impeça atualizações
                if path == 'sw.js':
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                
                return response
            
            # Caso contrário, serve o index.html (SPA routing)
            return send_from_directory(str(frontend_dir), 'index.html')
        except Exception as e:
            print(f"[ERRO] Erro ao servir arquivo '{path}': {e}")
            # Tentar servir o index.html como fallback
            try:
                frontend_dir = Path(__file__).parent.parent.parent / 'frontend'
                return send_from_directory(str(frontend_dir), 'index.html')
            except:
                abort(404)


